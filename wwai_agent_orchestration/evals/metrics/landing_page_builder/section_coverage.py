"""Section coverage task metrics."""

from __future__ import annotations

from wwai_agent_orchestration.evals.metrics.contracts import (
    EvalMetricsInput,
    EvalMetricsResult,
)
from wwai_agent_orchestration.evals.metrics.functions import generic_metrics


def section_coverage_metrics(input_bundle: EvalMetricsInput) -> EvalMetricsResult:
    """Task-specific metrics for section_coverage workflow."""
    return generic_metrics(input_bundle)
