"""
Resolve Template Sections Prompt Class (SMB).

Maps template L0/L1 positions to actual sections from repository.
Uses encoded section IDs for better LLM reasoning.
"""

from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field

from wwai_agent_orchestration.constants import prompt_versions
from wwai_agent_orchestration.prompt_builder import prompt_builder_dataclass
from wwai_agent_orchestration.prompt_builder.prompt_builder import PromptSpec


class MappedSection(BaseModel):
    """Mapped section for a single position"""
    section_index: int = Field(description="Index of the section position")
    section_id: str = Field(description="Section ID from repository (encoded)")
    section_l0: str = Field(description="L0 classification")
    section_l1: str = Field(description="L1 classification")
    content_description: str = Field(description="How to describe the content for this section")
    style_description: str = Field(description="How to style this section")
    reasoning: str = Field(description="Why this section from repository fits this position")


class SectionMapping(BaseModel):
    """Section mappings for all positions"""
    sections: List[MappedSection] = Field(
        description="List of mapped sections, one for each position in the template"
    )


class ResolveTemplateSectionsInput(BaseModel):
    """Input for resolve template sections prompt"""
    page_query: str = Field(description="Campaign query")
    section_info: List[Dict[str, Any]] = Field(description="Template section list (L0/L1 with reasoning)")
    section_repo: Any = Field(
        description="Filtered section repository (encoded IDs). Format: {(L0, L1): [{\"id\": \"encoded_id\", \"layout_description\": \"...\"}]}. Uses tuple keys."
    )


class ResolveTemplateSectionsSpec(PromptSpec):
    """PromptSpec for mapping SMB templates to actual sections from repository."""
    PROMPT_NAME: str = prompt_versions.RESOLVE_TEMPLATE_SECTIONS_PROMPT_NAME
    PROMPT_VERSION: Optional[str] = prompt_versions.RESOLVE_TEMPLATE_SECTIONS_PROMPT_VERSION
    TASK: prompt_builder_dataclass.PromptModules = prompt_builder_dataclass.PromptModules.NON_ECOMMERCE_RECOMMENDED_MAPPING
    MODE: str = "text"
    InputModel = ResolveTemplateSectionsInput
    OutputModel: Type[BaseModel] = SectionMapping
