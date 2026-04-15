"""
URL context cache utilities.

MongoDB caching for URL context extraction results (Gemini, ScrapingBee scrape,
screenshot intent). Used by the page_context_extractor node to avoid redundant
API calls to ScrapingBee and Gemini.
"""

import hashlib
import time
from datetime import datetime
from typing import Optional, Dict, Any

from wwai_agent_orchestration.core.database import db_manager
from wwai_agent_orchestration.core.observability.logger import get_logger

logger = get_logger(__name__)

COLLECTION_NAME = "url_context_cache"
DEFAULT_DB_NAME = "template_generation"


def generate_url_context_cache_key(url: str, method: str) -> str:
    """
    Generate deterministic cache key from URL + method.

    Args:
        url: Page URL that was scraped/analyzed
        method: Extraction method (e.g., "gemini", "scrape_raw", "screenshot_intent")

    Returns:
        Cache key string: "url_context_cache:{hash}"
    """
    url_str = (url or "").strip()
    method_str = method or ""
    cache_input = f"{url_str}|{method_str}"
    hash_key = hashlib.md5(cache_input.encode("utf-8")).hexdigest()
    return f"url_context_cache:{hash_key}"


def get_cached_url_context(
    cache_key: str,
    config: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Get cached URL context from MongoDB by cache key.

    Args:
        cache_key: Cache key from generate_url_context_cache_key
        config: Optional config with save_database_name (default: template_generation)

    Returns:
        Cached result dict if found, None otherwise.
        The result contains the stored output (e.g., response_text for gemini,
        html_content/screenshot_s3_url for scrape_raw, campaign_query for screenshot_intent).
    """
    config = config or {}
    start = time.perf_counter()

    try:
        db_name = config.get("save_database_name", DEFAULT_DB_NAME)
        db = db_manager.get_database(db_name)
        collection = db[COLLECTION_NAME]

        document = collection.find_one({"_id": cache_key})

        if document:
            now = datetime.utcnow()
            collection.update_one(
                {"_id": cache_key},
                {"$set": {"last_accessed": now}},
            )

            if "_id" in document:
                document["_id"] = str(document["_id"])

            duration_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "MongoDB get_cached_url_context hit=True",
                cache_key=cache_key,
                duration_ms=round(duration_ms, 2),
            )
            return document.get("result") or document

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "MongoDB get_cached_url_context hit=False",
            cache_key=cache_key,
            duration_ms=round(duration_ms, 2),
        )
        return None

    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.error(
            f"Error retrieving url_context cache: {str(e)}",
            cache_key=cache_key,
            error=str(e),
        )
        return None


def save_url_context_cache(
    cache_key: str,
    url: str,
    method: str,
    result: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Save URL context result to MongoDB.

    Args:
        cache_key: Cache key from generate_url_context_cache_key
        url: Page URL
        method: Extraction method (gemini, scrape_raw, screenshot_intent)
        result: Result dict to cache (must be JSON-serializable)
        config: Optional config with save_database_name

    Returns:
        True if successful, False on error
    """
    config = config or {}
    start = time.perf_counter()

    try:
        db_name = config.get("save_database_name", DEFAULT_DB_NAME)
        db = db_manager.get_database(db_name)
        collection = db[COLLECTION_NAME]

        now = datetime.utcnow()
        existing = collection.find_one({"_id": cache_key})

        # Convert result to dict if it's a Pydantic model
        if hasattr(result, "model_dump"):
            result = result.model_dump()
        elif hasattr(result, "dict"):
            result = dict(result)

        document = {
            "_id": cache_key,
            "cache_key": cache_key,
            "url": url,
            "method": method,
            "result": result,
            "updated_at": now,
            "last_accessed": now,
        }

        if not existing:
            document["created_at"] = now
        else:
            document["created_at"] = existing.get("created_at", now)

        collection.update_one(
            {"_id": cache_key},
            {"$set": document},
            upsert=True,
        )

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "MongoDB save_url_context_cache success=True",
            cache_key=cache_key,
            method=method,
            duration_ms=round(duration_ms, 2),
        )
        return True

    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.error(
            f"Error saving url_context cache: {str(e)}",
            cache_key=cache_key,
            method=method,
            error=str(e),
        )
        return False
