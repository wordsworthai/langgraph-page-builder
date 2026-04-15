"""Template selection task metrics."""

from __future__ import annotations

from wwai_agent_orchestration.evals.metrics._common import (
    agreement_pct,
    is_ai_pass,
    safe_pct,
)
from wwai_agent_orchestration.evals.metrics.contracts import (
    EvalMetricsInput,
    EvalMetricsResult,
)
from wwai_agent_orchestration.evals.metrics.functions import extend_generic_metrics


def template_selection_metrics(input_bundle: EvalMetricsInput) -> EvalMetricsResult:
    """Task-specific metrics for template_selection with stricter AI pass threshold (0.8)."""
    ai_threshold = 0.8
    ai_passes = sum(
        1
        for doc in input_bundle.judge_results
        if is_ai_pass(doc, score_threshold=ai_threshold)
    )
    judge_count = len(input_bundle.judge_results)
    return extend_generic_metrics(
        input_bundle,
        overrides={
            "ai_pass_pct": safe_pct(ai_passes, judge_count),
            "agreement_pct": agreement_pct(input_bundle, ai_threshold=ai_threshold),
        },
    )
