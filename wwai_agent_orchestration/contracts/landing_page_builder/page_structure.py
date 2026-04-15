"""
Page structure metadata for template build output.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from template_json_builder.models.template_build_output import TemplateBuildOutput


class PageStructureInfo(BaseModel):
    """Page-level metadata and section grouping for a template."""
    page_type: str
    header_unique_ids: List[str] = Field(default_factory=list)
    body_unique_ids: List[str] = Field(default_factory=list)
    footer_unique_ids: List[str] = Field(default_factory=list)


class TemplateWithPageInfo(BaseModel):
    """Template build output plus page structure metadata."""

    template_build_output: TemplateBuildOutput
    page_structure_info: PageStructureInfo
