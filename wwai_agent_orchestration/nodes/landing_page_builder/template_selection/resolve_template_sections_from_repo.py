# nodes/landing_page_builder/template_selection/resolve_template_sections_from_repo.py

"""
Resolve Template Sections From Repo - Filter repo + LLM map sections + Enrich.

- Uses campaign_intent instead of page URL
- Same validation logic (ID encoding/decoding, L0/L1 consistency)
- Parallel execution (3x - one per template)
- Streams tokens via LLM call

This node runs IN PARALLEL - one instance per template!
"""

import time
from typing import Dict, Any, Optional

from langgraph.types import RunnableConfig
from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.nodes.landing_page_builder.template_selection.node_utils.section_repo_for_mapping import (
    prepare_section_candidates_for_llm,
    get_sections_from_llm_response,
)
from wwai_agent_orchestration.prompt_builder.prompt_builder import PromptBuilder
from wwai_agent_orchestration.prompt_builder.prompt_classes.landing_page_builder.template_selection.resolve_template_sections import (
    ResolveTemplateSectionsSpec,
    ResolveTemplateSectionsInput,
)
from wwai_agent_orchestration.utils.llm.model_utils import get_model_config_from_configurable
from wwai_agent_orchestration.utils.landing_page_builder.ui_logs import (
    section_breakdown_html,
    make_ui_execution_log_entry_from_registry,
)

logger = get_logger(__name__)


def _call_llm_for_section_mapping(
    campaign_query: str,
    template_sections: list,
    encoded_section_repo: Dict[str, Any],
    run_on_worker: bool,
    model_config: Any,
) -> list:
    """Call LLM to map template sections to encoded section IDs; returns list of section_mappings."""
    result = ResolveTemplateSectionsSpec.execute(
        builder=PromptBuilder(),
        inp=ResolveTemplateSectionsInput(
            page_query=campaign_query,
            section_info=template_sections,
            section_repo=encoded_section_repo,
        ),
        model_config=model_config,
        run_on_worker=run_on_worker,
    )
    if result.status.value != "success":
        raise Exception(f"Section mapping failed: {result.error}")
    return result.result["sections"]


# ============================================================================
# MAIN NODE
# ============================================================================

@NodeRegistry.register(
    name="resolve_template_sections_from_repo",
    description="Filter repo, map sections via LLM with ID encoding, enrich with screenshots (per template)",
    max_retries=1,
    timeout=180,
    tags=["smb", "llm", "content", "streaming", "validation"],
    display_name="Selecting sections",
    show_node=True,
    show_output=True,
)
def resolve_template_sections_from_repo_node(
    state: Dict[str, Any],
    config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """
    For ONE template: Filter repo + LLM section mapping + Screenshot enrichment.
    
    This node runs IN PARALLEL (3x) - one per template.
    Each instance streams LLM tokens simultaneously!
    
    Args:
        state: Must contain:
            - 'template': Single template dict
            - 'section_repo': List of SMB sections
            - 'campaign_intent': Campaign intent for LLM
        config: Node configuration (RunnableConfig from LangGraph)
        
    Returns:
        Dict with resolved_template_recommendations: [single recommendation dict]
    """
    start_time = time.time()


    # Extract from Send state (section_retrieval_payload in template, injected by section_retrieval_subgraph router)
    template_state = state.get("template") if isinstance(state, dict) else getattr(state, "template", None)
    payload = None
    if template_state:
        payload = template_state.get("section_retrieval_payload") if isinstance(template_state, dict) else getattr(template_state, "section_retrieval_payload", None)
    if not payload:
        raise ValueError("section_retrieval_payload required for resolve_template_sections_from_repo (from Send)")
    template = payload.get("template")
    section_repo = payload.get("section_repo") or []
    campaign_intent = payload.get("campaign_intent")
    if not template or not section_repo:
        raise ValueError("template and section_repo required in section_retrieval_payload")
    
    template_id = template['template_id']
    template_name = template['template_name']
    template_sections = template['section_info']
    
    configurable = config.get("configurable", {}) if config else {}
    run_on_worker = configurable.get('run_on_worker', False)
    max_sections_per_l0_l1 = configurable.get('max_sections_per_l0_l1', 3)
    model_config = get_model_config_from_configurable(configurable)
    
    logger.info(
        f"Starting section retrieval for template: {template_name}",
        node="resolve_template_sections_from_repo",
        template_id=template_id,
        template_name=template_name
    )
    
    # Prepare section candidates and encode IDs for the LLM so we can decode returned IDs back to real section IDs (join-back).
    prep_start = time.time()
    encoded_section_repo, encoded_section_id_to_real_id_mapping = prepare_section_candidates_for_llm(
        section_repo=section_repo,
        template_sections=template_sections,
        max_sections_per_l0_l1=max_sections_per_l0_l1,
    )
    logger.info(
        f"Prepared candidates for {template_name}",
        node="resolve_template_sections_from_repo",
        encoded_count=len(encoded_section_id_to_real_id_mapping),
        prep_duration_ms=round((time.time() - prep_start) * 1000, 2),
    )

    # ========================================================================
    # STEP 3: LLM CALL TO MAP SECTIONS (STREAMS!)
    # ========================================================================
    llm_start = time.time()
    
    logger.info(
        f"Calling LLM for section mapping: {template_name}",
        node="resolve_template_sections_from_repo"
    )
    
    campaign_query = campaign_intent.campaign_query if hasattr(campaign_intent, "campaign_query") else campaign_intent.get("campaign_query")
    section_mappings = _call_llm_for_section_mapping(
        campaign_query=campaign_query,
        template_sections=template_sections,
        encoded_section_repo=encoded_section_repo,
        run_on_worker=run_on_worker,
        model_config=model_config,
    )

    llm_duration = (time.time() - llm_start) * 1000
    
    logger.info(
        f"LLM returned {len(section_mappings)} section mappings for {template_name}",
        node="resolve_template_sections_from_repo",
        llm_duration_ms=round(llm_duration, 2)
    )
    
    # Decode LLM response to real section IDs, enrich with screenshots.
    result = get_sections_from_llm_response(
        section_mappings=section_mappings,
        id_mapping=encoded_section_id_to_real_id_mapping,
        section_repo=section_repo,
        template_id=template_id,
        template_name=template_name,
    )
    total_duration = (time.time() - start_time) * 1000
    logger.info(
        f"Section retrieval complete for {template_name}",
        node="resolve_template_sections_from_repo",
        template_name=template_name,
        sections_mapped=len(result["section_mappings"]),
        total_duration_ms=round(total_duration, 2),
    )

    ui_output_html = section_breakdown_html(
        template_name=template_name,
        section_mappings=result["section_mappings"],
    )

    return {
        "resolved_template_recommendations": [result],
        "ui_execution_log": [
            make_ui_execution_log_entry_from_registry(
                "resolve_template_sections_from_repo",
                ui_output_html,
                instance_id=template_name,
            )
        ],
    }
