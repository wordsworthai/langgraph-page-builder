# nodes/smb/autopop/content_nodes/media/template_level_image.py
"""
Content media template-level image agent node.

Processes all sections together for images in a single call, enabling deduplication across sections.
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
    SectionImageElementAutopopInputModel,
    SectionImageElementAutopopOutputModel,
    SectionImageElementAutopopOutputEntry,
)

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils import autopop_helpers
from wwai_agent_orchestration.utils.landing_page_builder.ui_logs import (
    template_images_html,
    make_ui_execution_log_entry_from_registry,
)
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.content_nodes.media.media_recommendation_mapper import (
    map_image_recommendations_to_output
)
from wwai_agent_orchestration.core.observability.logger import get_logger

logger = get_logger(__name__)

def content_image_agent_module(
    imm: AutopopulationImmutableState,
    brand_url: str,
    entity_url: str,
    media_recommendations: Dict[str, Any] = None,
    use_mock: bool = False,
    bypass_prompt_cache: bool = False
) -> Dict[str, Any]:
    """Autopopulate image content for all sections using template-level optimization.
    
    This function implements template-level autopopulation for efficiency:
    1. Build ONE combined SectionImageElementAutopopInputModel for all sections
    2. Call media_generator.autopopulate_section_images() once
    3. Split the returned mappings by section_index back to per-section outputs
    
    Args:
        imm: The immutable state containing template and section information
        brand_url: URL of the brand for context
        entity_url: URL of the entity for context
        use_mock: Whether to use mock data instead of calling the actual agent
        
    Returns:
        Dict containing agent_input and agent_output with module_name and section_ids as keys
    """
    module_name = AutopopulationModuleTypes.CONTENT_IMAGE.value

    # Aggregate across sections
    combined_images: List[Dict[str, Any]] = []  # Store as dicts for Pydantic
    # Map section_index -> section_id for splitting later
    secidx_to_section_id: Dict[int, str] = {}
    # Keep original per-section inputs for debugging/traceability
    per_section_inputs: Dict[str, SectionImageElementAutopopInputModel] = {}

    for section_id in imm.agents_context.sections.keys():
        # Build section-scoped agent input
        section_input: SectionImageElementAutopopInputModel = media_agent_utils.section_specific_content_media_module(
            imm,
            section_id=section_id,
            data_context={},
            module_name=module_name,
            brand_url=brand_url,
            entity_url=entity_url,
        )

        # Track mapping from section_index -> section_id
        for entry in section_input.images:
            secidx_to_section_id[entry.section_index] = section_id

        # Merge images as dicts (convert Pydantic models to dicts)
        combined_images.extend([entry.model_dump() for entry in section_input.images])
        per_section_inputs[section_id] = section_input

    # Build ONE combined input (Pydantic will convert dicts back to models)
    
    combined_input = SectionImageElementAutopopInputModel(
        brand_url=brand_url,
        entity_url=entity_url,
        images=combined_images,  # List of dicts - Pydantic will convert to SectionMediaElementAutopopInputEntry
        data_context={},  # Required field, empty dict since we're using media_recommendations instead
    )

    # Use media recommendation mapper (real media) or ipsum lorem (mock)
    if use_mock:
        combined_output = media_generator.autopopulate_section_images(combined_input)
    else:
        # Map pre-fetched recommendations to output format
        if not media_recommendations:
            logger.warning("No media recommendations provided, falling back to ipsum lorem")
            combined_output = media_generator.autopopulate_section_images(combined_input)
        else:
            combined_output = map_image_recommendations_to_output(
                combined_input,
                media_recommendations,
                section_index_to_section_id=secidx_to_section_id
            )

    # Split back by section_id via section_index
    per_section_mappings: Dict[str, List[SectionImageElementAutopopOutputEntry]] = defaultdict(list)
    for mapping in combined_output.mappings:
        sid = secidx_to_section_id.get(mapping.section_index)
        if sid is not None:
            per_section_mappings[sid].append(mapping)

    # Prepare per-section outputs
    agent_input_data = {}
    agent_output_data = {}
    for section_id in imm.agents_context.sections.keys():
        # Convert mappings to dicts for Pydantic
        mappings_list = per_section_mappings.get(section_id, [])
        mappings_dicts = [mapping.model_dump() if hasattr(mapping, 'model_dump') else mapping for mapping in mappings_list]
        out_model = SectionImageElementAutopopOutputModel(
            mappings=mappings_dicts  # List of dicts - Pydantic will convert to SectionImageElementAutopopOutputEntry
        )
        agent_input_data[section_id] = per_section_inputs[section_id].model_dump()
        agent_output_data[section_id] = out_model.model_dump()

    return {
        "agent_input": {module_name: agent_input_data},
        "agent_output": {module_name: agent_output_data}
    }


@NodeRegistry.register(
    name="template_level_image",
    description="Autopopulate template-level image content using LLM (processes all sections together for efficiency)",
    max_retries=1,
    timeout=150,
    tags=["autopopulation", "content", "media", "image", "template"],
    display_name="Selecting template images",
    show_node=True,
    show_output=False,
)
async def content_media_image_template_level_agent(
    state: LandingPageWorkflowState, 
    config: RunnableConfig = None
) -> Dict[str, Any]:
    """Process all sections together for images using template-level optimization (enables deduplication).
    
    This node processes image content for all sections in a single call,
    allowing the media generator to deduplicate results across sections.
    
    Args:
        state: LandingPageWorkflowState containing autopopulation_langgraph_state
        config: RunnableConfig with store instance
        
    Returns:
        Dict with agent_inputs and agent_outputs for image module
    """
    autopop_state = autopop_helpers.get_autopop_state(state)
    imm = await autopop_helpers.resolve_imm(autopop_state, config, full_state=state)
    
    # Get shared context
    brand_url_val = autopop_helpers.brand_url(autopop_state)
    entity_url_val = autopop_helpers.entity_url(autopop_state)
    use_mock_flag = autopop_helpers.use_mock(autopop_state)
    bypass_prompt_cache = autopop_state.get("bypass_prompt_cache", False)
    
    # Get data_context, business_id, and media_recommendations from state
    meta = autopop_state.get("meta", {})
    media_recommendations = meta.get("media_recommendations", {}).get("images")
    
    # Process all sections together for images (template-level optimization)
    image_result = content_image_agent_module(
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
            "agent_inputs": image_result["agent_input"],
            "agent_outputs": image_result["agent_output"],
            "logs": [{"level": "info", "msg": "content_media_image_template_level_agent: completed for all sections"}],
        },
        "ui_execution_log": [
            make_ui_execution_log_entry_from_registry("template_level_image", template_images_html())
        ],
    }
