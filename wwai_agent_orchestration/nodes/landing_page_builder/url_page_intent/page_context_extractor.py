"""
Page context extractor node.

Consolidates 3 extraction methods (Gemini URL context, ScrapingBee text, Screenshot+LLM)
into a single configurable node with MongoDB caching. Uses a single ScrapingBee call
when either text or screenshot extraction is enabled. Screenshots are compressed,
uploaded to S3, and stored as URL in cache. Config controls whether to pass S3 URL
or base64 data URL to the LLM.
"""

import time
from typing import Dict, Any, List, Optional

from langgraph.types import RunnableConfig

from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.contracts.landing_page_builder.user_input import get_page_url_from_state
from wwai_agent_orchestration.prompt_builder.prompt_classes.landing_page_builder.url_context.gemini_extraction import GeminiURLContextExtractor
from wwai_agent_orchestration.prompt_builder.prompt_builder import PromptBuilder
from wwai_agent_orchestration.prompt_builder.prompt_classes.landing_page_builder.campaign_intent.dummy_campaign_intent_generation import (
    ScreenshotIntentExtractionSpec,
    ScreenshotIntentExtractionInput,
)
from wwai_agent_orchestration.prompt_builder import prompt_builder_dataclass
from wwai_agent_orchestration.utils.landing_page_builder.page_scrape_cache import get_cached_page_scrape_data
from wwai_agent_orchestration.utils.landing_page_builder.screenshot_utils import s3_url_to_base64_data_url
from wwai_agent_orchestration.contracts.landing_page_builder.execution_config import (
    DEFAULT_PAGE_CONTEXT_EXTRACTION_CONFIG,
    PageContextExtractionConfig,
)

logger = get_logger(__name__)


def _get_page_extraction_config(state: Dict[str, Any]) -> PageContextExtractionConfig:
    """Resolve page context extraction config from state.execution_config or use default."""
    exec_config = state.get("execution_config")
    if not exec_config:
        return DEFAULT_PAGE_CONTEXT_EXTRACTION_CONFIG
    if isinstance(exec_config, dict):
        pce = exec_config.get("page_context_extraction")
    else:
        pce = getattr(exec_config, "page_context_extraction", None)
    if pce is None:
        return DEFAULT_PAGE_CONTEXT_EXTRACTION_CONFIG
    if isinstance(pce, dict):
        return PageContextExtractionConfig(**pce)
    return pce


def _format_section_content_as_text(content: Optional[Any]) -> str:
    """Format SectionContent or dict as plain text for page context."""
    if content is None:
        return ""
    if hasattr(content, "clean_text") and content.clean_text:
        return content.clean_text
    if isinstance(content, dict) and content.get("clean_text"):
        return content["clean_text"]
    if isinstance(content, dict):
        parts = []
        if content.get("clean_text"):
            parts.append(content["clean_text"])
        if content.get("entities"):
            for e in content["entities"][:20]:
                text = e.get("text") if isinstance(e, dict) else getattr(e, "text", "")
                if text:
                    parts.append(f"- {text}")
        return "\n".join(parts) if parts else str(content)[:2000]
    return str(content)[:2000]


def _extract_screenshot_intent(image_for_llm: str) -> Optional[str]:
    """
    Run screenshot intent extraction via ScreenshotIntentExtractionSpec.
    Returns campaign_query string on success, None otherwise.
    """
    try:
        result = ScreenshotIntentExtractionSpec.execute(
            builder=PromptBuilder(),
            inp=ScreenshotIntentExtractionInput(
                image_labels={
                    image_for_llm: "**Above image**: Full page screenshot for campaign intent analysis"
                }
            ),
        )
        res = getattr(result, "result", None) or {}
        logger.info(
            "Screenshot intent LLM response",
            has_status=hasattr(result, "status"),
            status=getattr(result, "status", None),
            result_type=type(res).__name__,
            result_keys=list(res.keys()) if isinstance(res, dict) else None,
            campaign_query_preview=(
                str(res.get("campaign_query", ""))[:200] + "..."
                if isinstance(res, dict) and res.get("campaign_query")
                else None
            ),
        )
        if hasattr(result, "status") and result.status == prompt_builder_dataclass.Status.SUCCESS:
            campaign_query = res.get("campaign_query") if isinstance(res, dict) else None
            if campaign_query:
                return campaign_query
        logger.warning(
            "Screenshot intent LLM returned no campaign_query",
            result_repr=str(res)[:500] if res else "None",
        )
    except Exception as e:
        logger.warning(f"Screenshot intent extraction failed: {e}")
    return None


