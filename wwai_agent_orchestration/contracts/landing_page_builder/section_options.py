"""
Response models for section categories and sections for replacement (editor).
"""

from typing import Optional

from pydantic import BaseModel, Field


class CategoryResponse(BaseModel):
    """Response model for section categories."""

    key: str = Field(..., description="Normalized category key (e.g. from section_l0)")
    name: str = Field(..., description="Display name for the category")
    description: str = Field(default="", description="Optional description")


class SectionMetadataResponse(BaseModel):
    """Response model for section metadata matching frontend SectionMetadata interface."""

    section_id: str = Field(..., description="Section identifier")
    display_name: str = Field(..., description="Display name (e.g. section_l0 - section_l1)")
    category_key: str = Field(..., description="Normalized category key")
    preview_image_url: Optional[str] = Field(default=None, description="Desktop preview image URL")
    description: Optional[str] = Field(default=None, description="Optional section description")
