# nodes/smb/autopop/content_nodes/media/section_agent.py
"""
Content media section agent node.

Processes both image and video content for a single section (runs in parallel for each section).
"""

from typing import Any, Dict
from langgraph.types import RunnableConfig

from template_json_builder.autopopulation.autopopulators.graph_state import (
    AutopopulationLangGraphAgentsState,
    AutopopulationImmutableState,
)
from template_json_builder.models.schema_and_code import AutopopulationModuleTypes
from template_json_builder.ipsum_lorem_agents.agent_utils import media_agent_utils
from template_json_builder.ipsum_lorem_agents.default_content_provider import media_generator
from template_json_builder.models.autopop_dataclasses.prompt_spec.prompt_dataclasses_media import (
    SectionImageElementAutopopInputModel,
    SectionImageElementAutopopOutputModel,
    SectionVideoElementAutopopInputModel,
    SectionVideoElementAutopopOutputModel,
)

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils import autopop_helpers


def content_media_agent_module_single_section(
    imm: AutopopulationImmutableState,
    section_id: str,
    brand_url: str,
    entity_url: str,
    media_providers_tools_response: Dict[str, Any],
    use_mock: bool = False,
    bypass_prompt_cache: bool = False
) -> Dict[str, Any]:
    """Autopopulate both image and video content for a single section (for parallel processing).
    
    Args:
        imm: The immutable state containing template and section information
        section_id: The section ID to process
        brand_url: URL of the brand for context
        entity_url: URL of the entity for context
        media_providers_tools_response: Response from media provider tools
        use_mock: Whether to use mock data instead of calling the actual agent
        bypass_prompt_cache: Whether to bypass prompt cache
        
    Returns:
        Dict containing agent_input and agent_output for both image and video modules for the single section
    """
    image_module_name = AutopopulationModuleTypes.CONTENT_IMAGE.value
    video_module_name = AutopopulationModuleTypes.CONTENT_VIDEO.value
    
    # Process images for this section
    section_image_input: SectionImageElementAutopopInputModel = media_agent_utils.section_specific_content_media_module(
        imm,
        section_id=section_id,
        data_context=media_providers_tools_response,
        module_name=image_module_name,
        brand_url=brand_url,
        entity_url=entity_url,
    )
    
    # Process videos for this section
    section_video_input: SectionVideoElementAutopopInputModel = media_agent_utils.section_specific_content_media_module(
        imm,
        section_id=section_id,
        data_context=media_providers_tools_response,
        module_name=video_module_name,
        brand_url=brand_url,
        entity_url=entity_url,
    )
    
    # Generate outputs
    if use_mock:
        image_output = media_generator.autopopulate_section_images(section_image_input)
        video_output = media_generator.autopopulate_section_videos(section_video_input)
    else:
        image_output = media_generator.autopopulate_section_images(section_image_input)
        video_output = media_generator.autopopulate_section_videos(section_video_input)
        # image_output = prompt_utils.execute_section_image_autopop_prompt(section_image_input, bypass_prompt_cache)
        # video_output = prompt_utils.execute_section_video_autopop_prompt(section_video_input, bypass_prompt_cache)
    
    # Convert outputs to dicts
    image_mappings_dicts = [mapping.model_dump() if hasattr(mapping, 'model_dump') else mapping for mapping in image_output.mappings]
    video_mappings_dicts = [mapping.model_dump() if hasattr(mapping, 'model_dump') else mapping for mapping in video_output.mappings]
    
    image_output_model = SectionImageElementAutopopOutputModel(mappings=image_mappings_dicts)
    video_output_model = SectionVideoElementAutopopOutputModel(mappings=video_mappings_dicts)
    
    return {
        "agent_input": {
            image_module_name: {section_id: section_image_input.model_dump()},
            video_module_name: {section_id: section_video_input.model_dump()}
        },
        "agent_output": {
            image_module_name: {section_id: image_output_model.model_dump()},
            video_module_name: {section_id: video_output_model.model_dump()}
        }
    }


@NodeRegistry.register(
    name="content_media_section_agent",
    description="Autopopulate media content (images/videos) for a specific section using LLM (runs in parallel per section)",
    max_retries=1,
    timeout=150,
    tags=["autopopulation", "content", "media", "section"],
    display_name="Selecting section media",
    show_node=False,
    show_output=False,
)
async def content_media_section_agent(state: Dict[str, Any], config: RunnableConfig = None) -> Dict[str, Any]:
    """Process both image and video content for a single section (runs in parallel for each section).
    
    According to GRAPH_DOCUMENTATION.md, when using Send(), the payload becomes the node's
    entire state. So state here is the Send payload dict.
    """    
    # When using Send(), the payload becomes the entire state
    # So state here is the Send payload dict
    if hasattr(state, 'model_dump'):
        state_dict = state.model_dump()
    else:
        state_dict = state
    
    # Extract data from Send payload (which is now the state)
    section_id = state_dict.get("section_id")
    if not section_id:
        raise ValueError("section_id not found in Send payload for content_media_section_agent")
    
    brand_url = state_dict.get("brand_url", "")
    entity_url = state_dict.get("entity_url", "")
    media_tools_resp = state_dict.get("media_providers_tools_response", {})
    use_mock = state_dict.get("use_mock", False)
    bypass_prompt_cache = state_dict.get("bypass_prompt_cache", False)
    
    # Reconstruct autopop_state from Send payload to resolve imm
    immutable_ref = state_dict.get("immutable_ref", {})
    meta = state_dict.get("meta", {})
    if not (immutable_ref.get("run_id") or meta.get("run_id")):
        raise ValueError("No run_id found in Send payload for content_media_section_agent")

    autopop_state_for_imm = AutopopulationLangGraphAgentsState(
        immutable_ref=immutable_ref,
        meta=meta
    )
    imm = await autopop_helpers.resolve_imm(autopop_state_for_imm, config)
    
    # Process both image and video for this section
    res = content_media_agent_module_single_section(
        imm=imm,
        section_id=section_id,
        brand_url=brand_url,
        entity_url=entity_url,
        media_providers_tools_response=media_tools_resp,
        use_mock=use_mock,
        bypass_prompt_cache=bypass_prompt_cache
    )
    
    # Return delta that will be merged by LangGraph's state reducer
    # Since we're in a subgraph with LandingPageWorkflowState, we need to return results
    # that update autopopulation_langgraph_state
    # The agent_inputs and agent_outputs will be merged across all parallel sections
    return {
        "autopopulation_langgraph_state": {
            "agent_inputs": res["agent_input"],
            "agent_outputs": res["agent_output"],
            "logs": [{"level": "info", "msg": f"content_media_section_agent: completed for section {section_id}"}],
        }
    }
