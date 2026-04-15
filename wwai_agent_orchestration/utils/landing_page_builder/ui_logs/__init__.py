"""
Landing page builder UI utils for ui_execution_log HTML generation.
"""

from wwai_agent_orchestration.utils.landing_page_builder.ui_logs._common import (
    make_ui_execution_log_entry,
    make_ui_execution_log_entry_from_registry,
    wrap_content,
)
from wwai_agent_orchestration.utils.landing_page_builder.ui_logs.template_selection_ui import (
    section_breakdown_html,
    template_list_html,
)
from wwai_agent_orchestration.utils.landing_page_builder.ui_logs.data_collection_ui import (
    business_data_html,
    campaign_intent_html,
    trade_picked_html,
)
from wwai_agent_orchestration.utils.landing_page_builder.ui_logs.milestone_ui import (
    save_sections_html,
    loading_sections_html,
    compilation_html,
    autopop_start_html,
    autopop_end_html,
    preparing_template_html,
    cache_lookup_html,
    container_color_html,
    semantic_names_html,
    content_planner_html,
    template_images_html,
    template_videos_html,
    final_snapshot_html,
    content_text_finalized_html,
    content_media_finalized_html,
)

__all__ = [
    "make_ui_execution_log_entry",
    "make_ui_execution_log_entry_from_registry",
    "wrap_content",
    "section_breakdown_html",
    "template_list_html",
    "business_data_html",
    "campaign_intent_html",
    "trade_picked_html",
    "save_sections_html",
    "loading_sections_html",
    "compilation_html",
    "autopop_start_html",
    "autopop_end_html",
    "preparing_template_html",
    "cache_lookup_html",
    "container_color_html",
    "semantic_names_html",
    "content_planner_html",
    "template_images_html",
    "template_videos_html",
    "final_snapshot_html",
    "content_text_finalized_html",
    "content_media_finalized_html",
]
