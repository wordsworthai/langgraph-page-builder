# nodes/smb/autopop/content_nodes/media/fanout.py
"""
Content media fanout conditional edge function.

Spawns parallel section media content nodes using LangGraph Send().
"""

from langgraph.types import Send, RunnableConfig

from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils import autopop_helpers


async def content_media_fanout(state: LandingPageWorkflowState, config: RunnableConfig = None):
    """Conditional edge function that spawns parallel section media content nodes."""
    autopop_state = autopop_helpers.get_autopop_state(state)
    imm = await autopop_helpers.resolve_imm(autopop_state, config, full_state=state)
    section_ids = list(imm.agents_context.sections.keys())
    
    # Prepare shared data to include in each Send payload
    # According to GRAPH_DOCUMENTATION.md, Send payloads become the node's entire state
    # So we need to include all necessary data in each Send
    brand_url_val = autopop_helpers.brand_url(autopop_state)
    entity_url_val = autopop_helpers.entity_url(autopop_state)
    media_tools_resp = {}
    use_mock_flag = autopop_helpers.use_mock(autopop_state)
    bypass_prompt_cache = autopop_state.get("bypass_prompt_cache", False)
    
    # Create a Send for EACH section - this spawns parallel execution paths!
    return [
        Send("content_media_section_agent", {
            "section_id": section_id,
            "brand_url": brand_url_val,
            "entity_url": entity_url_val,
            "media_providers_tools_response": media_tools_resp,
            "use_mock": use_mock_flag,
            "bypass_prompt_cache": bypass_prompt_cache,
            # Include the immutable_ref so we can resolve imm in the section node
            "immutable_ref": autopop_state.get("immutable_ref", {}),
            "meta": autopop_state.get("meta", {})
        })
        for section_id in section_ids
    ]
