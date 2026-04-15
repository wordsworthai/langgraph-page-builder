# nodes/smb/autopop/content_nodes/media/template_level_video.py
"""
Content media template-level video agent node.

Processes all sections together for videos in a single call, enabling deduplication across sections.
Uses template-level optimization for efficiency.
"""

from collections import defaultdict
from typing import Any, Dict, List
from langgraph.types import RunnableConfig

from template_json_builder.autopopulation.autopopulators.graph_state import AutopopulationImmutableState
from template_json_builder.models.schema_and_code import AutopopulationModuleTypes
from template_json_builder.ipsum_lorem_agents.default_content_provider import media_generator
from template_json_builder.ipsum_lorem_agents.agent_utils import media_agent_utils
from template_json_builder.models.autopop_dataclasses.prompt_spec.prompt_dataclasses_media import (
    SectionVideoElementAutopopInputModel,
    SectionVideoElementAutopopOutputModel,
    SectionVideoElementAutopopOutputEntry,
)

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils import autopop_helpers
from wwai_agent_orchestration.utils.landing_page_builder.ui_logs import (
    template_videos_html,
    make_ui_execution_log_entry_from_registry,
)
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.content_nodes.media.media_recommendation_mapper import (
    map_video_recommendations_to_output
)
from wwai_agent_orchestration.core.observability.logger import get_logger

logger = get_logger(__name__)


def content_video_agent_module(
    imm: AutopopulationImmutableState, 
    brand_url: str,
    entity_url: str,
    media_recommendations: Dict[str, Any] = None,
    use_mock: bool = False,
    bypass_prompt_cache: bool = False
) -> Dict[str, Any]:
    """Autopopulate video content for all sections using template-level optimization.
    
    This function implements template-level autopopulation for efficiency:
    1. Build ONE combined SectionVideoElementAutopopInputModel for all sections
    2. Call media_generator.autopopulate_section_videos() once (shared matcher, no reuse)
    3. Split the returned mappings by section_index back to per-section outputs
    
    Args:
        imm: The immutable state containing template and section information
        brand_url: URL of the brand for context
        entity_url: URL of the entity for context
        media_providers_tools_response: Response from media provider tools
        use_mock: Whether to use mock data instead of calling the actual agent
        
    Returns:
        Dict containing agent_input and agent_output with module_name and section_ids as keys
    """
    module_name = AutopopulationModuleTypes.CONTENT_VIDEO.value

    combined_videos: List[Dict[str, Any]] = []  # Store as dicts for Pydantic
    secidx_to_section_id: Dict[int, str] = {}
    per_section_inputs: Dict[str, SectionVideoElementAutopopInputModel] = {}

    # Aggregate all section requests into one input
    for section_id in imm.agents_context.sections.keys():
        # Build a section-scoped input
        section_input: SectionVideoElementAutopopInputModel = media_agent_utils.section_specific_content_media_module(
            imm,
            section_id=section_id,
            data_context={},  # data context will be provided globally below
            module_name=module_name,
            brand_url=brand_url,
            entity_url=entity_url,
        )

        # Track section_index -> section_id
        for entry in section_input.videos:  # field is `videos` for the video input model
            secidx_to_section_id[entry.section_index] = section_id

        # Convert Pydantic models to dicts
        combined_videos.extend([entry.model_dump() for entry in section_input.videos])
        per_section_inputs[section_id] = section_input

    # Single combined input    
    combined_input = SectionVideoElementAutopopInputModel(
        brand_url=brand_url,
        entity_url=entity_url,
        videos=combined_videos,
        data_context={},
    )

    # Use media recommendation mapper (real media) or ipsum lorem (mock)
    if use_mock:
        combined_output = media_generator.autopopulate_section_videos(combined_input)
    else:
        # Map pre-fetched recommendations to output format
        if not media_recommendations:
            logger.warning("No media recommendations provided, falling back to ipsum lorem")
            combined_output = media_generator.autopopulate_section_videos(combined_input)
        else:
            combined_output = map_video_recommendations_to_output(
                combined_input,
                media_recommendations,
                section_index_to_section_id=secidx_to_section_id
            )

    # Split results by section_id via section_index
    per_section_mappings: Dict[str, List[SectionVideoElementAutopopOutputEntry]] = defaultdict(list)
    for mapping in combined_output.mappings:
        sid = secidx_to_section_id.get(mapping.section_index)
        per_section_mappings[sid].append(mapping)

    # Prepare per-section outputs
    agent_input_data = {}
    agent_output_data = {}
    for section_id in imm.agents_context.sections.keys():
        # Convert mappings to dicts for Pydantic
        mappings_list = per_section_mappings.get(section_id, [])
        mappings_dicts = [mapping.model_dump() if hasattr(mapping, 'model_dump') else mapping for mapping in mappings_list]
        out_model = SectionVideoElementAutopopOutputModel(
            mappings=mappings_dicts  # List of dicts - Pydantic will convert to SectionVideoElementAutopopOutputEntry
        )
        agent_input_data[section_id] = per_section_inputs[section_id].model_dump()
        agent_output_data[section_id] = out_model.model_dump()

    return {
        "agent_input": {module_name: agent_input_data},
        "agent_output": {module_name: agent_output_data}
    }


@NodeRegistry.register(
    name="template_level_video",
    description="Autopopulate template-level video content using LLM (processes all sections together for efficiency)",
    max_retries=1,
    timeout=150,
    tags=["autopopulation", "content", "media", "video", "template"],
    display_name="Selecting template videos",
    show_node=True,
    show_output=False,
)
async def content_media_video_template_level_agent(
    state: LandingPageWorkflowState, 
    config: RunnableConfig = None
) -> Dict[str, Any]:
    """Process all sections together for videos using template-level optimization (enables deduplication).
    
    This node processes video content for all sections in a single call,
    allowing the media generator to deduplicate results across sections.
    
    Args:
        state: LandingPageWorkflowState containing autopopulation_langgraph_state
        config: RunnableConfig with store instance
        
    Returns:
        Dict with agent_inputs and agent_outputs for video module
    """
    autopop_state = autopop_helpers.get_autopop_state(state)
    imm = await autopop_helpers.resolve_imm(autopop_state, config, full_state=state)
    
    # Get shared context
    brand_url_val = autopop_helpers.brand_url(autopop_state)
    entity_url_val = autopop_helpers.entity_url(autopop_state)
    media_tools_resp = {}  # TODO: Get from state if available
    use_mock_flag = autopop_helpers.use_mock(autopop_state)
    bypass_prompt_cache = autopop_state.get("bypass_prompt_cache", False)
    
    # Get data_context, business_id, and media_recommendations from state
    meta = autopop_state.get("meta", {})
    media_recommendations = meta.get("media_recommendations", {}).get("videos")
    
    # Process all sections together for videos (template-level optimization)
    video_result = content_video_agent_module(
        imm=imm,
        brand_url=brand_url_val,
        entity_url=entity_url_val,
        media_recommendations=media_recommendations,
        use_mock=use_mock_flag,
        bypass_prompt_cache=bypass_prompt_cache
    )
    
    # Return delta that will be merged by LangGraph's state reducer
    return {
        "autopopulation_langgraph_state": {
            "agent_inputs": video_result["agent_input"],
            "agent_outputs": video_result["agent_output"],
            "logs": [{"level": "info", "msg": "content_media_video_template_level_agent: completed for all sections"}],
        },
        "ui_execution_log": [
            make_ui_execution_log_entry_from_registry("template_level_video", template_videos_html())
        ],
    }
