"""Compute metrics from stored runs, human feedback, and judge results.

Task type is inferred from runs, feedback, or eval_sets.

  poetry run python scripts/metrics/compute_metrics.py \
    --eval_set_id="template_selection_sample_20260304_093257"
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
flags.DEFINE_string("eval_set_id", None, "Eval set ID", required=True)
flags.DEFINE_string(
    "task_name",
    "template_eval",
    "Judge task_name filter (e.g. template_eval)",
)


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


def main(argv):
    del argv
    client = MongoClient(FLAGS.mongo_uri)
    db = client[FLAGS.db_name]

    runs_coll = db[RUNS_COLLECTION]
    feedback_coll = db[FEEDBACK_COLLECTION]
    judge_coll = db[JUDGE_COLLECTION]
    eval_sets_coll = db[EVAL_SETS_COLLECTION]

    runs = list(runs_coll.find({"eval_set_id": FLAGS.eval_set_id}))
    feedback_docs = list(feedback_coll.find({"eval_set_id": FLAGS.eval_set_id}))
    judge_docs = list(
        judge_coll.find(
            {"eval_set_id": FLAGS.eval_set_id, "task_name": FLAGS.task_name}
        )
    )
    eval_set_doc = eval_sets_coll.find_one({"eval_set_id": FLAGS.eval_set_id})

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

    output = result.model_dump()
    output["sample_run_ids"] = [r.get("run_id") for r in runs[:3] if r.get("run_id")]
    print_json(output)
    return 0


if __name__ == "__main__":
    app.run(main)
