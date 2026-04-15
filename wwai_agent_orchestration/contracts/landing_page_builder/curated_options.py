"""
Response models for curated pages and template options (editor).
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class CuratedPageOption(BaseModel):
    """Single curated page option from MongoDB curated_pages collection."""

    page_path: str = Field(..., description="Path of the curated page")
    page_title: str = Field(..., description="Title of the curated page")
    page_description: Optional[str] = Field(
        default=None,
        description="Optional page description",
    )
    section_ids: List[str] = Field(..., description="List of section IDs in the page")
    section_desktop_urls: List[str] = Field(
        ..., description="List of desktop screenshot URLs for sections"
    )


class CuratedPagesResponse(BaseModel):
    """Response for GET /generations/curated-pages."""

    pages: List[CuratedPageOption] = Field(
        default_factory=list,
        description="List of curated page options",
    )


class TemplateOption(BaseModel):
    """Single template option for the editor (from template_cache)."""

    template_id: str = Field(..., description="Template identifier")
    template_name: str = Field(..., description="Display name")
    section_count: int = Field(..., description="Number of sections")
    index: int = Field(..., description="Index in list (0, 1, 2, ...)")
    is_current: bool = Field(
        default=False,
        description="True if this template is used for the current generation",
    )
    section_ids: List[str] = Field(..., description="List of section IDs in a template")
    section_desktop_urls: Optional[List[str]] = Field(
        default=None,
        description="URLs for section desktop previews",
    )
    intent: Optional[str] = Field(
        default=None,
        description="Website intention for this template",
    )


class TemplateOptionsResponse(BaseModel):
    """Response for GET template options by business_id."""

    options: List[TemplateOption] = Field(
        default_factory=list,
        description="List of template options",
    )
