"""
Template Evaluation Prompt Class.

Evaluates generated template variations for quality.
Provides score, advantages, disadvantages, and improvement suggestions.
"""

from typing import Dict, Any, Optional, List, Type
from pydantic import BaseModel, Field

from wwai_agent_orchestration.constants import prompt_versions
from wwai_agent_orchestration.prompt_builder import prompt_builder_dataclass
from wwai_agent_orchestration.prompt_builder.prompt_builder import PromptSpec


class ImprovementSuggestion(BaseModel):
    """Single improvement suggestion"""
    operation: str = Field(description="Type of operation: add, remove, reorder, or modify")
    section: str = Field(description="Section L0 - L1 combination")
    reasoning: str = Field(description="Explanation for the suggestion")


class TemplateEvaluation(BaseModel):
    """Evaluation result for a single template."""
    advantages: List[str] = Field(
        description="Advantages and strengths of this section order for the business"
    )
    disadvantages: List[str] = Field(
        description="Disadvantages and weaknesses of this section order"
    )
    improvement_suggestions: List[ImprovementSuggestion] = Field(
        description="Specific suggestions to improve the choice or order of sections"
    )
    score: int = Field(
        description="Score out of 10 (0=unusable, 10=perfect). Be heavily critical.",
        ge=0,
        le=10
    )


class TemplateEvaluationInput(BaseModel):
    """Input for template evaluation prompt"""
    generator_response: List[Dict[str, Any]] = Field(description="Template section list (L0/L1 order)")
    page_query: str = Field(description="Campaign query from step 1")
    type_details: List[Dict[str, Any]] = Field(description="Filtered type details (possible sections)")


class TemplateEvaluationSpec(PromptSpec):
    """PromptSpec for evaluating SMB template quality."""
    PROMPT_NAME: str = prompt_versions.TEMPLATE_EVALUATION_PROMPT_NAME
    PROMPT_VERSION: Optional[str] = prompt_versions.TEMPLATE_EVALUATION_PROMPT_VERSION
    TASK: prompt_builder_dataclass.PromptModules = prompt_builder_dataclass.PromptModules.NON_ECOMMERCE_PAGE_EVALUATOR
    MODE: str = "text"
    InputModel = TemplateEvaluationInput
    OutputModel: Type[BaseModel] = TemplateEvaluation
