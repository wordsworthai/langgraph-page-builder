"""
Campaign Query Synthesis Prompt Class.

Generates campaign query from business data (Google, Yelp, etc.).
"""

from typing import Dict, Optional, List, Any, Type
from pydantic import BaseModel, Field

from wwai_agent_orchestration.constants import prompt_versions
from wwai_agent_orchestration.prompt_builder import prompt_builder_dataclass
from wwai_agent_orchestration.prompt_builder.prompt_builder import PromptSpec


class CampaignQuery(BaseModel):
    """Campaign query output structure"""
    campaign_query: str = Field(
        description="Brief paragraph describing the business and landing page requirements"
    )


class CampaignQuerySynthesisInput(BaseModel):
    """Raw input from caller - transformed by prepare_input to business_context"""
    business_name: str = Field(description="Name of the business")
    sector: str = Field(description="Industry/sector")
    full_address: str = Field(default="Not available", description="Location")
    google_rating: Optional[float] = None
    google_total_ratings: Optional[int] = None
    google_price_level: Optional[str] = None
    google_types: Optional[List[str]] = None
    yelp_rating: Optional[Any] = None  # str or float from provider
    yelp_review_count: Optional[int] = None
    yelp_categories: Optional[Any] = None  # str or List[str] from provider
    yelp_specialties: Optional[str] = None
    yelp_history: Optional[str] = None
    website_intention: Optional[str] = None
    website_tone: Optional[str] = None


class _CampaignQuerySynthesisPreparedInput(BaseModel):
    """Internal: prepared input with business_context string"""
    business_context: str = ""


def _build_business_context(raw: Dict[str, Any]) -> str:
    """Build the complete business context section from raw input."""
    context_parts = []
    context_parts.append("# Business Information")
    context_parts.append(f"**Business Name:** {raw.get('business_name', '')}")
    context_parts.append(f"**Industry:** {raw.get('sector', '')}")
    context_parts.append(f"**Location:** {raw.get('full_address', 'Not available')}")
    context_parts.append("")

    reputation_lines = []
    if raw.get("google_rating"):
        reputation_lines.append(f"- Google Rating: {raw['google_rating']}/5.0 ({raw.get('google_total_ratings', 0)} reviews)")
    if raw.get("yelp_rating"):
        reputation_lines.append(f"- Yelp Rating: {raw['yelp_rating']}/5.0 ({raw.get('yelp_review_count', 0)} reviews)")
    if reputation_lines:
        context_parts.append("# Reputation & Social Proof")
        context_parts.extend(reputation_lines)
        context_parts.append("")

    if raw.get("google_price_level"):
        price_desc = {"$": "budget-friendly", "$$": "moderate pricing", "$$$": "upscale", "$$$$": "luxury"}.get(
            raw["google_price_level"], "moderate"
        )
        context_parts.append("# Business Positioning")
        context_parts.append(f"- Price Level: {raw['google_price_level']} ({price_desc})")
        context_parts.append("")

    category_lines = []
    if raw.get("google_types"):
        category_lines.append(f"- Business Type: {', '.join(raw['google_types'])}")
    if raw.get("yelp_categories"):
        cats = raw["yelp_categories"]
        cats_str = ", ".join(cats) if isinstance(cats, list) else str(cats)
        category_lines.append(f"- Categories: {cats_str}")
    if category_lines:
        context_parts.append("# Business Categories")
        context_parts.extend(category_lines)
        context_parts.append("")

    if raw.get("yelp_specialties") or raw.get("yelp_history"):
        context_parts.append("# What Makes Them Special")
        if raw.get("yelp_specialties"):
            context_parts.append(f"**Specialties:** {raw['yelp_specialties']}")
        if raw.get("yelp_history"):
            context_parts.append(f"**Background:** {raw['yelp_history']}")
        context_parts.append("")

    context_parts.append("# Website Objectives")
    context_parts.append(f"**Primary Goal:** {raw.get('website_intention', 'generate_leads')}")
    context_parts.append(f"**Desired Tone:** {raw.get('website_tone', 'professional')}")
    context_parts.append("")

    return "\n".join(context_parts)


class CampaignQuerySynthesisSpec(PromptSpec):
    """PromptSpec for generating SMB campaign query from business data."""
    PROMPT_NAME: str = prompt_versions.CAMPAIGN_QUERY_SYNTHESIS_PROMPT_NAME
    PROMPT_VERSION: Optional[str] = prompt_versions.CAMPAIGN_QUERY_SYNTHESIS_PROMPT_VERSION
    TASK: prompt_builder_dataclass.PromptModules = prompt_builder_dataclass.PromptModules.NON_ECOMMERCE_SINGLE_PAGE_QUERY
    MODE: str = "text"
    InputModel = CampaignQuerySynthesisInput
    OutputModel: Type[BaseModel] = CampaignQuery

    @classmethod
    def prepare_input(cls, inp: BaseModel) -> BaseModel:
        """Build business_context from raw input."""
        raw = inp.model_dump()
        raw.setdefault("website_intention", "generate_leads")
        raw.setdefault("website_tone", "professional")
        raw.setdefault("full_address", raw.get("full_address") or "Not available")
        business_context = _build_business_context(raw)
        return _CampaignQuerySynthesisPreparedInput(business_context=business_context)
