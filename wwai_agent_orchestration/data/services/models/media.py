"""
Pydantic schemas for media service requests and responses.

Updated with use_source flag and source-weighted scoring metadata.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

from wwai_agent_orchestration.data.services.media.defaults import (
    DEFAULT_IMAGE_RETRIEVAL_SOURCES,
)


class MediaSlotIdentity(BaseModel):
    """Identifies a slot within a layout/section structure."""
    element_id: Optional[str] = Field(
        None, description="Unique identifier for the element"
    )
    block_type: Optional[str] = Field(
        None, description="Type of block containing the slot (e.g., 'hero', 'gallery')"
    )
    block_index: Optional[int] = Field(
        None, description="Index of block within section (0-based)"
    )
    section_id: Optional[str] = Field(
        None, description="Identifier of the section containing the slot"
    )


class MediaSlot(BaseModel):
    """Represents a slot that needs media."""
    width: int = Field(gt=0, description="Required width in pixels")
    height: int = Field(gt=0, description="Required height in pixels")
    slot_identity: Optional[MediaSlotIdentity] = Field(
        None, description="Identity details of the slot within the layout"
    )


class MediaMatchRequest(BaseModel):
    """Request to match media slots to available assets."""
    business_id: str = Field(description="Business identifier")
    retrieval_sources: List[Literal["stock", "generated", "google_maps"]] = Field(
        default_factory=lambda: list(DEFAULT_IMAGE_RETRIEVAL_SOURCES),
        description="List of sources to fetch from: generated, google_maps, stock"
    )
    slots: List[MediaSlot] = Field(description="List of slots to fill")
    max_recommendations_per_slot: int = Field(
        default=10,
        ge=1,
        description="Maximum number of recommendations to return per slot (default: 10)"
    )
    


# ==================== Match Metadata ====================

class MatchMetadata(BaseModel):
    """Metadata about the match quality including tiered source bonus."""
    fit_score: float = Field(
        description="Final score (dimension_score + source_bonus)"
    )
    source: str = Field(
        description="Media source (google_maps, stock, generated)"
    )
    source_bonus: float = Field(
        description="Additive bonus for source (0.15 for google_maps if excellent, 0.08 if good)"
    )
    dimension_score: float = Field(
        description="Raw dimension fit score (0-1)"
    )
    quality_tier: str = Field(
        description="Quality tier: excellent (>=0.85), good (>=0.70), fair (>=0.50), poor (<0.50)"
    )
    match_type: str = Field(
        description="Type of match (dimension_fit, extreme_fallback)"
    )
    match_reason: str = Field(description="URL-safe reason code")
    match_explanation: str = Field(description="Human-readable explanation")


# ==================== Image Schemas ====================

class ShopifyImageObject(BaseModel):
    """Shopify-compatible image object."""
    id: str
    src: str
    alt: Optional[str] = None
    width: int
    height: int
    aspect_ratio: float


class ImageMatchResult(BaseModel):
    """Result of matching a single image slot."""
    slot_identity: Optional[MediaSlotIdentity] = Field(
        None, description="Identity details of the matched slot"
    )
    shopify_image: Optional[ShopifyImageObject] = Field(
        None, description="Matched image in Shopify format, None if no match"
    )
    match_metadata: Optional[MatchMetadata] = Field(
        None, description="Match quality info, None if no match"
    )


class MediaMatchResponse(BaseModel):
    """Response containing all matched images."""
    results: List[ImageMatchResult] = Field(
        description="Match results for each slot"
    )
    total_slots: int = Field(description="Total number of slots requested")
    matched_count: int = Field(description="Number of successfully matched slots")
    unmatched_count: int = Field(description="Number of unmatched slots")


# ==================== Video Schemas ====================

class ShopifyVideoSource(BaseModel):
    """Video source variant for different formats."""
    format: str = Field(description="Video format (e.g., 'mp4', 'webm')")
    mime_type: str = Field(description="MIME type (e.g., 'video/mp4')")
    url: str = Field(description="Video source URL")
    width: int = Field(description="Video width in pixels")
    height: int = Field(description="Video height in pixels")


class ShopifyVideoObject(BaseModel):
    """Shopify-compatible video object."""
    id: str
    filename: str
    alt: Optional[str] = None
    aspect_ratio: float
    preview_image: Optional[ShopifyImageObject] = Field(
        None, description="Thumbnail/preview image for video"
    )
    sources: List[ShopifyVideoSource] = Field(
        description="Video sources in different formats"
    )


class VideoMatchResult(BaseModel):
    """Result of matching a single video slot."""
    slot_identity: Optional[MediaSlotIdentity] = Field(
        None, description="Identity details of the matched slot"
    )
    shopify_video: Optional[ShopifyVideoObject] = Field(
        None, description="Matched video in Shopify format, None if no match"
    )
    match_metadata: Optional[MatchMetadata] = Field(
        None, description="Match quality info, None if no match"
    )


class VideoMatchResponse(BaseModel):
    """Response containing all matched videos."""
    results: List[VideoMatchResult] = Field(
        description="Match results for each slot"
    )
    total_slots: int = Field(description="Total number of slots requested")
    matched_count: int = Field(description="Number of successfully matched slots")
    unmatched_count: int = Field(description="Number of unmatched slots")