@NodeRegistry.register(
    name="page_context_extractor",
    description="Extract page context via Gemini, ScrapingBee text, and/or screenshot intent",
    max_retries=1,
    timeout=180,
    tags=["llm", "intent", "scraper", "gemini"],
)
def page_context_extractor_node(state: Dict[str, Any], config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """
    Extract page context using enabled methods (Gemini, ScrapingBee text, Screenshot).
    Results are concatenated into page_context. Uses MongoDB caching; ScrapingBee
    scrape is done once and both HTML and screenshot are cached (S3 upload before cache).
    """
    start_time = time.time()

    if hasattr(state, "model_dump"):
        state = state.model_dump()

    config = config or {}
    configurable = config.get("configurable") or {}
    page_extraction_config = _get_page_extraction_config(state)
    page_url = get_page_url_from_state(state)
    if not page_url:
        raise ValueError("page_url required for page_context_extractor")

    enable_gemini = page_extraction_config.enable_gemini_context
    enable_scraping_bee = page_extraction_config.enable_scraping_bee_text
    enable_screenshot = page_extraction_config.enable_screenshot_intent
    screenshot_use_base64_for_llm = page_extraction_config.screenshot_use_base64_for_llm
    bypass_gemini_cache = page_extraction_config.bypass_gemini_cache
    bypass_scraping_bee_cache = page_extraction_config.bypass_scraping_bee_cache
    generation_version_id = configurable.get("thread_id") or state.get("input", {}).get("generation_version_id")

    logger.info(
        "Extracting page context",
        page_url=page_url,
        enable_gemini=enable_gemini,
        enable_scraping_bee=enable_scraping_bee,
        enable_screenshot=enable_screenshot,
    )

    context_parts: List[str] = []
    methods_used: List[str] = []

    # 1. Gemini (if enabled)
    if enable_gemini:
        try:
            extractor = GeminiURLContextExtractor()
            gemini_result = extractor.execute_gemini_url_call(
                page_url, use_cache=not bypass_gemini_cache
            )
            if gemini_result and gemini_result.response_text:
                context_parts.append(f"--- Gemini Context ---\n{gemini_result.response_text}")
                methods_used.append("gemini")
        except Exception as e:
            logger.warning(f"Gemini extraction failed: {e}")

    # 2. ScrapingBee shared call (if text OR screenshot enabled)
    scrape_data = None
    if enable_scraping_bee or enable_screenshot:
        try:
            scrape_data = get_cached_page_scrape_data(
                page_url,
                generation_version_id=generation_version_id,
                use_cache=not bypass_scraping_bee_cache,
            )
            if scrape_data:
                logger.info("Scrape data retrieved (from cache or fresh)")
        except Exception as e:
            logger.warning(f"ScrapingBee scrape failed: {e}")

    # 2a. ScrapingBee text (from structured_content.clean_text only)
    if enable_scraping_bee and scrape_data:
        text = _format_section_content_as_text(scrape_data.get("structured_content"))
        if text:
            context_parts.append(f"--- ScrapingBee Text ---\n{text}")
            methods_used.append("scraping_bee")

    # 2b. Screenshot intent (from scrape_data S3 URL + LLM)
    # Config controls: pass S3 URL directly or download and pass base64 data URL
    # Not cached - always run fresh to avoid stale/error responses
    if enable_screenshot and scrape_data:
        screenshot_s3_url = scrape_data.get("screenshot_s3_url")
        if not screenshot_s3_url:
            logger.warning(
                "Screenshot enabled but no screenshot_s3_url in scrape data. "
                "Clear scrape_raw cache and re-run to get fresh screenshot."
            )
        else:
            if screenshot_use_base64_for_llm:
                image_for_llm = s3_url_to_base64_data_url(screenshot_s3_url)
                if not image_for_llm:
                    logger.warning("Failed to fetch screenshot from S3 as base64, skipping")
                    image_for_llm = None
            else:
                image_for_llm = screenshot_s3_url

            if image_for_llm:
                campaign_query = _extract_screenshot_intent(image_for_llm)
                if campaign_query:
                    context_parts.append(f"--- Screenshot Intent ---\n{campaign_query}")
                    methods_used.append("screenshot")
                    logger.info("Screenshot intent extracted", length=len(campaign_query))

    page_context = "\n\n".join(context_parts) if context_parts else ""
    if not page_context:
        logger.warning("No page context extracted from any method")

    duration_ms = (time.time() - start_time) * 1000
    logger.info(
        "Page context extraction complete",
        methods_used=methods_used,
        context_length=len(page_context),
        duration_ms=round(duration_ms, 2),
    )

    return {
        "data": {
            "page_context": page_context,
            "extraction_methods_used": methods_used,
        },
    }
