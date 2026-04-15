# nodes/smb/autopop/content_nodes/media/media_data_context_fetcher.py
"""
Media Data Context Fetcher Node.

Fetches all media recommendations (images and videos) upfront by:
1. Extracting all image/video slots from immutable state
2. Calling media_service once to get all recommendations
3. Storing results in meta.media_recommendations for use by template-level agents
"""

from typing import Any, Dict, List
from langgraph.types import RunnableConfig

from template_json_builder.models.schema_and_code import AutopopulationModuleTypes
from template_json_builder.ipsum_lorem_agents.agent_utils import media_agent_utils
from template_json_builder.models.autopop_dataclasses.prompt_spec.prompt_dataclasses_media import (
    SectionImageElementAutopopInputModel,
    SectionVideoElementAutopopInputModel,
    SectionMediaElementAutopopInputEntry,
    Device,
)

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils import autopop_helpers
from wwai_agent_orchestration.data.services.media.defaults import (
    DEFAULT_IMAGE_RETRIEVAL_SOURCES,
    DEFAULT_VIDEO_RETRIEVAL_SOURCES,
)
from wwai_agent_orchestration.data.services.media.media_service import media_service
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.content_nodes.media.utils import (
    fetch_and_merge_image_recommendations,
)

logger = get_logger(__name__)


def _convert_input_entry_to_media_slot(
    entry: SectionMediaElementAutopopInputEntry,
    section_id: str
) -> Dict[str, Any]:
    """
    Convert SectionMediaElementAutopopInputEntry to MediaSlot.
    
    Uses DESKTOP dimensions (not mobile) for slot size.
    Uses the actual section_id for mapping back.
    
    Args:
        entry: The media entry to convert
        section_id: The actual section_id (e.g., "section_1", "section_2")
        
    Returns:
        MediaSlot with slot_identity containing the section_id
    """
    # Extract desktop dimensions
    desktop_metadata = entry.media_metadata.get(Device.DESKTOP)
    if not desktop_metadata:
        raise ValueError(f"No desktop metadata found for entry {entry.element_id}")
    
    return {
        "width": desktop_metadata.width,
        "height": desktop_metadata.height,
        "slot_identity": {
            "element_id": entry.element_id,
            "block_type": entry.block_type,
            "block_index": entry.block_index,
            "section_id": section_id,
        },
    }


def _extract_image_slots_from_section(
    imm: Any,
    section_id: str,
    brand_url: str,
    entity_url: str
) -> List[Dict[str, Any]]:
    """
    Extract image slots from a single section.
    
    Args:
        imm: Immutable state
        section_id: The section ID to extract from
        brand_url: Brand URL for context
        entity_url: Entity URL for context
        
    Returns:
        Tuple of (list of MediaSlots, dict mapping slot identity key to entry metadata)
    """
    slots: List[Dict[str, Any]] = []
    image_module_name = AutopopulationModuleTypes.CONTENT_IMAGE.value
    
    try:
        # Build section-scoped input to extract slots
        section_input: SectionImageElementAutopopInputModel = media_agent_utils.section_specific_content_media_module(
            imm,
            section_id=section_id,
            data_context={},
            module_name=image_module_name,
            brand_url=brand_url,
            entity_url=entity_url,
        )
        
        # Convert each image entry to MediaSlot
        for entry in section_input.images:
            try:
                slot = _convert_input_entry_to_media_slot(entry, section_id)
                slots.append(slot)
            except Exception as e:
                logger.warning(f"Failed to convert image entry {entry.element_id} to slot: {e}")
                continue
    except Exception as e:
        logger.warning(f"Failed to extract image slots from section {section_id}: {e}")
    
    return slots


def _extract_video_slots_from_section(
    imm: Any,
    section_id: str,
    brand_url: str,
    entity_url: str
) -> List[Dict[str, Any]]:
    """
    Extract video slots from a single section.
    
    Args:
        imm: Immutable state
        section_id: The section ID to extract from
        brand_url: Brand URL for context
        entity_url: Entity URL for context
        
    Returns:
        Tuple of (list of MediaSlots, dict mapping slot identity key to entry metadata)
    """
    slots: List[Dict[str, Any]] = []
    
    video_module_name = AutopopulationModuleTypes.CONTENT_VIDEO.value
    
    try:
        # Build section-scoped input to extract slots
        section_input: SectionVideoElementAutopopInputModel = media_agent_utils.section_specific_content_media_module(
            imm,
            section_id=section_id,
            data_context={},
            module_name=video_module_name,
            brand_url=brand_url,
            entity_url=entity_url,
        )
        
        # Convert each video entry to MediaSlot
        for entry in section_input.videos:
            try:
                slot = _convert_input_entry_to_media_slot(entry, section_id)
                slots.append(slot)
            except Exception as e:
                logger.warning(f"Failed to convert video entry {entry.element_id} to slot: {e}")
                continue
    except Exception as e:
        logger.warning(f"Failed to extract video slots from section {section_id}: {e}")
    
    return slots


