"""Eval sets, runs, and AI eval results endpoints."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from eval_metrics_adapter import (
    get_all_eval_sets,
    get_eval_runs,
    get_eval_set_summary,
    get_eval_results_for_set,
    get_eval_result_by_run_id,
    get_eval_set_metrics,
)

from .common import (
    DEFAULT_MONGO_URI,
    DEFAULT_DB_NAME,
    make_json_serializable,
)

router = APIRouter()


class EvalSetsRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    db_name: Optional[str] = DEFAULT_DB_NAME
    limit: Optional[int] = 50


@router.post("/api/eval-sets")
async def list_eval_sets(request: EvalSetsRequest):
    """Get list of all eval sets with their summary statistics."""
    try:
        eval_sets = get_all_eval_sets(
            mongo_uri=request.mongo_uri,
            db_name=request.db_name,
            limit=request.limit,
        )
        return make_json_serializable({"eval_sets": eval_sets})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class EvalSetRunsRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    db_name: Optional[str] = DEFAULT_DB_NAME
    eval_set_id: str
    status_filter: Optional[str] = None


@router.post("/api/eval-set-runs")
async def list_eval_set_runs(request: EvalSetRunsRequest):
    """Get case-centric runs for a specific eval set (one per case, latest run)."""
    try:
        runs = get_eval_runs(
            eval_set_id=request.eval_set_id,
            mongo_uri=request.mongo_uri,
            db_name=request.db_name,
            status_filter=request.status_filter,
        )
        summary = get_eval_set_summary(
            eval_set_id=request.eval_set_id,
            mongo_uri=request.mongo_uri,
            db_name=request.db_name,
        )
        return make_json_serializable({
            "eval_set_id": request.eval_set_id,
            "summary": summary,
            "runs": runs,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/eval-results")
async def get_eval_results_endpoint(request: Request):
    """
    Get all AI eval results for an eval set.
    """
    try:
        body = await request.json()
        mongo_uri = body.get("mongo_uri") or DEFAULT_MONGO_URI
        db_name = body.get("db_name") or DEFAULT_DB_NAME
        eval_set_id = body.get("eval_set_id")
        task_name = body.get("task_name", "template_eval")

        if not eval_set_id:
            raise HTTPException(status_code=400, detail="eval_set_id is required")

        results = get_eval_results_for_set(
            eval_set_id=eval_set_id,
            task_name=task_name,
            mongo_uri=mongo_uri,
            db_name=db_name,
        )

        metrics = get_eval_set_metrics(
            eval_set_id=eval_set_id,
            task_name=task_name,
            mongo_uri=mongo_uri,
            db_name=db_name,
        )

        for r in results:
            if "_id" in r:
                r["_id"] = str(r["_id"])
            for dt_field in ["created_at", "updated_at"]:
                if dt_field in r and r[dt_field]:
                    r[dt_field] = r[dt_field].isoformat() if hasattr(r[dt_field], "isoformat") else str(r[dt_field])

        return {
            "eval_set_id": eval_set_id,
            "task_name": task_name,
            "results": results,
            "metrics": metrics,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/eval-result")
async def get_eval_result_endpoint(request: Request):
    """
    Get a single AI eval result by eval_set_id + run_id + task_name.
    """
    try:
        body = await request.json()
        mongo_uri = body.get("mongo_uri") or DEFAULT_MONGO_URI
        db_name = body.get("db_name") or DEFAULT_DB_NAME
        eval_set_id = body.get("eval_set_id")
        run_id = body.get("run_id")
        task_name = body.get("task_name", "template_eval")

        if not eval_set_id or not run_id:
            raise HTTPException(
                status_code=400,
                detail="eval_set_id and run_id are required"
            )

        result = get_eval_result_by_run_id(
            eval_set_id=eval_set_id,
            run_id=run_id,
            task_name=task_name,
            mongo_uri=mongo_uri,
            db_name=db_name,
        )

        if result:
            if "_id" in result:
                result["_id"] = str(result["_id"])
            for dt_field in ["created_at", "updated_at"]:
                if dt_field in result and result[dt_field]:
                    result[dt_field] = result[dt_field].isoformat() if hasattr(result[dt_field], "isoformat") else str(result[dt_field])

        return {"result": result}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/eval-results-map")
async def get_eval_results_map_endpoint(request: Request):
    """
    Get AI eval results as a map keyed by run_id (for easy lookup in run lists).
    """
    try:
        body = await request.json()
        mongo_uri = body.get("mongo_uri") or DEFAULT_MONGO_URI
        db_name = body.get("db_name") or DEFAULT_DB_NAME
        eval_set_id = body.get("eval_set_id")
        task_name = body.get("task_name", "template_eval")

        if not eval_set_id:
            raise HTTPException(status_code=400, detail="eval_set_id is required")

        results = get_eval_results_for_set(
            eval_set_id=eval_set_id,
            task_name=task_name,
            mongo_uri=mongo_uri,
            db_name=db_name,
        )

        results_map = {}
        for r in results:
            run_id = r.get("run_id")
            if run_id:
                if "_id" in r:
                    r["_id"] = str(r["_id"])
                for dt_field in ["created_at", "updated_at"]:
                    if dt_field in r and r[dt_field]:
                        r[dt_field] = r[dt_field].isoformat() if hasattr(r[dt_field], "isoformat") else str(r[dt_field])
                results_map[run_id] = r

        return {
            "eval_set_id": eval_set_id,
            "task_name": task_name,
            "results_map": results_map,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
