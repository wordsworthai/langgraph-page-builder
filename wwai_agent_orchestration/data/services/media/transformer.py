"""
Transforms MediaItem (provider format) to MediaAsset (matcher format).

Key responsibility: Preserve source information for weighted scoring.
"""
from wwai_agent_orchestration.core.observability.logger import get_logger
from typing import List

from wwai_agent_orchestration.data.providers.models.media_assets import (
    MediaItem,
    ImageLookup,
    VideoLookup,
)
from wwai_agent_orchestration.data.services.models.media_asset import MediaAsset

logger = get_logger(__name__)


def media_item_to_asset(item: MediaItem) -> MediaAsset:
    """
    Transform a MediaItem to MediaAsset.
    
    IMPORTANT: Preserves 'source' field for weighted scoring.
    
    Args:
        item: MediaItem from provider
        
    Returns:
        MediaAsset for matcher
        
    Raises:
        ValueError: If lookup_object structure is invalid
    """
    lookup = item.lookup_object
    
    # Extract dimensions and URL based on media type
    if isinstance(lookup, ImageLookup):
        src = lookup.src
        width = lookup.width
        height = lookup.height
        alt = lookup.alt
        aspect_ratio = lookup.aspect_ratio
        
    elif isinstance(lookup, VideoLookup):
        # For videos, use first source
        if not lookup.sources:
            raise ValueError(f"Video {item.media_id} has no sources")
        
        src = lookup.sources[0].url
        width = lookup.sources[0].width
        height = lookup.sources[0].height
        alt = lookup.alt
        aspect_ratio = lookup.aspect_ratio
        
    else:
        raise ValueError(f"Unknown lookup_object type: {type(lookup)}")
    
    # Build MediaAsset with flattened structure
    # CRITICAL: Preserve 'source' for weighted scoring in matcher
    return MediaAsset(
        src=src,
        width=width,
        height=height,
        media_type=item.media_type,
        meta={
            "media_id": item.media_id,
            "source": item.source,  # IMPORTANT: preserved for scoring
            "shopify_id": lookup.id,
            "alt": alt,
            "aspect_ratio": aspect_ratio,
            # Preserve full lookup_object for reverse conversion
            "lookup_object": lookup.model_dump(),
        }
    )


def batch_transform(items: List[MediaItem]) -> List[MediaAsset]:
    """
    Transform a batch of MediaItems to MediaAssets.
    
    Args:
        items: List of MediaItem from provider
        
    Returns:
        List of MediaAsset for matcher
    """
    assets = []
    skipped = 0
    
    for item in items:
        try:
            asset = media_item_to_asset(item)
            assets.append(asset)
        except Exception as e:
            logger.warning(
                f"Failed to transform media_id={item.media_id}: {e}. Skipping."
            )
            skipped += 1
            continue
    
    if skipped > 0:
        logger.info(
            f"Transformed {len(assets)}/{len(items)} media items "
            f"({skipped} skipped)"
        )
    else:
        logger.info(f"Transformed {len(assets)} media items")
    
    return assets


def asset_to_shopify_image(asset: MediaAsset) -> dict:
    """
    Convert MediaAsset back to Shopify image format.
    
    Args:
        asset: Matched MediaAsset
        
    Returns:
        Dict in Shopify image format
    """
    # If we preserved the original lookup_object, use it
    if "lookup_object" in asset.meta:
        return asset.meta["lookup_object"]
    
    # Otherwise, reconstruct from asset attributes
    return {
        "id": asset.meta.get(
            "shopify_id", 
            f"gid://shopify/MediaImage/{asset.meta.get('media_id')}"
        ),
        "src": asset.src,
        "alt": asset.meta.get("alt"),
        "width": asset.width,
        "height": asset.height,
        "aspect_ratio": asset.aspect_ratio(),
    }


def asset_to_shopify_video(asset: MediaAsset) -> dict:
    """
    Convert MediaAsset back to Shopify video format.
    
    Args:
        asset: Matched MediaAsset (video type)
        
    Returns:
        Dict in Shopify video format
    """
    # If we preserved the original lookup_object, use it
    if "lookup_object" in asset.meta:
        return asset.meta["lookup_object"]
    
    # Otherwise, reconstruct from asset attributes
    # Note: This is a fallback - prefer using preserved lookup_object
    return {
        "id": asset.meta.get(
            "shopify_id", 
            f"gid://shopify/Video/{asset.meta.get('media_id')}"
        ),
        "filename": asset.meta.get("filename", "video.mp4"),
        "alt": asset.meta.get("alt"),
        "aspect_ratio": asset.aspect_ratio(),
        "preview_image": asset.meta.get("preview_image"),
        "sources": asset.meta.get("sources", []),
    }