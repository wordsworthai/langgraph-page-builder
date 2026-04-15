# nodes/smb/trade_classifier_node.py

"""
Trade Classifier Node - Classify businesses into trade categories.

Uses LLM to analyze Google Maps + Yelp data and assign relevant trades
from a predefined catalog. Runs in parallel with campaign_intent_synthesizer.

UPDATED: 
- Now uses new provider data format (google_maps_data, yelp_data as dicts)
- Added caching: checks DB for existing classification before calling LLM
- Added force_reclassify config option to bypass cache
"""

import hashlib
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from langgraph.types import RunnableConfig

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.core.database import DocumentNotFoundError
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState, DataCollectionResult
from wwai_agent_orchestration.data.providers.trades_catalog_provider import TradesCatalogProvider
from wwai_agent_orchestration.data.providers.trade_classification_provider import TradeClassificationProvider
from wwai_agent_orchestration.prompt_builder.prompt_builder import PromptBuilder
from wwai_agent_orchestration.prompt_builder.prompt_classes.landing_page_builder.data_preparation.trade_classification import (
    TradeClassificationSpec,
    TradeClassificationInput,
)
from wwai_agent_orchestration.utils.llm.model_utils import get_model_config_from_configurable
from wwai_agent_orchestration.utils.landing_page_builder.ui_logs import (
    make_ui_execution_log_entry_from_registry,
    trade_picked_html,
)

logger = get_logger(__name__)
trade_classification_provider = TradeClassificationProvider()
trades_catalog_provider = TradesCatalogProvider()

# When LLM returns no matching trades (e.g. temple, pilgrimage site), use this placeholder
UNCLASSIFIED_TRADE = "Unclassified"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _ensure_at_least_one_trade(classification_result: Dict[str, Any]) -> None:
    """
    If assigned_trades is empty, inject a single Unclassified entry.
    Business doesn't match any catalog trade (e.g. pilgrimage site, temple).
    Mutates classification_result in place.
    """
    assigned = classification_result.get("assigned_trades", [])
    if not assigned or not any(t.get("trade") for t in assigned):
        business_summary = classification_result.get("business_summary", "") or ""
        classification_result["assigned_trades"] = [
            {
                "trade": UNCLASSIFIED_TRADE,
                "parent_category": "Other",
                "confidence": "low",
                "reasoning": business_summary[:500] if business_summary else "Business does not match any trade in the catalog.",
            }
        ]


def _derive_location_id(
    google_data: Optional[Dict[str, Any]],
    yelp_data: Optional[Dict[str, Any]],
) -> str:
    """
    Derive a stable location identifier for cache keying.
    Priority: place_id > google_maps_url > formatted_address > yelp full_address > default
    Supports both snake_case (parsed) and camelCase (raw) keys.
    """
    if google_data:
        place_id = google_data.get("place_id") or google_data.get("id")
        if place_id and isinstance(place_id, str) and place_id.strip():
            return place_id.strip()
        url = google_data.get("google_maps_url") or google_data.get("googleMapsURI")
        if url and isinstance(url, str) and url.strip():
            return "url:" + hashlib.sha256(url.encode()).hexdigest()[:16]
        addr = google_data.get("formatted_address") or google_data.get("formattedAddress")
        if addr and isinstance(addr, str) and addr.strip():
            return "addr:" + hashlib.sha256(addr.encode()).hexdigest()[:16]
    if yelp_data:
        addr = (
            yelp_data.get("full_address")
            or yelp_data.get("address")
            or yelp_data.get("localized_address")
        )
        if addr and isinstance(addr, str) and addr.strip():
            return "yelp:" + hashlib.sha256(addr.encode()).hexdigest()[:16]
    return "default"


