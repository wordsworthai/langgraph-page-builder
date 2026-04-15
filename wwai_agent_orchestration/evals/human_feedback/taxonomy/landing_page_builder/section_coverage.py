"""Section coverage task: taxonomy and policy."""

from __future__ import annotations

from typing import Any, Dict

from wwai_agent_orchestration.evals.human_feedback.utils import is_true
from wwai_agent_orchestration.evals.human_feedback.taxonomy.contracts import (
    TaskFeedbackTaxonomy,
    TaxonomyCategory,
)

def get_task_feedback_taxonomy() -> TaskFeedbackTaxonomy:
    return TaskFeedbackTaxonomy(
        task_type="section_coverage",
        mode="mixed",
        display_name="Section Coverage",
        description="Preset sections workflow for section coverage testing",
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
                key="breaking_section_index",
                label="Index of Breaking Section",
                value_type="text",
                required=False,
                severity="major",
                order=2,
                placeholder="Comma-separated list of 0-based indices (e.g. 0, 2, 5) where breaking sections appear (when above is True)",
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
