"""Landing page builder workflow: task-specific taxonomy and policy."""

from wwai_agent_orchestration.evals.human_feedback.taxonomy.landing_page_builder.color_palette import (
    derive_overall_pass as color_palette_derive_overall_pass,
    get_task_feedback_taxonomy as color_palette_get_task_feedback_taxonomy,
)
from wwai_agent_orchestration.evals.human_feedback.taxonomy.landing_page_builder.landing_page import (
    derive_overall_pass as landing_page_derive_overall_pass,
    get_task_feedback_taxonomy as landing_page_get_task_feedback_taxonomy,
)
from wwai_agent_orchestration.evals.human_feedback.taxonomy.landing_page_builder.section_coverage import (
    derive_overall_pass as section_coverage_derive_overall_pass,
    get_task_feedback_taxonomy as section_coverage_get_task_feedback_taxonomy,
)
from wwai_agent_orchestration.evals.human_feedback.taxonomy.landing_page_builder.template_selection import (
    derive_overall_pass as template_selection_derive_overall_pass,
    get_task_feedback_taxonomy as template_selection_get_task_feedback_taxonomy,
)

__all__ = [
    "color_palette_derive_overall_pass",
    "color_palette_get_task_feedback_taxonomy",
    "landing_page_derive_overall_pass",
    "landing_page_get_task_feedback_taxonomy",
    "section_coverage_derive_overall_pass",
    "section_coverage_get_task_feedback_taxonomy",
    "template_selection_derive_overall_pass",
    "template_selection_get_task_feedback_taxonomy",
]
