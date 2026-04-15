# nodes/smb/autopop/content_nodes/html/content_html_agent.py
"""
Content HTML agent node.

Processes all HTML elements (maps, embeds) across all sections in a single node.
Uses placeholder generation for both mock and non-mock modes (no LLM yet).
Builds map embed from business profile when business_id is available.
"""

from typing import Any, Dict, Optional
from langgraph.types import RunnableConfig

from template_json_builder.models.schema_and_code import AutopopulationModuleTypes
from template_json_builder.ipsum_lorem_agents.agent_utils import content_agent_utils
from template_json_builder.ipsum_lorem_agents.default_content_provider import html_content_generator

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils import autopop_helpers
from wwai_agent_orchestration.utils.landing_page_builder.maps.google_maps_embed import build_map_embed_html


def content_html_agent_module(
    imm,
    default_embed_html: Optional[str] = None,
) -> Dict[str, Any]:
    """Autopopulate HTML content for all sections in a single loop.

    Uses build_html_content_from_placeholder for both mock and non-mock modes.
    No section-wise splitting - processes all sections in one pass.

    Args:
        imm: Autopopulation immutable state.
        default_embed_html: Map embed iframe HTML. If None, uses DEFAULT_MAP_EMBED.

    Returns:
        Dict with agent_input and agent_output keyed by module_name and section_id.
    """
    module_name = AutopopulationModuleTypes.CONTENT_HTML.value
    agent_inputs_by_section: Dict[str, Any] = {}
    agent_outputs_by_section: Dict[str, Any] = {}

    embed_html = default_embed_html or html_content_generator.DEFAULT_MAP_EMBED

    for section_id in imm.agents_context.sections.keys():
        section_context = imm.agents_context.sections[section_id]
        if module_name not in section_context.section_module_level_context:
            continue

        agent_input = content_agent_utils.section_specific_content_html_module(
            imm, section_id=section_id
        )
        if not agent_input.element_info:
            continue

        agent_output = html_content_generator.build_html_content_from_placeholder(
            agent_input, default_embed_html=embed_html
        )

        agent_inputs_by_section[section_id] = agent_input.model_dump()
        agent_outputs_by_section[section_id] = agent_output.model_dump()

    return {
        "agent_input": {module_name: agent_inputs_by_section},
        "agent_output": {module_name: agent_outputs_by_section},
    }


@NodeRegistry.register(
    name="content_html_agent",
    description="Autopopulate HTML content (maps, embeds) for all sections in a single node",
    max_retries=1,
    timeout=90,
    tags=["autopopulation", "content", "html"],
    display_name="Populating HTML embeds",
    show_node=False,
    show_output=False,
)
async def content_html_agent(
    state: LandingPageWorkflowState, config: RunnableConfig = None
) -> Dict[str, Any]:
    """Process all HTML elements across all sections in one node."""
    autopop_state = autopop_helpers.get_autopop_state(state)
    imm = await autopop_helpers.resolve_imm(autopop_state, config, full_state=state)

    default_embed_html = None
    business_id = getattr(state.input, "business_id", None) if state.input else None
    if business_id:
        try:
            from wwai_agent_orchestration.data.providers.business_profile_provider import (
                BusinessProfileProvider,
            )

            profile = BusinessProfileProvider().get_by_business_id(business_id)
            default_embed_html = build_map_embed_html(
                formatted_address=profile.formatted_address,
                business_name=profile.business_name,
                address=profile.address,
            )
        except Exception:
            pass  # Fall back to DEFAULT_MAP_EMBED

    res = content_html_agent_module(imm=imm, default_embed_html=default_embed_html)

    delta = {
        "agent_inputs": res["agent_input"],
        "agent_outputs": res["agent_output"],
        "logs": [
            {"level": "info", "msg": "content_html_agent: completed for all sections"}
        ],
    }
    return autopop_helpers.update_autopop_state(state, delta)
