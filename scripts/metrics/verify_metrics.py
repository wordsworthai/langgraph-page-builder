"""Verify bounds and consistency of computed metrics.

Task type is inferred from runs, feedback, or eval_sets.

  poetry run python scripts/metrics/verify_metrics.py \
    --eval_set_id="template_selection_sample_20260303_115118"
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from absl import app, flags
from pymongo import MongoClient

from _common import (
    DEFAULT_DB_NAME,
    DEFAULT_MONGO_URI,
    EVAL_SETS_COLLECTION,
    FEEDBACK_COLLECTION,
    JUDGE_COLLECTION,
    RUNS_COLLECTION,
    print_json,
)
from wwai_agent_orchestration.evals.metrics import EvalMetricsInput, MetricsService

FLAGS = flags.FLAGS

flags.DEFINE_string("mongo_uri", DEFAULT_MONGO_URI, "MongoDB connection URI")
flags.DEFINE_string("db_name", DEFAULT_DB_NAME, "Database name")
flags.DEFINE_string("eval_set_id", None, "Eval set ID to verify", required=True)
flags.DEFINE_string("task_name", "template_eval", "Judge task_name filter")


def _infer_task_type(
    runs: list,
    feedback_docs: list,
    eval_set_doc: dict | None,
) -> str:
    """Infer task_type from runs, feedback, or eval_sets."""
    if runs and runs[0].get("task_type"):
        return runs[0]["task_type"]
    if feedback_docs and feedback_docs[0].get("task_type"):
        return feedback_docs[0]["task_type"]
    if eval_set_doc:
        eval_type = eval_set_doc.get("eval_type") or eval_set_doc.get("task_type")
        if eval_type:
            return eval_type
    raise SystemExit(
        "Cannot infer task_type for eval_set_id. "
        "Ensure eval_runs, human_feedback, or eval_sets has task_type/eval_type."
    )


def _assert(value: bool, message: str, failures: list[str]) -> None:
    if not value:
        failures.append(message)


def _in_range(val: float | None, lo: float, hi: float) -> bool:
    if val is None:
        return True
    return lo <= val <= hi


def main(argv):
    del argv
    client = MongoClient(FLAGS.mongo_uri)
    db = client[FLAGS.db_name]

    runs = list(db[RUNS_COLLECTION].find({"eval_set_id": FLAGS.eval_set_id}))
    feedback_docs = list(
        db[FEEDBACK_COLLECTION].find({"eval_set_id": FLAGS.eval_set_id})
    )
    judge_docs = list(
        db[JUDGE_COLLECTION].find(
            {"eval_set_id": FLAGS.eval_set_id, "task_name": FLAGS.task_name}
        )
    )
    eval_set_doc = db[EVAL_SETS_COLLECTION].find_one(
        {"eval_set_id": FLAGS.eval_set_id}
    )

    task_type = _infer_task_type(runs, feedback_docs, eval_set_doc)

    human_feedback = [
        {
            "run_id": d.get("run_id"),
            "task_type": d.get("task_type", task_type),
            "feedback": d.get("feedback", {}),
        }
        for d in feedback_docs
    ]
    judge_results = [
        {"run_id": d.get("run_id"), "result": d.get("result", {})}
        for d in judge_docs
    ]
    runs_for_input = [
        {
            "run_id": r.get("run_id"),
            "status": r.get("status", "unknown"),
            "task_type": r.get("task_type", task_type),
            "workflow_mode": r.get("workflow_mode", "unknown"),
        }
        for r in runs
    ]

    input_bundle = EvalMetricsInput(
        eval_set_id=FLAGS.eval_set_id,
        task_type=task_type,
        runs=runs_for_input,
        human_feedback=human_feedback,
        judge_results=judge_results,
    )

    service = MetricsService()
    result = service.compute(input_bundle)

    failures: list[str] = []

    _assert(
        result.total_runs >= 0,
        f"total_runs must be non-negative, got {result.total_runs}",
        failures,
    )
    _assert(
        result.completed_runs >= 0,
        f"completed_runs must be non-negative, got {result.completed_runs}",
        failures,
    )
    _assert(
        result.completed_runs <= result.total_runs,
        f"completed_runs ({result.completed_runs}) must be <= total_runs ({result.total_runs})",
        failures,
    )
    _assert(
        result.human_feedback_count >= 0,
        f"human_feedback_count must be non-negative, got {result.human_feedback_count}",
        failures,
    )
    _assert(
        result.ai_feedback_count >= 0,
        f"ai_feedback_count must be non-negative, got {result.ai_feedback_count}",
        failures,
    )
    _assert(
        _in_range(result.human_pass_pct, 0, 100),
        f"human_pass_pct must be in [0,100] or None, got {result.human_pass_pct}",
        failures,
    )
    _assert(
        _in_range(result.ai_pass_pct, 0, 100),
        f"ai_pass_pct must be in [0,100] or None, got {result.ai_pass_pct}",
        failures,
    )
    _assert(
        _in_range(result.agreement_pct, 0, 100),
        f"agreement_pct must be in [0,100] or None, got {result.agreement_pct}",
        failures,
    )
    _assert(
        0 <= result.coverage_pct <= 100,
        f"coverage_pct must be in [0,100], got {result.coverage_pct}",
        failures,
    )

    for seg_key, seg in result.segments.items():
        _assert(
            seg.get("total_runs", 0) >= seg.get("completed_runs", 0),
            f"Segment {seg_key}: completed_runs must be <= total_runs",
            failures,
        )

    output = {
        "eval_set_id": FLAGS.eval_set_id,
        "task_type": task_type,
        "failures": failures,
        "passed": len(failures) == 0,
        "sample_run_ids": [r.get("run_id") for r in runs[:3] if r.get("run_id")],
        "metrics_summary": {
            "total_runs": result.total_runs,
            "completed_runs": result.completed_runs,
            "human_feedback_count": result.human_feedback_count,
            "ai_feedback_count": result.ai_feedback_count,
        },
    }
    print_json(output)
    return 0 if not failures else 1


if __name__ == "__main__":
    app.run(main)
