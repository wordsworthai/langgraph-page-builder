# data_providers/models/media_assets.py
"""
Media Assets data models.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Union, Dict, Any, Literal
from datetime import datetime

from wwai_agent_orchestration.data.services.media.defaults import (
    DEFAULT_IMAGE_RETRIEVAL_SOURCES,
)


# =============================================================================
# LOOKUP OBJECTS (Shopify format)
# =============================================================================

class ImageLookup(BaseModel):
    """Image in Shopify format."""
    id: str                              # "gid://shopify/MediaImage/..."
    src: str
    alt: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    aspect_ratio: Optional[float] = None
    variations: Optional[Dict[str, Any]] = None


class PreviewImage(BaseModel):
    """Video preview/thumbnail image."""
    url: str
    width: int
    height: int
    alt: Optional[str] = None


class VideoSource(BaseModel):
    """Video source variant."""
    format: str
    mime_type: str
    url: str
    width: int
    height: int


class VideoLookup(BaseModel):
    """Video in Shopify format."""
    id: str                              # "gid://shopify/Video/..."
    filename: str
    alt: Optional[str] = None
    aspect_ratio: Optional[float] = None
    preview_image: Optional[PreviewImage] = None
    sources: List[VideoSource] = Field(default_factory=list)


# =============================================================================
# INPUT / OUTPUT
# =============================================================================

class MediaAssetsInput(BaseModel):
    """Input for MediaAssets retrieval."""
    business_id: str
    media_type: str = "all"              # "image" | "video" | "all"
    retrieval_sources: List[Literal["stock", "generated", "google_maps"]] = Field(
        default_factory=lambda: list(DEFAULT_IMAGE_RETRIEVAL_SOURCES),
        description="List of sources to fetch from: generated, google_maps, stock"
    )
    max_results: Optional[int] = None


class MediaItem(BaseModel):
    """Single media item with metadata."""
    media_id: str
    media_type: str                      # "image" | "video"
    source: str                          # "upload" | "stock"
    lookup_object: Union[ImageLookup, VideoLookup]


class MediaAssetsOutput(BaseModel):
    """Media assets output."""
    items: List[MediaItem] = Field(default_factory=list)
    total_count: int = 0
    images_count: int = 0
    videos_count: int = 0
    
    # Metadata
    last_updated: datetime = Field(default_factory=datetime.utcnow)