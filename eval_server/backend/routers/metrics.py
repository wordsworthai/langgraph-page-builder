"""Metrics summary endpoints."""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from eval_metrics_adapter import (
    get_all_eval_sets,
    get_eval_runs,
    get_human_feedback_for_eval_set,
    get_eval_judge_results_for_eval_set,
)
from wwai_agent_orchestration.evals.metrics import (
    EvalMetricsInput,
    MetricsService,
)

from .common import (
    DEFAULT_MONGO_URI,
    DEFAULT_DB_NAME,
    make_json_serializable,
)

router = APIRouter()

METRICS_DB = "eval"


class MetricsSummaryRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    db_name: Optional[str] = DEFAULT_DB_NAME
    limit: Optional[int] = 50


def _build_metrics_input(eval_set_id, task_type, runs, human_feedback_docs, judge_docs):
    """Build EvalMetricsInput from raw DB docs."""
    runs_for_input = [
        {
            "run_id": r.get("run_id"),
            "status": r.get("status", "unknown"),
            "task_type": r.get("task_type", task_type),
            "workflow_mode": r.get("workflow_mode", "unknown"),
        }
        for r in runs
    ]
    human_feedback = [
        {
            "run_id": d.get("run_id"),
            "task_type": d.get("task_type", task_type),
            "feedback": d.get("feedback", {}),
        }
        for d in human_feedback_docs
    ]
    judge_results = [
        {"run_id": d.get("run_id"), "result": d.get("result", {})}
        for d in judge_docs
    ]
    return EvalMetricsInput(
        eval_set_id=eval_set_id,
        task_type=task_type,
        runs=runs_for_input,
        human_feedback=human_feedback,
        judge_results=judge_results,
    )


@router.post("/api/metrics/summary")
async def get_metrics_summary(request: MetricsSummaryRequest):
    """Get eval sets with aggregated metrics (human feedback + AI judge results)."""
    try:
        db_name = request.db_name or METRICS_DB
        eval_sets = get_all_eval_sets(
            mongo_uri=request.mongo_uri,
            db_name=db_name,
            limit=request.limit or 50,
        )
        metrics_service = MetricsService()
        rows = []
        for es in eval_sets:
            eval_set_id = es["eval_set_id"]
            task_type = es.get("task_type", "landing_page")
            runs = get_eval_runs(
                eval_set_id=eval_set_id,
                mongo_uri=request.mongo_uri,
                db_name=db_name,
            )
            human_feedback_docs = get_human_feedback_for_eval_set(
                eval_set_id=eval_set_id,
                mongo_uri=request.mongo_uri,
                db_name=db_name,
            )
            judge_docs = get_eval_judge_results_for_eval_set(
                eval_set_id=eval_set_id,
                task_name="template_eval",
                mongo_uri=request.mongo_uri,
                db_name=db_name,
            )
            input_bundle = _build_metrics_input(
                eval_set_id=eval_set_id,
                task_type=task_type,
                runs=runs,
                human_feedback_docs=human_feedback_docs,
                judge_docs=judge_docs,
            )
            result = metrics_service.compute(input_bundle)
            metrics = result.model_dump()
            rows.append({
                "eval_set_id": eval_set_id,
                "task_type": task_type,
                "total": es.get("total", 0),
                "completed": es.get("completed", 0),
                "failed": es.get("failed", 0),
                "running": es.get("running", 0),
                "progress_pct": es.get("progress_pct", 0),
                "latest_timestamp": es.get("latest_timestamp"),
                "metrics": make_json_serializable(metrics),
            })
        return make_json_serializable({"eval_sets": rows})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
