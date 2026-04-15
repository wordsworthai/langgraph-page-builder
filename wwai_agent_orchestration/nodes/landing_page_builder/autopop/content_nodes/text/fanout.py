# nodes/smb/autopop/content_nodes/text/fanout.py
"""
Content text fanout conditional edge function.

Spawns parallel section content text nodes using LangGraph Send().
"""

from langgraph.types import Send, RunnableConfig

from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils import autopop_helpers
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.content_nodes.text.utils.section_data_context_utils import (
    get_section_id_to_data_context_mapping,
)


async def content_text_fanout(state: LandingPageWorkflowState, config: RunnableConfig = None):
    """Conditional edge function that spawns parallel section content text nodes."""
    autopop_state = autopop_helpers.get_autopop_state(state)
    imm = await autopop_helpers.resolve_imm(autopop_state, config, full_state=state)
    section_ids = list(imm.agents_context.sections.keys())
    
    # Prepare shared data to include in each Send payload
    # According to GRAPH_DOCUMENTATION.md, Send payloads become the node's entire state
    # So we need to include all necessary data in each Send
    brand_url_val = autopop_helpers.brand_url(autopop_state)
    entity_url_val = autopop_helpers.entity_url(autopop_state)
    tools_resp = {}
    use_mock_flag = autopop_helpers.use_mock(autopop_state)
    bypass_prompt_cache = autopop_state.get("bypass_prompt_cache", False)
    
    meta = autopop_state.get("meta", {})
    data_context_full = meta.get("data_context", "")
    data_context_nav = meta.get("data_context_nav", "")
    resolved = state.resolved_template_recommendations or []
    section_id_to_data_context = get_section_id_to_data_context_mapping(
        section_ids=section_ids,
        resolved_template_recommendations=resolved,
        data_context_full=data_context_full,
        data_context_nav=data_context_nav,
    )
    
    # Create a Send for EACH section - this spawns parallel execution paths!
    sends = []
    for section_id in section_ids:
        chosen_data_context = section_id_to_data_context.get(section_id, data_context_full)
        payload_meta = {**meta, "data_context": chosen_data_context}
        
        sends.append(Send("content_text_section_agent", {
            "section_id": section_id,
            "brand_url": brand_url_val,
            "entity_url": entity_url_val,
            "content_providers_tools_response": tools_resp,
            "use_mock": use_mock_flag,
            "bypass_prompt_cache": bypass_prompt_cache,
            "immutable_ref": autopop_state.get("immutable_ref", {}),
            "meta": payload_meta
        }))
    
    return sends
