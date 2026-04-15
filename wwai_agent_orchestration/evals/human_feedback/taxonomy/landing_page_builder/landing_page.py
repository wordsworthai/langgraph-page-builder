"""Landing page task: taxonomy and policy."""

from __future__ import annotations

from typing import Any, Dict

from wwai_agent_orchestration.evals.human_feedback.utils import is_true
from wwai_agent_orchestration.evals.human_feedback.taxonomy.contracts import (
    TaskFeedbackTaxonomy,
    TaxonomyCategory,
)

def get_task_feedback_taxonomy() -> TaskFeedbackTaxonomy:
    return TaskFeedbackTaxonomy(
        task_type="landing_page",
        mode="mixed",
        display_name="Full Page Generation",
        description="Complete end-to-end Landing Page Builder recommendation with autopopulation",
        categories=[
            TaxonomyCategory(
                key="widget_code_issue",
                label="Widget Code Issue",
                value_type="boolean",
                severity="blocker",
                order=1,
            ),
            TaxonomyCategory(
                key="ai_copy_issue",
                label="AI Copy Issue",
                value_type="boolean",
                severity="major",
                order=2,
            ),
            TaxonomyCategory(
                key="ai_image_issue",
                label="AI Image Issue",
                value_type="boolean",
                severity="major",
                order=3,
            ),
            TaxonomyCategory(
                key="ai_styles_issue",
                label="AI Styles Issue",
                value_type="boolean",
                severity="major",
                order=4,
            ),
            TaxonomyCategory(
                key="overall_readiness",
                label="Overall Readiness",
                value_type="enum",
                options=["fail", "needs_work", "pass"],
                required=False,
                severity="blocker",
                order=5,
            ),
            TaxonomyCategory(
                key="comments",
                label="Comments",
                value_type="text",
                severity="minor",
                order=7,
            ),
        ],
    )


def derive_overall_pass(feedback: Dict[str, Any]) -> bool:
    readiness = feedback.get("overall_readiness")
    if readiness == "fail":
        return False
    if readiness == "pass":
        return True
    major_flags = [
        "widget_code_issue",
        "ai_copy_issue",
        "ai_image_issue",
        "ai_styles_issue",
    ]
    return all(not is_true(feedback.get(flag)) for flag in major_flags)
