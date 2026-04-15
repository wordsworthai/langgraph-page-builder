# nodes/smb/business_data_extractor.py
"""
Business Data Extractor Node - Fetch Google Maps + Yelp data via providers.

Refactored to use data providers for clean separation of concerns.

Handles:
1. Google Maps data retrieval (from DB via provider)
2. Yelp data retrieval (DB lookup or API scrape via provider)
3. Sector derivation (priority: Google → Yelp → None)

Error handling:
- Google data: Graceful if not found, fail-fast on validation errors
- Yelp data: Graceful on network errors, fail-fast on validation errors
"""

import time
from typing import Dict, Any, Optional
from langgraph.types import RunnableConfig

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState, DataCollectionResult

# Providers
from wwai_agent_orchestration.data.providers.google_maps_provider import (
    GoogleMapsProvider,
    GoogleMapsValidationError,
)
from wwai_agent_orchestration.data.providers.yelp_provider import (
    YelpProvider,
    YelpValidationError,
)

from wwai_agent_orchestration.utils.landing_page_builder.ui_logs import (
    business_data_html,
    make_ui_execution_log_entry_from_registry,
)

logger = get_logger(__name__)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def derive_sector(
    google_data: Optional[Any],
    yelp_data: Optional[Any]
) -> Optional[str]:
    """
    Derive business sector with priority: Google → Yelp → None.
    
    Args:
        google_data: Parsed Google Maps data (or None)
        yelp_data: Parsed Yelp data (or None)
        
    Returns:
        Sector string or None
    """
    # Try Google first (already derived by provider)
    if google_data and google_data.derived_sector:
        return google_data.derived_sector
    
    # Fallback to Yelp (already derived by provider)
    if yelp_data and yelp_data.derived_sector:
        return yelp_data.derived_sector
    
    return None


# ============================================================================
# MAIN NODE
# ============================================================================

@NodeRegistry.register(
    name="business_data_extractor",
    description="Fetch business data from Google Maps and Yelp via providers",
    max_retries=1,
    timeout=40,
    tags=["smb", "data", "providers"],
    display_name="Gathering business data",
    show_node=True,
    show_output=True,
)
def business_data_extractor_node(
    state: LandingPageWorkflowState,
    config: RunnableConfig = None
) -> Dict[str, Any]:
    """
    Extract business data using data providers.
    
    Flow:
    1. Fetch Google Maps data via GoogleMapsProvider (DB only)
    2. Fetch Yelp data via YelpProvider (DB → API if needed)
    3. Derive sector (Google → Yelp → None)
    4. Return clean data for downstream nodes
    
    Args:
        state: LandingPageWorkflowState with business_id and optional yelp_url
        config: Node configuration with rapidapi credentials
        
    Returns:
        Dict with google_maps_data, yelp_data, derived_sector
        
    Raises:
        ValueError: If data validation fails (fail-fast)
    """
    start_time = time.time()
    config = config or {}
    
    # Extract inputs from nested state
    inp = state.input
    business_id = inp.business_id if inp else None
    yelp_url = inp.external_data_context.yelp_url if inp and inp.external_data_context else None

    if not business_id:
        raise ValueError("business_id is required for business_data_extractor")
    
    # Get API credentials from config
    configurable = config.get("configurable", {})
    rapidapi_key = configurable.get("rapidapi_key", "")
    rapidapi_host = configurable.get("rapidapi_host", "yelp-business-api.p.rapidapi.com")
    yelp_timeout = configurable.get("yelp_timeout", 30)
    
    logger.info(
        f"Starting business data extraction for business_id: {business_id}",
        extra={
            "has_yelp_url": bool(yelp_url),
            "has_rapidapi_key": bool(rapidapi_key),
        }
    )
    
    google_data: Optional[Any] = None
    yelp_data: Optional[Any] = None
    google_data_valid = False
    yelp_scraping_success = False
    yelp_scraping_error: Optional[str] = None
    
    # ========================================================================
    # STEP 1: Fetch Google Maps Data
    # ========================================================================
    try:
        google_provider = GoogleMapsProvider()
        google_data = google_provider.get_by_business_id(business_id)
        
        if google_data:
            google_data_valid = True
            logger.info(
                f"✅ Google Maps data retrieved",
                extra={
                    "display_name": google_data.display_name,
                    "derived_sector": google_data.derived_sector,
                }
            )
        else:
            logger.info("No Google Maps data found in DB")
            
    except GoogleMapsValidationError as e:
        # Fail-fast on validation errors
        logger.error(f"❌ Google Maps validation error: {e}")
        raise ValueError(f"Invalid Google Maps data: {e}")
    except Exception as e:
        # Graceful on other errors (DB connection issues, etc.)
        logger.warning(f"⚠️ Google Maps retrieval error (non-fatal): {e}")
    
    # ========================================================================
    # STEP 2: Fetch Yelp Data
    # ========================================================================
    try:
        yelp_provider = YelpProvider(
            rapidapi_key=rapidapi_key,
            rapidapi_host=rapidapi_host,
            timeout=yelp_timeout
        )
        yelp_data = yelp_provider.get_by_business_id(business_id=business_id, yelp_url=yelp_url)
        
        if yelp_data:
            yelp_scraping_success = True
            logger.info(
                f"✅ Yelp data retrieved",
                extra={
                    "business_name": yelp_data.business_name,
                    "derived_sector": yelp_data.derived_sector,
                    "from_api": yelp_data.from_api,
                }
            )
        else:
            yelp_scraping_error = "No Yelp data found or API call failed"
            logger.info("No Yelp data available")
            
    except YelpValidationError as e:
        # Fail-fast on validation errors
        logger.error(f"❌ Yelp validation error: {e}")
        raise ValueError(f"Invalid Yelp data: {e}")
    except Exception as e:
        # Graceful on other errors
        yelp_scraping_error = str(e)
        logger.warning(f"⚠️ Yelp retrieval error (non-fatal): {e}")
    
    # ========================================================================
    # STEP 3: Derive Sector
    # ========================================================================
    derived_sector = derive_sector(google_data, yelp_data)
    
    if derived_sector:
        logger.info(f"Derived sector: {derived_sector}")
    else:
        logger.info("No sector derived from external data")
    
    # ========================================================================
    # STEP 4: Build Result
    # ========================================================================
    duration_ms = (time.time() - start_time) * 1000
    
    logger.info(
        f"✅ Business data extraction complete",
        extra={
            "google_data_valid": google_data_valid,
            "yelp_scraping_success": yelp_scraping_success,
            "derived_sector": derived_sector,
            "duration_ms": round(duration_ms, 2),
        }
    )
    
    ui_output_html = business_data_html(
        google_data=google_data,
        yelp_data=yelp_data,
        derived_sector=derived_sector,
    )

    return {
        "data": DataCollectionResult(
            google_maps_data=google_data.model_dump() if google_data else None,
            yelp_data=yelp_data.model_dump() if yelp_data else None,
            derived_sector=derived_sector,
            google_data_valid=google_data_valid,
            yelp_scraping_success=yelp_scraping_success,
            yelp_scraping_error=yelp_scraping_error,
        ),
        "ui_execution_log": [
            make_ui_execution_log_entry_from_registry("business_data_extractor", ui_output_html)
        ],
    }