def _extract_all_image_slots(
    imm: Any,
    brand_url: str,
    entity_url: str
) -> List[Dict[str, Any]]:
    """
    Extract all image slots from all sections.
    
    Args:
        imm: Immutable state
        brand_url: Brand URL for context
        entity_url: Entity URL for context
        
    Returns:
        Tuple of (list of all MediaSlots, dict mapping slot identity key to entry metadata)
    """
    all_slots: List[Dict[str, Any]] = []
    
    for section_id in imm.agents_context.sections.keys():
        slots = _extract_image_slots_from_section(
            imm, section_id, brand_url, entity_url
        )
        
        # Append all slots and merge identity mappings
        all_slots.extend(slots)
    
    return all_slots


def _extract_all_video_slots(
    imm: Any,
    brand_url: str,
    entity_url: str
) -> List[Dict[str, Any]]:
    """
    Extract all video slots from all sections.
    
    Args:
        imm: Immutable state
        brand_url: Brand URL for context
        entity_url: Entity URL for context
        
    Returns:
        Tuple of (list of all MediaSlots, dict mapping slot identity key to entry metadata)
    """
    all_slots: List[Dict[str, Any]] = []
    
    for section_id in imm.agents_context.sections.keys():
        slots = _extract_video_slots_from_section(
            imm, section_id, brand_url, entity_url
        )
        
        # Append all slots and merge identity mappings
        all_slots.extend(slots)
    
    return all_slots


@NodeRegistry.register(
    name="media_data_context_fetcher",
    description="Fetch all media recommendations upfront for images and videos",
    max_retries=1,
    timeout=60,
    tags=["media", "context", "data-fetch"],
    show_node=False,
)
async def media_data_context_fetcher_node(
    state: LandingPageWorkflowState,
    config: RunnableConfig = None
) -> Dict[str, Any]:
    """
    Fetch all media recommendations (images and videos) upfront.
    
    This node:
    1. Extracts all image/video slots from immutable state
    2. Calls media_service once for images and once for videos
    3. Stores results in autopopulation_langgraph_state.meta.media_recommendations
    
    Args:
        state: LandingPageWorkflowState with state.input.business_id and autopopulation_langgraph_state
        config: Node configuration with store instance
        
    Returns:
        Dict with updated autopopulation_langgraph_state containing media_recommendations
    """
    business_id = state.input.business_id if state.input else None
    if not business_id:
        raise ValueError("business_id is required in state.input for media data context fetcher")
    
    autopop_state = autopop_helpers.get_autopop_state(state)
    imm = await autopop_helpers.resolve_imm(autopop_state, config, full_state=state)
    
    # Get shared context
    brand_url_val = autopop_helpers.brand_url(autopop_state)
    entity_url_val = autopop_helpers.entity_url(autopop_state)
    
    logger.info(
        "Fetching media recommendations for all sections",
        business_id=business_id,
        section_count=len(imm.agents_context.sections)
    )
    
    # ========================================================================
    # EXTRACT IMAGE SLOTS
    # ========================================================================
    image_slots = _extract_all_image_slots(
        imm, brand_url_val, entity_url_val
    )
    
    # ========================================================================
    # EXTRACT VIDEO SLOTS
    # ========================================================================
    video_slots = _extract_all_video_slots(
        imm, brand_url_val, entity_url_val
    )
    
    # ========================================================================
    # FETCH IMAGE RECOMMENDATIONS (partition: logo vs media_service)
    # ========================================================================
    image_recommendations = None
    if image_slots:
        resolved = state.resolved_template_recommendations or []
        image_recommendations = fetch_and_merge_image_recommendations(
            image_slots=image_slots,
            resolved_template_recommendations=resolved,
            business_id=business_id,
            retrieval_sources=DEFAULT_IMAGE_RETRIEVAL_SOURCES,
            logger=logger,
        )
    else:
        logger.info("No image slots found, skipping image recommendations")
    
    # ========================================================================
    # FETCH VIDEO RECOMMENDATIONS
    # ========================================================================
    video_recommendations = None
    if video_slots:
        logger.info(f"Fetching {len(video_slots)} video recommendations")
        video_response = media_service.match_videos_for_slots(
            business_id=business_id,
            slots=video_slots,
            retrieval_sources=DEFAULT_VIDEO_RETRIEVAL_SOURCES,
            max_recommendations_per_slot=10,
        )
        video_recommendations = {
            "response": video_response
        }
        logger.info(
            f"Fetched {video_response.get('matched_count', 0)}/{video_response.get('total_slots', 0)} video recommendations"
        )
    else:
        logger.info("No video slots found, skipping video recommendations")
    
    # ========================================================================
    # STORE IN META
    # ========================================================================
    current_autopop_state = state.autopopulation_langgraph_state or {}
    current_meta = current_autopop_state.get("meta", {})
    
    # Update meta with media recommendations
    updated_meta = {
        **current_meta,
        "media_recommendations": {
            "images": image_recommendations,
            "videos": video_recommendations
        }
    }
    
    logger.info(
        "Media recommendations fetched and stored",
        image_slots=len(image_slots),
        video_slots=len(video_slots)
    )
    
    # Return updated state
    return {
        "autopopulation_langgraph_state": {
            **current_autopop_state,
            "meta": updated_meta
        }
    }
