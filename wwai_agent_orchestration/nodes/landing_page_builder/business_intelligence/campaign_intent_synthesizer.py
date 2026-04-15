# nodes/smb/campaign_intent_synthesizer.py
"""
Campaign Intent Synthesizer Node - LLM creates narrative campaign brief.

Updated to use new clean data models from providers.
No heavy transformation needed - providers already did the work.

Inputs:
- Business name, website intention, website tone (required)
- Query (optional additional context)
- Google Maps data (clean GoogleMapsOutput from provider)
- Yelp data (clean YelpOutput from provider)

Output:
- Narrative campaign brief optimized for template generation
"""

import time
from typing import Dict, Any, Optional
from langgraph.types import RunnableConfig

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import (
    LandingPageWorkflowState,
    CampaignIntent,
    DataCollectionResult,
)
from wwai_agent_orchestration.prompt_builder.prompt_builder import PromptBuilder
from wwai_agent_orchestration.prompt_builder.prompt_classes.landing_page_builder.campaign_intent.campaign_query_synthesis import (
    CampaignQuerySynthesisSpec,
    CampaignQuerySynthesisInput,
)
from wwai_agent_orchestration.utils.llm.model_utils import get_model_config_from_configurable
from wwai_agent_orchestration.utils.landing_page_builder.ui_logs import (
    campaign_intent_html,
    make_ui_execution_log_entry_from_registry,
)

logger = get_logger(__name__)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def build_llm_input(state: LandingPageWorkflowState) -> Dict[str, Any]:
    """
    Build structured input for LLM campaign synthesis.
    
    Uses clean data from providers - minimal transformation needed.
    
    Args:
        state: LandingPageWorkflowState with all business data
        
    Returns:
        Dict with all context for LLM
    """
    inp = state.input
    data = state.data
    llm_input = {
        "business_name": inp.business_name if inp else "",
        "website_intention": inp.website_context.website_intention if inp else "generate_leads",
        "website_tone": inp.website_context.website_tone if inp else "professional",
        "query": (inp.generic_context.query or "") if inp else "",
        "sector": data.derived_sector if data else None,
    }
    
    # Add Google Maps data (already clean from provider)
    google_data = data.google_maps_data if data else None
    if google_data:
        # Data is already clean - just map to LLM-friendly format
        llm_input["google_data"] = {
            "display_name": google_data.get("display_name"),
            "address": google_data.get("formatted_address"),
            "primary_type": google_data.get("primary_type_display") or google_data.get("primary_type"),
            "rating": google_data.get("rating"),
            "review_count": google_data.get("review_count"),
            "editorial_summary": google_data.get("editorial_summary"),
            "price_level": google_data.get("price_level"),
            "phone": google_data.get("phone"),
            "website": google_data.get("website"),
            "hours": google_data.get("hours", []),  # Already a list of strings
            "recent_reviews": google_data.get("recent_reviews", []),  # Already cleaned
            "types": google_data.get("types", []),
        }
    
    # Add Yelp data (already clean from provider)
    yelp_data = data.yelp_data if data else None
    if yelp_data:
        llm_input["yelp_data"] = {
            "business_name": yelp_data.get("business_name"),
            "rating": yelp_data.get("rating"),  # Already float
            "review_count": yelp_data.get("review_count"),
            "specialties": yelp_data.get("specialties"),
            "history": yelp_data.get("history"),
            "services": yelp_data.get("services", []),  # Already a list
            "categories": yelp_data.get("categories", []),  # Already a list
            "year_established": yelp_data.get("year_established"),  # Already int
            "price": yelp_data.get("price"),
        }
    
    return llm_input


def determine_synthesis_method(state: LandingPageWorkflowState) -> str:
    """
    Determine which data sources were used for synthesis.
    
    Args:
        state: LandingPageWorkflowState
        
    Returns:
        Method string for logging/debugging
    """
    data = state.data
    has_google = data is not None and data.google_maps_data is not None
    has_yelp = data is not None and data.yelp_data is not None
    
    if has_google and has_yelp:
        return "llm_with_google_and_yelp"
    elif has_google:
        return "llm_with_google_only"
    elif has_yelp:
        return "llm_with_yelp_only"
    else:
        return "llm_minimal_data"


# ============================================================================
# MAIN NODE
# ============================================================================

