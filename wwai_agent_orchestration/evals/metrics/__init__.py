"""Task-agnostic metrics contracts and on-read computation services."""

from wwai_agent_orchestration.evals.metrics.contracts import (
    EvalMetricsInput,
    EvalMetricsResult,
)
from wwai_agent_orchestration.evals.metrics.functions import (
    extend_generic_metrics,
    generic_metrics,
)
from wwai_agent_orchestration.evals.metrics.landing_page_builder import (
    color_palette_metrics,
    landing_page_metrics,
    section_coverage_metrics,
    template_selection_metrics,
)
from wwai_agent_orchestration.evals.metrics.service import MetricsService

__all__ = [
    "EvalMetricsInput",
    "EvalMetricsResult",
    "MetricsService",
    "extend_generic_metrics",
    "generic_metrics",
    "color_palette_metrics",
    "landing_page_metrics",
    "section_coverage_metrics",
    "template_selection_metrics",
]
