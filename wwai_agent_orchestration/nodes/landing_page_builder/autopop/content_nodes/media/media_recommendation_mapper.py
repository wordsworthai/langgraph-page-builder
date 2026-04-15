# nodes/smb/autopop/content_nodes/media/media_recommendation_mapper.py
"""
Media Recommendation Mapper - Maps pre-fetched recommendations to output format.

Takes recommendations from media_data_context_fetcher and maps them to slots,
with deduplication to ensure images/videos aren't reused.
"""

from typing import Any, Dict, List, Set, Optional, Tuple
from collections import defaultdict
import random

from template_json_builder.models.autopop_dataclasses.prompt_spec.prompt_dataclasses_media import (
    SectionImageElementAutopopInputModel,
    SectionImageElementAutopopOutputModel,
    SectionImageElementAutopopOutputEntry,
    SectionVideoElementAutopopInputModel,
    SectionVideoElementAutopopOutputModel,
    SectionVideoElementAutopopOutputEntry,
    ShopifyImageObject,
    ShopifyVideoObject,
)

from wwai_agent_orchestration.core.observability.logger import get_logger

logger = get_logger(__name__)


def _convert_media_service_image_to_shopify_image(
    shopify_image: Dict[str, Any]
) -> ShopifyImageObject:
    """Convert MediaService ShopifyImageObject to autopop ShopifyImageObject."""
    return ShopifyImageObject(
        alt=shopify_image.get("alt") or "",
        aspect_ratio=shopify_image.get("aspect_ratio", 1.0),
        height=shopify_image.get("height", 1),
        id=shopify_image.get("id"),
        src=shopify_image.get("src"),
        width=shopify_image.get("width", 1),
        url=shopify_image.get("src"),  # url field for compatibility
    )


def _convert_media_service_video_to_shopify_video(
    shopify_video: Dict[str, Any]
) -> ShopifyVideoObject:
    """Convert MediaService ShopifyVideoObject to autopop ShopifyVideoObject."""
    # Convert preview image if available
    preview_image = None
    if shopify_video.get("preview_image"):
        preview_image = _convert_media_service_image_to_shopify_image(
            shopify_video["preview_image"]
        )
    
    return ShopifyVideoObject(
        filename=shopify_video.get("filename"),
        alt=shopify_video.get("alt") or "",
        aspect_ratio=shopify_video.get("aspect_ratio", 1.0),
        id=shopify_video.get("id"),
        preview_image=preview_image,
        sources=shopify_video.get("sources", []),
    )


def _group_results_by_slot_identity(
    results: List[Dict[str, Any]]
) -> Dict[Tuple[str, str, str, int], List[Dict[str, Any]]]:
    """
    Group match results by slot identity (section_id, element_id, block_type, block_index).
    
    Multiple results can match the same slot - this groups them for random selection.
    
    Args:
        results: List of match result dictionaries from MediaMatchResponse
        
    Returns:
        Dict mapping (section_id, element_id, block_type, block_index) to list of matching results
    """
    results_by_slot: Dict[Tuple[str, str, str, int], List[Dict[str, Any]]] = defaultdict(list)
    
    for match_result_data in results:
        slot_identity_data = match_result_data.get("slot_identity")
        if not slot_identity_data:
            continue
        
        # Create key from slot identity including section_id
        section_id = slot_identity_data.get("section_id")
        element_id = slot_identity_data.get("element_id")
        block_type = slot_identity_data.get("block_type")
        block_index = slot_identity_data.get("block_index")
        
        # element_id, block_type, and block_index must be present
        # section_id can be None (we'll use empty string as placeholder for None)
        if element_id is not None and block_type is not None and block_index is not None:
            slot_key = (
                section_id if section_id is not None else "",
                element_id,
                block_type,
                block_index
            )
            results_by_slot[slot_key].append(match_result_data)
    
    return results_by_slot


