"""
Template Section Structure Generation Prompt Class.

Generates 3 template variations with L0/L1 section structure.
Uses valid L0/L1 pairs to prevent LLM from creating invalid combinations.
"""

from typing import Dict, Any, Optional, List, Type
from pydantic import BaseModel, Field
from enum import Enum

from wwai_agent_orchestration.constants import prompt_versions
from wwai_agent_orchestration.prompt_builder import prompt_builder_dataclass
from wwai_agent_orchestration.prompt_builder.prompt_builder import PromptSpec


class TemplateName(str, Enum):
    """Template name options"""
    TEMPLATE_1 = "template_1"
    TEMPLATE_2 = "template_2"
    TEMPLATE_3 = "template_3"


class RecommendedSection(BaseModel):
    """Individual recommended section with L0, L1 classification."""
    section_l0: str = Field(description="L0 level section category (must match valid_section_combinations)")
    section_l1: str = Field(description="L1 level section type (must match valid_section_combinations)")
    section_content_description: str = Field(default="", description="Brief description of section content")
    section_index: Optional[int] = Field(default=None, description="Index of the section")
    section_l2: Optional[str] = Field(default="", description="L2 level detailed section description")
    why: Optional[str] = Field(default="", description="Why this section fits here")


class RecommendedL0L1(BaseModel):
    """Recommended L0/L1 classifications for 3 templates"""
    recommendations: Dict[TemplateName, List[RecommendedSection]] = Field(
        description="Dictionary mapping template names to their list of recommended sections"
    )


class TemplateSectionStructureGenerationInput(BaseModel):
    """Raw input from caller - transformed by prepare_input before LLM call"""
    campaign_query: str = Field(description="Campaign query from step 1")
    type_details: List[Dict[str, Any]] = Field(description="Filtered type details with L0/L1/L2")
    past_context: Optional[Dict[str, Any]] = Field(default=None, description="Past evaluation feedback (if reflection)")


class _TemplateSectionStructurePreparedInput(BaseModel):
    """Internal: prepared input for LLM (built by prepare_input)"""
    page_query: str = ""
    valid_section_combinations: List[Dict[str, str]] = Field(default_factory=list)
    previous_context: str = ""


def _build_valid_combinations_list(type_details: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Build clean list of valid L0/L1/L2 combinations for LLM."""
    valid_combinations = []
    for type_detail in type_details:
        l0 = type_detail.get("section_type_l1")
        l1 = type_detail.get("section_subtype_l2")
        l2 = type_detail.get("Description", "")
        if l0 and l1:
            valid_combinations.append({"section_l0": l0, "section_l1": l1, "section_l2": l2 or ""})
    return valid_combinations


class TemplateSectionStructureGenerationSpec(PromptSpec):
    """PromptSpec for generating SMB template L0/L1 section structures."""
    PROMPT_NAME: str = prompt_versions.TEMPLATE_SECTION_STRUCTURE_GENERATION_PROMPT_NAME
    PROMPT_VERSION: Optional[str] = prompt_versions.TEMPLATE_SECTION_STRUCTURE_GENERATION_PROMPT_VERSION
    TASK: prompt_builder_dataclass.PromptModules = prompt_builder_dataclass.PromptModules.NON_ECOMMERCE_RECOMMENDED_L0_L1
    MODE: str = "text"
    InputModel = TemplateSectionStructureGenerationInput
    OutputModel: Type[BaseModel] = RecommendedL0L1

    @classmethod
    def prepare_input(cls, inp: BaseModel) -> BaseModel:
        """Transform raw input: build valid_section_combinations and previous_context."""
        raw = inp.model_dump()
        type_details = raw.get("type_details", [])
        past_context = raw.get("past_context")
        valid_section_combinations = _build_valid_combinations_list(type_details)
        previous_context = ""
        if past_context:
            previous_context = (
                "An output was generated based on this prompt. Here is the output generated "
                "and feedback for each template. Follow the suggestions provided for each template "
                f"and improve it further. You must adhere to the suggestions: {past_context}"
            )
        return _TemplateSectionStructurePreparedInput(
            page_query=raw.get("campaign_query", ""),
            valid_section_combinations=valid_section_combinations,
            previous_context=previous_context,
        )
