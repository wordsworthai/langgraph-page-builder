"""Task-specific verdict policy for human feedback."""

from __future__ import annotations

from typing import Any, Dict, List

from wwai_agent_orchestration.evals.human_feedback.metrics.kpi_utils import (
    compute_task_human_kpis_from_taxonomy,
)
from wwai_agent_orchestration.evals.human_feedback.taxonomy.landing_page_builder import (
    color_palette_derive_overall_pass,
    landing_page_derive_overall_pass,
    section_coverage_derive_overall_pass,
    template_selection_derive_overall_pass,
)
from wwai_agent_orchestration.evals.human_feedback.taxonomy.registry import (
    get_taxonomy,
)


def derive_overall_pass(task_type: str, feedback: Dict[str, Any]) -> bool:
    """Derive pass/fail from task-specific policy."""
    if task_type == "template_selection":
        return template_selection_derive_overall_pass(feedback)
    if task_type == "landing_page":
        return landing_page_derive_overall_pass(feedback)
    if task_type == "section_coverage":
        return section_coverage_derive_overall_pass(feedback)
    if task_type == "color_palette":
        return color_palette_derive_overall_pass(feedback)
    raise ValueError(f"Unsupported task_type for verdict policy: {task_type}")


def task_human_kpis(
    task_type: str,
    feedback_docs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Return taxonomy-driven human KPIs from feedback docs."""
    try:
        taxonomy = get_taxonomy(task_type=task_type)
    except ValueError:
        return {}
    return compute_task_human_kpis_from_taxonomy(taxonomy, feedback_docs)