def extract_google_summary(google_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract relevant fields from Google Maps data for LLM.
    
    UPDATED: Now expects dict from GoogleMapsOutput.model_dump()
    
    Args:
        google_data: Dict from GoogleMapsOutput (provider output)
        
    Returns:
        Dict with extracted fields for LLM
    """
    return {
        "display_name": google_data.get("display_name"),
        "primary_type": google_data.get("primary_type_display") or google_data.get("primary_type"),
        "types": google_data.get("types", []),
        "editorial_summary": google_data.get("editorial_summary"),
        "rating": google_data.get("rating"),
        "review_count": google_data.get("review_count"),
        "price_level": google_data.get("price_level")
    }


def extract_yelp_summary(yelp_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract relevant fields from Yelp data for LLM.
    
    UPDATED: Now expects dict from YelpOutput.model_dump()
    
    Args:
        yelp_data: Dict from YelpOutput (provider output)
        
    Returns:
        Dict with extracted fields for LLM
    """
    return {
        "business_name": yelp_data.get("business_name"),
        "categories": yelp_data.get("categories", []),  # Already a list
        "services_offered": yelp_data.get("services", []),  # Field renamed
        "specialties": yelp_data.get("specialties"),
        "history": yelp_data.get("history"),
        "year_established": yelp_data.get("year_established"),
        "rating": yelp_data.get("rating"),
        "review_count": yelp_data.get("review_count")
    }


# ============================================================================
# MAIN NODE
# ============================================================================

@NodeRegistry.register(
    name="trade_classifier",
    description="Classify business into trade categories using LLM",
    max_retries=1,
    timeout=60,
    tags=["smb", "llm", "classification", "parallel"],
    display_name="Business type finalized",
    show_node=True,
    show_output=False,
)
def trade_classifier_node(
    state: LandingPageWorkflowState,
    config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """
    Classify business into relevant trade categories.
    
    This node runs IN PARALLEL with campaign_intent_synthesizer.
    
    UPDATED: Now uses google_maps_data and yelp_data (dicts from providers)
    instead of the old GooglePlacesData/YelpBusinessData types.
    
    Args:
        state: LandingPageWorkflowState with provider data
        config: Node configuration
            - force_reclassify: bool - Skip cache and always run LLM (default: False)
            - run_on_worker: bool - Run LLM on worker (default: False)
            - trade_classification_prompt_version: str - Prompt version (default: "1")
        
    Returns:
        Dict with trade_classification_result
    """
    start_time = time.time()
    config = config or {}
    
    # Extract inputs from nested state
    inp = state.input
    data = state.data
    business_name = inp.business_name if inp else ""
    business_id = inp.business_id if inp else None
    google_data = data.google_maps_data if data else None  # Dict from GoogleMapsOutput
    yelp_data = data.yelp_data if data else None           # Dict from YelpOutput
    
    # Cache key: business_id + location so different map locations get fresh classification
    location_id = _derive_location_id(google_data, yelp_data)
    cache_key = f"{business_id}:{location_id}" if business_id else f"anon:{location_id}"
    
    # Config
    configurable = config.get("configurable", {}) if config else {}
    run_on_worker = configurable.get('run_on_worker', False)
    force_reclassify = configurable.get('force_reclassify', False)  # bypass DB cache
    model_config = get_model_config_from_configurable(configurable)
    
    logger.info(
        "Starting trade classification",
        node="trade_classifier",
        business_name=business_name,
        has_google_data=bool(google_data),
        has_yelp_data=bool(yelp_data),
        has_business_id=bool(business_id),
        force_reclassify=force_reclassify
    )
    
    # ========================================================================
    # STEP 1: Check Cache (existing classification in DB)
    # ========================================================================
    if not force_reclassify:
        try:
            existing_classification = trade_classification_provider.get_by_cache_key(cache_key)
            
            if existing_classification and existing_classification.get("success", True):
                cache_duration = (time.time() - start_time) * 1000
                assigned = existing_classification.get("assigned_trades", [])
                trade_names = [t.get("trade", "") for t in assigned if t.get("trade")]
                
                logger.info(
                    "✅ Using cached trade classification",
                    node="trade_classifier",
                    business_id=str(business_id),
                    trades_count=len(existing_classification.get("assigned_trades", [])),
                    trades=", ".join([t.get("trade", "") for t in existing_classification.get("assigned_trades", [])]),
                    duration_ms=round(cache_duration, 2)
                )
                
                # Remove internal keys from result
                existing_classification.pop("business_id", None)
                existing_classification.pop("cache_key", None)
                _ensure_at_least_one_trade(existing_classification)
                
                assigned_trades = existing_classification.get("assigned_trades", [])
                trade_names = [t.get("trade", "") for t in assigned_trades if t.get("trade")]
                html = trade_picked_html(trades=trade_names)
                
                return {
                    "data": DataCollectionResult(
                        trade_classification_result={
                            "success": True,
                            "from_cache": True,
                            **existing_classification,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    ),
                    "ui_execution_log": [
                        make_ui_execution_log_entry_from_registry("trade_classifier", html)
                    ],
                }
            else:
                logger.info(
                    "No cached classification found, proceeding with LLM",
                    node="trade_classifier"
                )
                
        except Exception as cache_error:
            # Non-fatal: proceed with LLM classification
            logger.warning(
                f"⚠️ Cache lookup failed (non-fatal): {str(cache_error)}",
                node="trade_classifier"
            )
    elif force_reclassify:
        logger.info(
            "force_reclassify=True, skipping cache lookup",
            node="trade_classifier"
        )
    
    # ========================================================================
    # STEP 2: Fetch Trades Catalog from MongoDB
    # ========================================================================
    try:
        trades_catalog = trades_catalog_provider.fetch_trades()
        
        logger.info(
            f"Fetched {len(trades_catalog)} trades from catalog",
            node="trade_classifier"
        )
        
    except DocumentNotFoundError:
        logger.warning(
            "⚠️ No trades found in catalog - skipping classification",
            node="trade_classifier"
        )
        return {
            "data": DataCollectionResult(
                trade_classification_result={
                    "success": False,
                    "error": "no_trades_in_catalog",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        }
    except Exception as e:
        logger.error(
            f"❌ Failed to fetch trades catalog: {str(e)}",
            node="trade_classifier"
        )
        return {
            "data": DataCollectionResult(
                trade_classification_result={
                    "success": False,
                    "error": f"catalog_fetch_failed: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        }
    
    # ========================================================================
    # STEP 3: Extract Business Data for LLM
    # ========================================================================
    google_summary = None
    yelp_summary = None
    
    if google_data:
        google_summary = extract_google_summary(google_data)
        logger.info("Extracted Google Maps summary", node="trade_classifier")
    
    if yelp_data:
        yelp_summary = extract_yelp_summary(yelp_data)
        logger.info("Extracted Yelp summary", node="trade_classifier")
    
    if not google_summary and not yelp_summary:
        logger.warning(
            "⚠️ No Google or Yelp data available - skipping classification",
            node="trade_classifier"
        )
        return {
            "data": DataCollectionResult(
                trade_classification_result={
                    "success": False,
                    "error": "no_business_data",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        }
    
    # ========================================================================
    # STEP 4: Call LLM for Classification
    # ========================================================================
    llm_start = time.time()
    
    try:
        result = TradeClassificationSpec.execute(
            builder=PromptBuilder(),
            inp=TradeClassificationInput(
                business_name=business_name,
                google_data=google_summary or {},
                yelp_data=yelp_summary or {},
                trades_catalog=trades_catalog,
            ),
            model_config=model_config,
            run_on_worker=run_on_worker,
        )
        
        if result.status.value != "success":
            raise Exception(f"LLM call failed: {result.error}")
        
        llm_duration = (time.time() - llm_start) * 1000
        
        classification_result = result.result
        # Normalize to dict for consistent access (PromptSpec may return Pydantic model)
        if hasattr(classification_result, "model_dump"):
            classification_result = classification_result.model_dump()
        _ensure_at_least_one_trade(classification_result)
        
        logger.info(
            "✅ LLM classification complete",
            node="trade_classifier",
            llm_duration_ms=round(llm_duration, 2),
            assigned_trades_count=len(classification_result.get("assigned_trades", [])),
            trades=", ".join([t.get("trade", "") for t in classification_result.get("assigned_trades", [])])
        )
        
    except Exception as e:
        logger.error(
            f"❌ Trade classification LLM failed: {str(e)}",
            node="trade_classifier"
        )
        return {
            "data": DataCollectionResult(
                trade_classification_result={
                    "success": False,
                    "error": f"llm_failed: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        }
    
    # ========================================================================
    # STEP 5: Store Results in MongoDB
    # ========================================================================
    try:
        # Add metadata
        classification_with_meta = {
            **classification_result,
            "business_id": str(business_id) if business_id else None,
            "classified_at": datetime.utcnow().isoformat(),
            "google_types": google_data.get("types") if google_data else None,
            "yelp_categories": yelp_data.get("categories") if yelp_data else None
        }
        
        store_success = trade_classification_provider.save_for_cache_key(
            cache_key=cache_key, trade_assignments=classification_with_meta
        )
            
        if not store_success:
            logger.warning(
                "⚠️ Trade classification storage failed (non-fatal)",
                node="trade_classifier"
            )
    
    except Exception as storage_error:
        logger.error(
            f"Trade classification storage error (non-fatal): {str(storage_error)}",
            node="trade_classifier"
        )
    
    # ========================================================================
    # STEP 6: Return Result
    # ========================================================================
    total_duration = (time.time() - start_time) * 1000
    
    logger.info(
        "✅ Trade classification complete",
        node="trade_classifier",
        total_duration_ms=round(total_duration, 2),
        assigned_trades=len(classification_result.get("assigned_trades", []))
    )
    
    assigned_trades = classification_result.get("assigned_trades", [])
    trade_names = [t.get("trade", "") for t in assigned_trades if t.get("trade")]
    html = trade_picked_html(trades=trade_names)
    
    return {
        "data": DataCollectionResult(
            trade_classification_result={
                "success": True,
                "from_cache": False,
                **classification_result,
                "timestamp": datetime.utcnow().isoformat()
            }
        ),
        "ui_execution_log": [
            make_ui_execution_log_entry_from_registry("trade_classifier", html)
        ],
    }