@NodeRegistry.register(
    name="campaign_intent_synthesizer",
    description="Synthesize campaign brief from business data using LLM",
    max_retries=1,
    timeout=90,
    tags=["smb", "llm", "synthesis", "streaming"],
    display_name="Understanding your business",
    show_node=True,
    show_output=True,
)
def campaign_intent_synthesizer_node(
    state: LandingPageWorkflowState,
    config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """
    Use LLM to create narrative campaign brief from all business data.
    
    Flow:
    1. Build LLM input from clean provider data
    2. Call LLM (streams tokens automatically)
    3. Validate output with Pydantic
    4. Return campaign intent
    
    Args:
        state: LandingPageWorkflowState with clean data from providers
        config: Node configuration
        
    Returns:
        Dict with campaign_intent
        
    Raises:
        ValueError: If LLM output validation fails
    """
    start_time = time.time()
    config = config or {}
    configurable = config.get("configurable", {})

    # Config options
    run_on_worker = configurable.get("run_on_worker", False)
    model_config = get_model_config_from_configurable(configurable)
    
    synthesis_method = determine_synthesis_method(state)
    
    logger.info(
        "Starting campaign intent synthesis",
        extra={
            "business_name": state.input.business_name if state.input else None,
            "has_google_data": (state.data and state.data.google_maps_data is not None),
            "has_yelp_data": (state.data and state.data.yelp_data is not None),
            "derived_sector": state.data.derived_sector if state.data else None,
            "synthesis_method": synthesis_method,
        }
    )
    
    # ========================================================================
    # STEP 1: Build LLM Input (minimal work - data already clean)
    # ========================================================================
    llm_input = build_llm_input(state)
    
    logger.info(
        f"LLM input prepared ({synthesis_method})",
        extra={"input_keys": list(llm_input.keys())}
    )
    
    # ========================================================================
    # STEP 2: Call LLM
    # ========================================================================
    llm_start = time.time()
    
    try:
        google_data = llm_input.get("google_data", {})
        yelp_data = llm_input.get("yelp_data", {})

        result = CampaignQuerySynthesisSpec.execute(
            builder=PromptBuilder(),
            inp=CampaignQuerySynthesisInput(
                business_name=llm_input["business_name"],
                sector=llm_input.get("sector") or "",
                full_address=google_data.get("address", "Not available"),
                google_rating=google_data.get("rating"),
                google_total_ratings=google_data.get("review_count"),
                google_price_level=google_data.get("price_level"),
                google_types=google_data.get("types"),
                yelp_rating=yelp_data.get("rating"),
                yelp_review_count=yelp_data.get("review_count"),
                yelp_categories=yelp_data.get("categories"),
                yelp_specialties=yelp_data.get("specialties"),
                yelp_history=yelp_data.get("history"),
                website_intention=llm_input["website_intention"],
                website_tone=llm_input["website_tone"],
            ),
            model_config=model_config,
            run_on_worker=run_on_worker,
            bypass_prompt_cache=True,
        )
        
        if result.status.value != "success":
            raise Exception(f"LLM call failed: {result.error}")
        
        llm_duration = (time.time() - llm_start) * 1000
        
        logger.info(
            "✅ LLM synthesis complete",
            extra={"llm_duration_ms": round(llm_duration, 2)}
        )
        
        campaign_brief = result.result
        
        if not isinstance(campaign_brief, dict) or "campaign_query" not in campaign_brief:
            raise ValueError(f"LLM returned invalid structure: {type(campaign_brief)}")
        
    except Exception as e:
        logger.error(f"❌ Campaign synthesis failed: {e}")
        raise
    
    # ========================================================================
    # STEP 3: Validate Output
    # ========================================================================
    try:
        campaign_intent = CampaignIntent(**campaign_brief)
        
        logger.info(
            "Campaign intent validated",
            extra={"brief_length": len(campaign_intent.campaign_query)}
        )
        
    except Exception as e:
        logger.error(f"❌ Campaign intent validation failed: {e}")
        raise ValueError(f"Invalid campaign intent from LLM: {e}")
    
    # ========================================================================
    # STEP 4: Build Result
    # ========================================================================
    total_duration = (time.time() - start_time) * 1000
        
    logger.info(
        "✅ Campaign intent synthesis complete",
        extra={
            "synthesis_method": synthesis_method,
            "total_duration_ms": round(total_duration, 2),
        }
    )
    
    full_query = campaign_intent.campaign_query
    ui_output_html = campaign_intent_html(full_query=full_query)

    return {
        "data": DataCollectionResult(campaign_intent=campaign_intent),
        "ui_execution_log": [
            make_ui_execution_log_entry_from_registry("campaign_intent_synthesizer", ui_output_html)
        ],
    }