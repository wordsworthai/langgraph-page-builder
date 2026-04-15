"""
Template recommendations cache utilities.

- Extract trades from state and generate cache key (for lookup/save nodes).
- Get/save template recommendations cache entries in MongoDB (template_cache).
"""

import hashlib
import time
from datetime import datetime
from typing import List, Optional, Dict, Any

from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import (
    LandingPageWorkflowState,
    TradeAssignment,
)
from wwai_agent_orchestration.data.providers.trade_classification_provider import TradeClassificationProvider
from wwai_agent_orchestration.core.database import db_manager
from wwai_agent_orchestration.core.observability.logger import get_logger

logger = get_logger(__name__)
trade_classification_provider = TradeClassificationProvider()


def extract_trades_from_state(
    state: LandingPageWorkflowState,
    business_id: Optional[str] = None
) -> List[str]:
    """
    Extract trade names from state or database.

    Priority:
    1. state.trade_classification_result.assigned_trades (if available)
    2. Query business_types collection using business_id (if provided)
    3. Return empty list (fallback)

    Args:
        state: LandingPageWorkflowState
        business_id: Optional business ID for database lookup

    Returns:
        Sorted list of trade names (strings)
    """
    trade_classification_result = None
    if getattr(state, "data", None):
        trade_classification_result = getattr(state.data, "trade_classification_result", None)
    if trade_classification_result and trade_classification_result.assigned_trades:
        trades = []
        for assignment in trade_classification_result.assigned_trades:
            if isinstance(assignment, TradeAssignment):
                trades.append(assignment.trade)
            elif isinstance(assignment, dict):
                trades.append(assignment.get("trade", ""))
            else:
                trades.append(str(assignment))

        trades = sorted([t for t in trades if t])
        if trades:
            logger.debug(
                "Extracted trades from state",
                trades_count=len(trades),
                trades=trades
            )
            return trades

    if business_id:
        try:
            classification = trade_classification_provider.get_by_business_id(str(business_id))
            if classification and classification.get("assigned_trades"):
                trades = []
                for assignment in classification.get("assigned_trades", []):
                    if isinstance(assignment, dict):
                        trade_name = assignment.get("trade", "")
                        if trade_name:
                            trades.append(trade_name)

                trades = sorted([t for t in trades if t])
                if trades:
                    logger.debug(
                        "Extracted trades from database",
                        business_id=business_id,
                        trades_count=len(trades),
                        trades=trades
                    )
                    return trades
        except Exception as e:
            logger.warning(
                "Failed to fetch trades from database",
                business_id=business_id,
                error=str(e)
            )

    logger.debug("No trades found in state or database")
    return []


def generate_section_cache_key(
    website_intention: str,
    trades: List[str]
) -> str:
    """
    Generate deterministic cache key from website_intention + trades.

    Args:
        website_intention: Website intention string (e.g., "generate_leads", "showcase_services")
        trades: List of trade names (will be sorted)

    Returns:
        Cache key string: "template_cache:{hash}"
    """
    website_intention_str = website_intention or ""
    sorted_trades = sorted(trades)
    trades_string = ",".join(sorted_trades)
    cache_input = f"{website_intention_str}|{trades_string}"
    hash_key = hashlib.md5(cache_input.encode('utf-8')).hexdigest()
    cache_key = f"template_cache:{hash_key}"
    logger.debug(
        "Generated section cache key",
        cache_key=cache_key,
        website_intention=website_intention_str[:50] if website_intention_str else "",
        trades_count=len(trades)
    )
    return cache_key


