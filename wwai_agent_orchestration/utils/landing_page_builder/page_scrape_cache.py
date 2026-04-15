"""
Cached page scrape utility.

Fetches page scrape data (structured content + screenshot S3 URL) with MongoDB caching.
Used by page_context_extractor when ScrapingBee text or screenshot intent is enabled.
"""

from typing import Dict, Any, Optional

from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.data.providers.scraping_bee_provider import WebScrapingProvider
from wwai_agent_orchestration.utils.landing_page_builder.url_context_cache import (
    generate_url_context_cache_key,
    get_cached_url_context,
    save_url_context_cache,
)
from wwai_agent_orchestration.utils.landing_page_builder.screenshot_utils import (
    compress_screenshot_to_jpeg_bytes,
    upload_screenshot_to_s3,
)

logger = get_logger(__name__)

METHOD_SCRAPE_RAW = "scrape_raw"


def get_cached_page_scrape_data(
    page_url: str,
    generation_version_id: Optional[str] = None,
    use_cache: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Get page scrape data (structured content + screenshot S3 URL) with caching.

    If use_cache=False, skips cache lookup and save; always scrapes fresh.

    Returns:
        Dict with structured_content, screenshot_s3_url, credits_used; or None on failure.
    """
    if use_cache:
        cache_key = generate_url_context_cache_key(page_url, METHOD_SCRAPE_RAW)
        cached = get_cached_url_context(cache_key)
        if cached and cached.get("structured_content") is not None:
            logger.info("Scrape data from cache (includes S3 URL)")
            return cached

    try:
        provider = WebScrapingProvider()
        scrape_result = provider.scrape_page_for_context(
            url=page_url,
            device="desktop",
            process_content=True,
        )
        if not scrape_result.get("success"):
            raise ValueError(scrape_result.get("error_message") or "Scrape failed")

        raw = scrape_result.get("raw") or {}
        screenshot_s3_url = None
        screenshot_base64 = raw.get("screenshot_base64")
        if screenshot_base64:
            jpeg_bytes = compress_screenshot_to_jpeg_bytes(screenshot_base64)
            if jpeg_bytes:
                screenshot_s3_url = upload_screenshot_to_s3(jpeg_bytes, generation_version_id)
                logger.info(
                    "Compressed and uploaded screenshot to S3",
                    original_kb=len(screenshot_base64) * 3 // 4 // 1024,
                )
        structured_content = scrape_result.get("structured_content")

        scrape_data = {
            "structured_content": structured_content,
            "screenshot_s3_url": screenshot_s3_url,
            "credits_used": raw.get("credits_used", 0),
        }

        if use_cache and (structured_content is not None or screenshot_s3_url):
            cache_key = generate_url_context_cache_key(page_url, METHOD_SCRAPE_RAW)
            save_url_context_cache(cache_key, page_url, METHOD_SCRAPE_RAW, scrape_data)

        return scrape_data
    except Exception as e:
        logger.warning(f"ScrapingBee scrape failed: {e}")
        return None