def map_image_recommendations_to_output(
    input_model: SectionImageElementAutopopInputModel,
    media_recommendations: Dict[str, Any],
    section_index_to_section_id: Optional[Dict[int, str]] = None
) -> SectionImageElementAutopopOutputModel:
    """
    Map pre-fetched image recommendations to output format with deduplication.
    
    For each input entry, finds matching recommendations by slot_identity and randomly
    picks one from available options, ensuring deduplication across slots.
    
    Args:
        input_model: SectionImageElementAutopopInputModel with images list
        media_recommendations: Dict from meta.media_recommendations["images"] containing:
            - "response": MediaMatchResponse with results (each result has slot_identity)
            
    Returns:
        SectionImageElementAutopopOutputModel with mapped images
    """
    if not media_recommendations:
        logger.warning("No image recommendations provided, returning empty output")
        return SectionImageElementAutopopOutputModel(mappings=[])
    
    response_data = media_recommendations.get("response", {})
    
    # Extract results from response
    results = response_data.get("results", [])
    if not results:
        logger.warning("No image match results in recommendations")
        return SectionImageElementAutopopOutputModel(mappings=[])
    
    # Group results by slot identity (section_id, element_id, block_type, block_index)
    results_by_slot = _group_results_by_slot_identity(results)
    
    # Track used image URLs for deduplication
    used_image_urls: Set[str] = set()
    output_mappings: List[SectionImageElementAutopopOutputEntry] = []
    
    # Process each input entry and find matching recommendations
    for entry in input_model.images:
        # Get section_id from mapping if available, otherwise try to match without it
        section_id = None
        if section_index_to_section_id:
            section_id = section_index_to_section_id.get(entry.section_index)
        
        # Create lookup key for this entry (with section_id if available)
        if section_id:
            slot_key = (section_id, entry.element_id, entry.block_type, entry.block_index)
            matching_results = results_by_slot.get(slot_key, [])
        else:
            # Fallback: match by (element_id, block_type, block_index) only
            # Find all results that match these components regardless of section_id
            matching_results = []
            for key, results_list in results_by_slot.items():
                if key[1:] == (entry.element_id, entry.block_type, entry.block_index):
                    matching_results.extend(results_list)
        
        if not matching_results:
            logger.debug(
                f"No recommendations found for slot: element_id={entry.element_id}, "
                f"block_type={entry.block_type}, block_index={entry.block_index}"
            )
            continue
        
        # Shuffle matching_results to introduce diversity across different runs
        # This ensures that when the same slot is processed multiple times (e.g., in partial autopop),
        # different images may be selected, providing variety while still respecting deduplication
        # random.shuffle(matching_results)
        
        # Filter out results that have images and aren't already used
        available_results = []
        for match_result_data in matching_results:
            shopify_image_data = match_result_data.get("shopify_image")
            if not shopify_image_data:
                continue
            
            image_url = shopify_image_data.get("src")
            if image_url and image_url not in used_image_urls:
                available_results.append(match_result_data)
        
        # If no unused images available, use any available (fallback)
        if not available_results:
            for match_result_data in matching_results:
                shopify_image_data = match_result_data.get("shopify_image")
                if shopify_image_data:
                    available_results.append(match_result_data)
                    break
        
        if not available_results:
            logger.debug(f"No valid image recommendations for slot: {slot_key}")
            continue
        
        # Randomly pick one from available recommendations
        selected_result = random.choice(available_results)
        shopify_image_data = selected_result.get("shopify_image")
        
        image_src = shopify_image_data.get("src")
        if not image_src:
            logger.warning(f"Image data missing src for slot {slot_key}")
            continue
        used_image_urls.add(image_src)
        
        # Convert to output format
        try:
            image_obj = _convert_media_service_image_to_shopify_image(shopify_image_data)
            
            output_entry = SectionImageElementAutopopOutputEntry(
                section_index=entry.section_index,
                element_id=entry.element_id,
                block_type=entry.block_type,
                block_index=entry.block_index,
                image=image_obj
            )
            output_mappings.append(output_entry)
        except Exception as e:
            logger.warning(f"Failed to create output entry for slot {slot_key}: {e}")
            continue
    
    logger.info(
        f"Mapped {len(output_mappings)} image recommendations "
        f"({len(used_image_urls)} unique images used, "
        f"{len(input_model.images)} input entries processed)"
    )
    
    return SectionImageElementAutopopOutputModel(mappings=output_mappings)