def get_template_recommendations_by_cache_key(
    cache_key: str,
    config: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Get template recommendations cache entry from MongoDB by cache key.

    Document shape: cache_key_input (website_intention, trades), cache_key_output
    (resolved_template_recommendations). Callers read from doc["cache_key_output"]["resolved_template_recommendations"].

    Args:
        cache_key: Cache key (hash) to look up
        config: Optional configuration dict (save_database_name, default 'template_generation')

    Returns:
        Cached document dict if found, None otherwise.
    """
    config = config or {}
    start = time.perf_counter()

    try:
        db_name = config.get('save_database_name', 'template_generation')
        db = db_manager.get_database(db_name)
        collection = db['template_cache']

        document = collection.find_one({"_id": cache_key})

        if document:
            now = datetime.utcnow()
            collection.update_one(
                {"_id": cache_key},
                {"$set": {"last_accessed": now}}
            )

            if "_id" in document:
                document["_id"] = str(document["_id"])

            duration_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "MongoDB get_template_recommendations_by_cache_key hit=True",
                cache_key=cache_key,
                duration_ms=round(duration_ms, 2),
            )
            output = document.get("cache_key_output") or {}
            logger.debug(
                "Retrieved template recommendations cache entry",
                cache_key=cache_key,
                has_recommendations=bool(output.get("resolved_template_recommendations"))
            )
            return document

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "MongoDB get_template_recommendations_by_cache_key hit=False",
            cache_key=cache_key,
            duration_ms=round(duration_ms, 2),
        )
        logger.debug("Template recommendations cache miss", cache_key=cache_key)
        return None

    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.error(
            f"Error retrieving template recommendations cache: {str(e)}",
            cache_key=cache_key,
            error=str(e),
        )
        logger.info(
            "MongoDB get_template_recommendations_by_cache_key error=True",
            cache_key=cache_key,
            duration_ms=round(duration_ms, 2),
        )
        return None


def save_template_recommendations_cache(
    cache_key: str,
    resolved_template_recommendations: List[Dict[str, Any]],
    trades: List[str],
    website_intention: str,
    config: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Save template recommendations cache entry to MongoDB.

    Document shape: cache_key_input (website_intention, trades), cache_key_output
    (resolved_template_recommendations).

    Args:
        cache_key: Cache key (hash) - used as _id for efficient lookups
        resolved_template_recommendations: List of section-mapped recommendation dicts
        trades: List of trade names (stored sorted in cache_key_input)
        website_intention: Website intention string
        config: Optional configuration dict (save_database_name, default 'template_generation')

    Returns:
        True if successful, False on error
    """
    config = config or {}
    start = time.perf_counter()

    try:
        db_name = config.get('save_database_name', 'template_generation')
        db = db_manager.get_database(db_name)
        collection = db['template_cache']

        now = datetime.utcnow()
        existing = collection.find_one({"_id": cache_key})

        document = {
            "_id": cache_key,
            "cache_key": cache_key,
            "cache_key_input": {
                "website_intention": website_intention,
                "trades": sorted(trades),
            },
            "cache_key_output": {
                "resolved_template_recommendations": resolved_template_recommendations,
            },
            "updated_at": now,
            "last_accessed": now
        }

        if not existing:
            document["created_at"] = now
        else:
            document["created_at"] = existing.get("created_at", now)

        result = collection.update_one(
            {"_id": cache_key},
            {"$set": document},
            upsert=True
        )

        if result.upserted_id or result.matched_count > 0:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "MongoDB save_template_recommendations_cache success=True",
                cache_key=cache_key,
                duration_ms=round(duration_ms, 2),
            )
            logger.info(
                "Saved template recommendations cache entry",
                cache_key=cache_key,
                recommendations_count=len(resolved_template_recommendations),
                trades_count=len(trades),
                is_update=result.matched_count > 0
            )
            return True
        else:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "MongoDB save_template_recommendations_cache success=False",
                cache_key=cache_key,
                duration_ms=round(duration_ms, 2),
            )
            logger.warning(
                "Failed to save template recommendations cache entry",
                cache_key=cache_key,
            )
            return False

    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "MongoDB save_template_recommendations_cache error=True",
            cache_key=cache_key,
            duration_ms=round(duration_ms, 2),
        )
        logger.error(
            f"Error saving template recommendations cache: {str(e)}",
            cache_key=cache_key,
            error=str(e)
        )
        return False
