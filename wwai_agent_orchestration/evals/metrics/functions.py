"""Default and task-agnostic metric functions."""

from __future__ import annotations

from typing import Any, Callable, Dict

from wwai_agent_orchestration.evals.human_feedback.policy import task_human_kpis
from wwai_agent_orchestration.evals.metrics._common import (
    agreement_pct,
    is_ai_pass,
    is_human_pass,
    safe_pct,
)
from wwai_agent_orchestration.evals.metrics.contracts import (
    EvalMetricsInput,
    EvalMetricsResult,
)

MetricsFn = Callable[[EvalMetricsInput], EvalMetricsResult]


def generic_metrics(input_bundle: EvalMetricsInput) -> EvalMetricsResult:
    """Task-agnostic baseline metrics from runs + human + judge artifacts."""
    total_runs = len(input_bundle.runs)
    completed_runs = sum(1 for run in input_bundle.runs if run.get("status") == "completed")
    human_count = len(input_bundle.human_feedback)
    judge_count = len(input_bundle.judge_results)

    # Use fixed 0.7 baseline; task-specific functions override with stricter thresholds
    ai_threshold = 0.7
    human_passes = sum(
        1
        for doc in input_bundle.human_feedback
        if is_human_pass(
            {
                "feedback": doc.get("feedback", {}),
                "task_type": doc.get("task_type", input_bundle.task_type),
            }
        )
    )
    ai_passes = sum(
        1
        for doc in input_bundle.judge_results
        if is_ai_pass(doc, score_threshold=ai_threshold)
    )

    coverage = safe_pct(human_count, total_runs)
    return EvalMetricsResult(
        eval_set_id=input_bundle.eval_set_id,
        task_type=input_bundle.task_type,
        total_runs=total_runs,
        completed_runs=completed_runs,
        human_feedback_count=human_count,
        ai_feedback_count=judge_count,
        human_pass_pct=safe_pct(human_passes, human_count),
        ai_pass_pct=safe_pct(ai_passes, judge_count),
        agreement_pct=agreement_pct(input_bundle, ai_threshold=ai_threshold),
        coverage_pct=coverage or 0.0,
        task_kpis=task_human_kpis(input_bundle.task_type, input_bundle.human_feedback),
    )


def extend_generic_metrics(
    input_bundle: EvalMetricsInput,
    overrides: Dict[str, Any] | None = None,
) -> EvalMetricsResult:
    """Run generic metrics and merge task-specific overrides."""
    result = generic_metrics(input_bundle)
    if overrides:
        return result.model_copy(update=overrides)
    return result
