"""
Adapters for eval_server to read from Mongo collections.

Split by domain:
- eval_adapter: eval sets, runs, outputs, judge results
- metrics_adapter: legacy judge-based aggregate metrics
- feedback_adapter: human feedback
"""

from .eval_adapter import (
    get_all_eval_sets,
    get_eval_output,
    get_eval_result_by_run_id,
    get_eval_results_for_set,
    get_eval_runs,
    get_eval_set_summary,
    get_eval_judge_results_for_eval_set,
    resolve_case_id_from_run,
    resolve_run_id_from_thread,
)
from .feedback_adapter import get_human_feedback_for_eval_set
from .metrics_adapter import get_eval_set_metrics

__all__ = [
    "get_all_eval_sets",
    "get_eval_output",
    "get_eval_result_by_run_id",
    "get_eval_results_for_set",
    "get_eval_runs",
    "get_eval_set_summary",
    "get_eval_judge_results_for_eval_set",
    "get_human_feedback_for_eval_set",
    "get_eval_set_metrics",
    "resolve_case_id_from_run",
    "resolve_run_id_from_thread",
]