def map_video_recommendations_to_output(
    input_model: SectionVideoElementAutopopInputModel,
    media_recommendations: Dict[str, Any],
    section_index_to_section_id: Optional[Dict[int, str]] = None
) -> SectionVideoElementAutopopOutputModel:
    """
    Map pre-fetched video recommendations to output format with deduplication.
    
    For each input entry, finds matching recommendations by slot_identity and randomly
    picks one from available options, ensuring deduplication across slots.
    
    Args:
        input_model: SectionVideoElementAutopopInputModel with videos list
        media_recommendations: Dict from meta.media_recommendations["videos"] containing:
            - "response": VideoMatchResponse with results (each result has slot_identity)
            
    Returns:
        SectionVideoElementAutopopOutputModel with mapped videos
    """
    if not media_recommendations:
        logger.warning("No video recommendations provided, returning empty output")
        return SectionVideoElementAutopopOutputModel(mappings=[])
    
    response_data = media_recommendations.get("response", {})
    
    # Extract results from response
    results = response_data.get("results", [])
    if not results:
        logger.warning("No video match results in recommendations")
        return SectionVideoElementAutopopOutputModel(mappings=[])
    
    # Group results by slot identity (section_id, element_id, block_type, block_index)
    results_by_slot = _group_results_by_slot_identity(results)
    
    # Track used video IDs for deduplication
    used_video_ids: Set[str] = set()
    output_mappings: List[SectionVideoElementAutopopOutputEntry] = []
    
    # Process each input entry and find matching recommendations
    for entry in input_model.videos:
        # Get section_id from mapping if available, otherwise try to match without it
        section_id = None
        if section_index_to_section_id:
            section_id = section_index_to_section_id.get(entry.section_index)
        
        # Create lookup key for this entry (with section_id if available)
        if section_id:
            slot_key = (section_id, entry.element_id, entry.block_type, entry.block_index)
            matching_results = results_by_slot.get(slot_key, [])
        else:
            # Fallback: match by (element_id, block_type, block_index) only
            # Find all results that match these components regardless of section_id
            matching_results = []
            for key, results_list in results_by_slot.items():
                if key[1:] == (entry.element_id, entry.block_type, entry.block_index):
                    matching_results.extend(results_list)
        
        if not matching_results:
            logger.debug(
                f"No recommendations found for slot: element_id={entry.element_id}, "
                f"block_type={entry.block_type}, block_index={entry.block_index}"
            )
            continue
        
        # Filter out results that have videos and aren't already used
        available_results = []
        for match_result_data in matching_results:
            shopify_video_data = match_result_data.get("shopify_video")
            if not shopify_video_data:
                continue
            
            video_id = shopify_video_data.get("id")
            if video_id and video_id not in used_video_ids:
                available_results.append(match_result_data)
        
        # If no unused videos available, use any available (fallback)
        if not available_results:
            for match_result_data in matching_results:
                shopify_video_data = match_result_data.get("shopify_video")
                if shopify_video_data:
                    available_results.append(match_result_data)
                    break
        
        if not available_results:
            logger.debug(f"No valid video recommendations for slot: {slot_key}")
            continue
        
        # Randomly pick one from available recommendations
        selected_result = random.choice(available_results)
        shopify_video_data = selected_result.get("shopify_video")
        
        video_id = shopify_video_data.get("id")
        if not video_id:
            logger.warning(f"Video data missing id for slot {slot_key}")
            continue
        used_video_ids.add(video_id)
        
        # Convert to output format
        try:
            video_obj = _convert_media_service_video_to_shopify_video(shopify_video_data)
            
            output_entry = SectionVideoElementAutopopOutputEntry(
                section_index=entry.section_index,
                element_id=entry.element_id,
                block_type=entry.block_type,
                block_index=entry.block_index,
                video=video_obj
            )
            output_mappings.append(output_entry)
        except Exception as e:
            logger.warning(f"Failed to create output entry for slot {slot_key}: {e}")
            continue
    
    logger.info(
        f"Mapped {len(output_mappings)} video recommendations "
        f"({len(used_video_ids)} unique videos used, "
        f"{len(input_model.videos)} input entries processed)"
    )
    
    return SectionVideoElementAutopopOutputModel(mappings=output_mappings)
