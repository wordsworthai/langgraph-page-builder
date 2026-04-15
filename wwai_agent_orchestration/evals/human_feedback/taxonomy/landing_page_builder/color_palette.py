"""Color palette task: taxonomy and policy."""

from __future__ import annotations

from typing import Any, Dict

from wwai_agent_orchestration.evals.human_feedback.utils import is_true
from wwai_agent_orchestration.evals.human_feedback.taxonomy.contracts import (
    TaskFeedbackTaxonomy,
    TaxonomyCategory,
)


def get_task_feedback_taxonomy() -> TaskFeedbackTaxonomy:
    return TaskFeedbackTaxonomy(
        task_type="color_palette",
        mode="mixed",
        display_name="Color Palette",
        description="Preset sections workflow for color palette comparison",
        categories=[
            TaxonomyCategory(
                key="has_breaking_section",
                label="Includes Section whose code is breaking",
                value_type="boolean",
                required=True,
                severity="blocker",
                order=1,
                placeholder="Does this run include any section whose code is breaking?",
            ),
            TaxonomyCategory(
                key="palette_works_well",
                label="Palette works well visually",
                value_type="boolean",
                required=False,
                severity="minor",
                order=2,
                placeholder="Does this color palette work well for this template?",
            ),
            TaxonomyCategory(
                key="comments",
                label="Comments",
                value_type="text",
                required=False,
                severity="minor",
                order=3,
            ),
        ],
    )


def derive_overall_pass(feedback: Dict[str, Any]) -> bool:
    return not is_true(feedback.get("has_breaking_section"))
