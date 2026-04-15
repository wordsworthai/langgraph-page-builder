"""Service-level registry and execution for metrics functions."""

from __future__ import annotations

from typing import Dict

from wwai_agent_orchestration.evals.metrics.contracts import (
    EvalMetricsInput,
    EvalMetricsResult,
)
from wwai_agent_orchestration.evals.metrics.functions import (
    MetricsFn,
    generic_metrics,
)
from wwai_agent_orchestration.evals.metrics.landing_page_builder import (
    color_palette_metrics,
    landing_page_metrics,
    section_coverage_metrics,
    template_selection_metrics,
)


class MetricsService:
    """Computes metrics using task-type-based function dispatch."""

    def __init__(self) -> None:
        self._registry: Dict[str, MetricsFn] = {}
        self._register_defaults()

    def register(self, task_type: str, fn: MetricsFn) -> None:
        self._registry[task_type] = fn

    def compute(self, input_bundle: EvalMetricsInput) -> EvalMetricsResult:
        fn = self._registry.get(input_bundle.task_type, generic_metrics)
        return fn(input_bundle)

    def _register_defaults(self) -> None:
        self._registry["template_selection"] = template_selection_metrics
        self._registry["landing_page"] = landing_page_metrics
        self._registry["section_coverage"] = section_coverage_metrics
        self._registry["color_palette"] = color_palette_metrics
