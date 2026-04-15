"""
Trade Classification Prompt Class.

Classifies businesses into relevant trade categories based on Google Places
and Yelp data using LLM analysis.
"""

from typing import Dict, Any, Optional, List, Type
from pydantic import BaseModel, Field

from wwai_agent_orchestration.constants import prompt_versions
from wwai_agent_orchestration.prompt_builder import prompt_builder_dataclass
from wwai_agent_orchestration.prompt_builder.prompt_builder import PromptSpec


class TradeAssignment(BaseModel):
    """Single trade assignment with reasoning"""
    trade: str = Field(description="Trade identifier from catalog")
    parent_category: str = Field(description="Parent category of the trade")
    confidence: str = Field(description="Confidence level: high, medium, or low")
    reasoning: str = Field(description="Why this trade matches the business (2-3 sentences)")


class TradeClassificationResult(BaseModel):
    """Trade classification result for a business"""
    assigned_trades: List[TradeAssignment] = Field(
        description="Relevant trades for this business (1-4 trades)",
        min_length=0,
        max_length=4
    )
    business_summary: str = Field(description="Brief summary of what the business does")


class TradeClassificationInput(BaseModel):
    """Input for trade classification prompt"""
    business_name: str = Field(description="Name of the business")
    google_data: Dict[str, Any] = Field(default_factory=dict, description="Google Places data")
    yelp_data: Dict[str, Any] = Field(default_factory=dict, description="Yelp data")
    trades_catalog: List[Dict[str, str]] = Field(description="List of available trades")


class TradeClassificationSpec(PromptSpec):
    """PromptSpec for classifying businesses into trade categories."""
    PROMPT_NAME: str = prompt_versions.TRADE_CLASSIFICATION_PROMPT_NAME
    PROMPT_VERSION: Optional[str] = prompt_versions.TRADE_CLASSIFICATION_PROMPT_VERSION
    TASK: prompt_builder_dataclass.PromptModules = prompt_builder_dataclass.PromptModules.TRADE_CLASSIFICATION
    MODE: str = "text"
    InputModel = TradeClassificationInput
    OutputModel: Type[BaseModel] = TradeClassificationResult
