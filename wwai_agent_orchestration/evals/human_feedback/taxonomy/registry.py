"""Versioned taxonomy registry for human feedback."""

from __future__ import annotations

from typing import Dict, List

from wwai_agent_orchestration.evals.human_feedback.taxonomy.contracts import (
    TaskFeedbackTaxonomy,
)
from wwai_agent_orchestration.evals.human_feedback.taxonomy.landing_page_builder import (
    color_palette_get_task_feedback_taxonomy,
    landing_page_get_task_feedback_taxonomy,
    section_coverage_get_task_feedback_taxonomy,
    template_selection_get_task_feedback_taxonomy,
)

REGISTRY: Dict[str, Dict[str, TaskFeedbackTaxonomy]] = {
    "template_selection": {"v1": template_selection_get_task_feedback_taxonomy()},
    "landing_page": {"v1": landing_page_get_task_feedback_taxonomy()},
    "section_coverage": {"v1": section_coverage_get_task_feedback_taxonomy()},
    "color_palette": {"v1": color_palette_get_task_feedback_taxonomy()},
}


def get_taxonomy(task_type: str, version: str = "v1") -> TaskFeedbackTaxonomy:
    """Return taxonomy for task + schema version."""
    task_versions = REGISTRY.get(task_type)
    if not task_versions:
        raise ValueError(f"Unsupported task_type: {task_type}")
    taxonomy = task_versions.get(version)
    if not taxonomy:
        raise ValueError(f"Unsupported taxonomy version for {task_type}: {version}")
    return taxonomy


def get_allowed_keys(task_type: str, version: str = "v1") -> List[str]:
    """Return active keys for task taxonomy."""
    taxonomy = get_taxonomy(task_type=task_type, version=version)
    active_categories = [c for c in taxonomy.categories if c.active]
    return [c.key for c in sorted(active_categories, key=lambda c: c.order)]


def get_all_task_types() -> List[str]:
    """Return all registered task types."""
    return list(REGISTRY.keys())
