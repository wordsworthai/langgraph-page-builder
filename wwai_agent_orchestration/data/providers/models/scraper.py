# data_providers/models/scraper.py
"""
ScrapingBee / web-scraping data models.

Single module for assets, validation, section detection, and page/section
scrape I/O. Used by ScrapingBee provider, section processing, and pipeline binaries.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# =============================================================================
# EXTENDED ASSET TYPES (for structured extraction and section data)
# =============================================================================

class WebsiteImageAsset(BaseModel):
    """Image with base_src and type for dedup and source tracking."""
    src: str
    base_src: str
    alt: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    loading: Optional[str] = None
    srcset: Optional[str] = None
    type: str  # 'img_tag' or 'css_background'


class WebsiteVideoAsset(BaseModel):
    """Video with type and optional sources."""
    src: Optional[str] = None
    type: str  # 'video_tag' or 'iframe_embed'
    width: Optional[int] = None
    height: Optional[int] = None
    autoplay: Optional[bool] = None
    loop: Optional[bool] = None
    muted: Optional[bool] = None
    poster: Optional[str] = None
    sources: Optional[List[Dict[str, str]]] = None


class WebsiteEntityLink(BaseModel):
    """Link entity with internal/external flag."""
    url: str
    text: str
    is_internal: bool


# =============================================================================
# VALIDATION
# =============================================================================

class ValidationStats(BaseModel):
    """Stats from structured extraction."""
    page_text_length: int
    images_count: int
    images_quality_count: int
    videos_count: int
    entities_count: int


# =============================================================================
# SECTION DETECTION
# =============================================================================

class SectionInfo(BaseModel):
    """Metadata about a section (full page or individual chunk)."""
    section_id: str
    section_index: int
    is_full_page: bool = False  # True when this section represents the entire page
    # Section-detection fields (only populated for individual sections)
    xpath: Optional[str] = None
    xpath_full: Optional[str] = None
    section_type: Optional[str] = None  # 'shopify', 'replo', 'geometric', 'others', 'user_provided'
    src: Optional[str] = None
    html_url: Optional[str] = None
    html_size_kb: Optional[float] = None
    css_properties: Optional[Dict[str, Any]] = None
    attributes: Optional[Dict[str, str]] = None


class SectionContent(BaseModel):
    """Extracted content (reusable at page and section level)."""
    clean_text: Optional[str] = None
    images: List[WebsiteImageAsset] = Field(default_factory=list)
    videos: List[WebsiteVideoAsset] = Field(default_factory=list)
    entities: List[WebsiteEntityLink] = Field(default_factory=list)
    validation_stats: Optional[ValidationStats] = None


class Section(BaseModel):
    """Section = info (metadata) + content (extracted data)."""
    info: SectionInfo
    content: SectionContent


class SectionDetectionMetadata(BaseModel):
    """Metadata about section detection process."""
    success: bool
    detection_method: str
    validation_passed: bool

    height_coverage: Optional[float] = None
    page_height: Optional[int] = None
    coverage_reason: Optional[str] = None

    pattern_count: int
    geometric_count: int
    raw_sections_count: int
    clean_sections_count: int
    wrappers_removed: int
    invisible_removed: int

    user_provided_count: int = 0
    user_matched_count: int = 0
    user_failed_xpaths: List[Dict[str, Any]] = []

    error: Optional[str] = None


# =============================================================================
# PAGE / SECTION SCRAPE I/O
# =============================================================================

class PageScrapeInput(BaseModel):
    """Input for page-level scrape."""
    url: str
    device: str = "desktop"  # "desktop" | "mobile"
    process_content: bool = False  # False=raw only, True=run processors


class SectionScrapeInput(BaseModel):
    """Input for section-level scrape (with section detection)."""
    url: str
    device: str = "desktop"
    user_xpaths: Optional[List[str]] = None
    process_content: bool = False


class RawScrapeResponse(BaseModel):
    """Raw response from ScrapingBee (shared by page and section scrapes)."""
    html_content: Optional[str] = None
    screenshot_base64: Optional[str] = None
    credits_used: int = 0
    sections_raw: Optional[Dict[str, Any]] = None  # only for section scrapes


class ScrapeOutput(BaseModel):
    """Unified output for page-level or section-level scrape."""
    url: str
    device: str
    success: bool
    raw: Optional[RawScrapeResponse] = None
    sections: List[Section] = Field(default_factory=list)  # page scrape: 1 section (is_full_page=True); section scrape: N sections
    page_content: Optional[SectionContent] = None  # optional full-page extraction (section scrape with process_content=True)
    section_detection_metadata: Optional[SectionDetectionMetadata] = None  # only for section scrapes
    credits_used: int = 0
    processing_time_seconds: float = 0
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None


# Backward compatibility aliases
ExtractedContent = SectionContent
ScrapingBeeInput = PageScrapeInput
