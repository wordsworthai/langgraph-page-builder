"""Template selection task: taxonomy and policy."""

from __future__ import annotations

from typing import Any, Dict

from wwai_agent_orchestration.evals.human_feedback.utils import is_true
from wwai_agent_orchestration.evals.human_feedback.taxonomy.contracts import (
    TaskFeedbackTaxonomy,
    TaxonomyCategory,
)


def get_task_feedback_taxonomy() -> TaskFeedbackTaxonomy:
    return TaskFeedbackTaxonomy(
        task_type="template_selection",
        mode="categories",
        display_name="Template Selection",
        description="Template generation with placeholder content (no autopopulation)",
        categories=[
            TaxonomyCategory(
                key="template_structure_issue",
                label="Template Structure Issue",
                value_type="boolean",
                severity="major",
                order=1,
            ),
            TaxonomyCategory(
                key="section_selection_issue",
                label="Section Selection Issue",
                value_type="boolean",
                severity="major",
                order=2,
            ),
            TaxonomyCategory(
                key="section_ordering_issue",
                label="Section Ordering Issue",
                value_type="boolean",
                severity="major",
                order=3,
            ),
            TaxonomyCategory(
                key="section_count_issue",
                label="Section Count Issue",
                value_type="boolean",
                severity="major",
                order=4,
            ),
            TaxonomyCategory(
                key="intent_fit_issue",
                label="Intent Fit Issue",
                value_type="boolean",
                severity="major",
                order=5,
            ),
            TaxonomyCategory(
                key="comments",
                label="Comments",
                value_type="text",
                severity="minor",
                order=6,
            ),
        ],
    )


def derive_overall_pass(feedback: Dict[str, Any]) -> bool:
    blocking_flags = [
        "template_structure_issue",
        "section_selection_issue",
        "section_ordering_issue",
        "section_count_issue",
        "intent_fit_issue",
    ]
    return all(not is_true(feedback.get(flag)) for flag in blocking_flags)
