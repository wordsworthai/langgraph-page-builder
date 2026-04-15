"""
Landing Page Builder nodes.

Organized by pipeline phase:
- routing: planner, fetch_sections_by_id
- business_intelligence: business_data_extractor, trade_classifier, campaign_intent_synthesizer
- template_selection: section repo, type details, L0/L1 generation, retrieval, caching
- post_processing: template sections, template compilation, HTML, screenshots
- autopop: style nodes, content nodes (text/media)
"""

from wwai_agent_orchestration.nodes.landing_page_builder.routing import (
    planner_node,
    fetch_sections_by_id_node,
)
from wwai_agent_orchestration.nodes.landing_page_builder.business_intelligence import (
    business_data_extractor_node,
    trade_classifier_node,
    campaign_intent_synthesizer_node,
)
from wwai_agent_orchestration.nodes.landing_page_builder.template_selection import (
    section_repo_fetcher_node,
    generate_template_structures_node,
    template_evaluator_smb_node,
    resolve_template_sections_from_repo_node,
    cache_lookup_template_recommendations_node,
    cache_template_recommendations_node,
)
from wwai_agent_orchestration.nodes.landing_page_builder.post_processing import (
    save_generation_template_sections_node,
    template_compilation_node,
    screenshot_capture_node,
    db_html_compilation_node,
)

__all__ = [
    # Routing
    "planner_node",
    "fetch_sections_by_id_node",
    # Business intelligence
    "business_data_extractor_node",
    "trade_classifier_node",
    "campaign_intent_synthesizer_node",
    # Template selection
    "section_repo_fetcher_node",
    "generate_template_structures_node",
    "template_evaluator_smb_node",
    "resolve_template_sections_from_repo_node",
    "cache_lookup_template_recommendations_node",
    "cache_template_recommendations_node",
    # Post processing
    "save_generation_template_sections_node",
    "template_compilation_node",
    "db_html_compilation_node",
    "screenshot_capture_node",
]
