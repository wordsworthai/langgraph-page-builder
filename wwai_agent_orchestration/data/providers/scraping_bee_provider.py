# data_providers/providers/scraping_bee_provider.py
"""
ScrapingBee / Web Scraping providers.

- WebScrapingProvider: New API with scrape_page() and scrape_sections(), raw or process_content.
- _ScrapingBeeClient: Low-level HTTP-only wrapper (internal).
- ScrapingBeeProvider: Legacy; use WebScrapingProvider for new code.
"""

import json
import os
import time
from typing import Optional, List, Dict, Any
from scrapingbee import ScrapingBeeClient
from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.data.connectors.base_mongo_provider import BaseProvider
from wwai_agent_orchestration.data.providers.models.scraper import (
    PageScrapeInput,
    SectionScrapeInput,
    RawScrapeResponse,
    ScrapeOutput,
    Section,
    SectionInfo,
    SectionContent,
    SectionDetectionMetadata,
)
from wwai_agent_orchestration.data.providers.utils.scraper.structured_extraction import (
    extract_base_url,
    extract_structured_data,
)
from wwai_agent_orchestration.data.providers.utils.scraper.section_processing import (
    process_section_detection_result,
)

logger = get_logger(__name__)


# =============================================================================
# LOW-LEVEL CLIENT (HTTP only, no extraction)
# =============================================================================

class _ScrapingBeeClient:
    """Low-level ScrapingBee API wrapper. HTTP only; no BS4 or extraction."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SCRAPINGBEE_API_KEY")
        if not self.api_key:
            logger.warning("SCRAPINGBEE_API_KEY not set")

    def scrape(self, url: str, device: str = "desktop") -> RawScrapeResponse:
        """Basic scrape: HTML + screenshot. Returns RawScrapeResponse."""
        if not self.api_key:
            raise ValueError("SCRAPINGBEE_API_KEY not configured")
        client = ScrapingBeeClient(api_key=self.api_key)
        params = {
            "render_js": True,
            "premium_proxy": True,
            "country_code": "us",
            "device": device,
            "return_page_source": True,
            "screenshot": True,
            "screenshot_full_page": True,
            "json_response": True,
            "wait": 3000,
        }
        response = client.get(url, params=params)
        if response.status_code != 200:
            raise Exception(f"ScrapingBee failed: {response.status_code}")
        data = response.json()
        credits_used = int(response.headers.get("Spb-Cost", 1))
        return RawScrapeResponse(
            html_content=data.get("body", ""),
            screenshot_base64=data.get("screenshot", ""),
            credits_used=credits_used,
        )

    def scrape_with_sections(
        self,
        url: str,
        device: str = "desktop",
        user_xpaths: Optional[List[str]] = None,
    ) -> RawScrapeResponse:
        """Scrape with section detection JS. Returns RawScrapeResponse with sections_raw."""
        if not self.api_key:
            raise ValueError("SCRAPINGBEE_API_KEY not configured")
        params = {
            "render_js": True,
            "premium_proxy": True,
            "country_code": "us",
            "device": device,
            "return_page_source": True,
            "screenshot": True,
            "screenshot_full_page": True,
            "json_response": True,
            "block_resources": False,
            "wait": 5000,
            "wait_for": ".product, .main-content, body",
        }
        cache_buster = int(time.time())
        js_url = f"https://storage.googleapis.com/wwai-scraping/section_detection/section_detection.js?v={cache_buster}"
        if user_xpaths and len(user_xpaths) > 0:
            logger.info(f"Section detection with {len(user_xpaths)} user xpaths")
            js_code = f"""
                (async () => {{
                    try {{
                        window.USER_PROVIDED_XPATHS = {json.dumps(user_xpaths)};
                        const response = await fetch('{js_url}', {{ method: 'GET', mode: 'cors', cache: 'no-cache' }});
                        if (!response.ok) throw new Error('HTTP ' + response.status);
                        const scriptCode = await response.text();
                        return eval(scriptCode);
                    }} catch (error) {{
                        return {{
                            success: false, detection_method: 'error', validation_passed: false,
                            error: error.message || error.toString(),
                            pattern_count: 0, geometric_count: 0,
                            user_provided_count: {len(user_xpaths)}, user_matched_count: 0,
                            user_failed_xpaths: [], sections: []
                        }};
                    }}
                }})()
            """
        else:
            js_code = f"""
                (async () => {{
                    try {{
                        const response = await fetch('{js_url}', {{ method: 'GET', mode: 'cors', cache: 'no-cache' }});
                        if (!response.ok) throw new Error('HTTP ' + response.status);
                        const scriptCode = await response.text();
                        return eval(scriptCode);
                    }} catch (error) {{
                        return {{
                            success: false, detection_method: 'error', validation_passed: false,
                            error: error.message || error.toString(),
                            pattern_count: 0, geometric_count: 0,
                            user_provided_count: 0, user_matched_count: 0,
                            user_failed_xpaths: [], sections: []
                        }};
                    }}
                }})()
            """
        params["js_scenario"] = {
            "instructions": [
                {"wait": 3000},
                {"scroll_y": 1000},
                {"wait": 2000},
                {"scroll_y": 2000},
                {"wait": 2000},
                {"scroll_y": 3000},
                {"wait": 3000},
                {"evaluate": js_code},
            ]
        }
        client = ScrapingBeeClient(api_key=self.api_key)
        response = client.get(url, params=params)
        if response.status_code != 200:
            error_detail = response.text[:200] if response.text else "No error details"
            raise Exception(f"ScrapingBee failed: {response.status_code} - {error_detail}")
        data = response.json()
        credits_used = int(response.headers.get("Spb-Cost", 1))
        html_content = data.get("body", "")
        screenshot_base64 = data.get("screenshot", "")
        sections_raw = None
        for key in ("js_scenario_result", "evaluate_results", "js_scenario_report"):
            if key not in data:
                continue
            js_result = data[key]
            if isinstance(js_result, list) and len(js_result) > 0:
                js_result = js_result[-1]
            if isinstance(js_result, dict):
                sections_raw = js_result
                break
        return RawScrapeResponse(
            html_content=html_content,
            screenshot_base64=screenshot_base64,
            credits_used=credits_used,
            sections_raw=sections_raw,
        )


# =============================================================================
# WEB SCRAPING PROVIDER (new API)
# =============================================================================

class WebScrapingProvider(BaseProvider):
    """Core data provider: page-level or section-level scraping with optional content processing."""

    def __init__(self):
        super().__init__()
        self._client = _ScrapingBeeClient()

    def scrape_page(self, input_data: PageScrapeInput) -> ScrapeOutput:
        """
        Scrape URL at page level.
        process_content=False: raw HTML + screenshot only (one section with empty content).
        process_content=True: one section with is_full_page=True and extracted content.
        """
        start_time = time.time()
        url = input_data.url
        if not url:
            return ScrapeOutput(
                url="",
                device=input_data.device,
                success=False,
                error_message="URL is required",
            )
        logger.info(f"Scraping URL (page): {url}")
        try:
            raw = self._client.scrape(url, input_data.device)
            processing_time = time.time() - start_time
            content = SectionContent()
            if input_data.process_content and raw.html_content:
                base_url = extract_base_url(url)
                content = extract_structured_data(raw.html_content, base_url)
            full_page_section = Section(
                info=SectionInfo(
                    section_id="full_page",
                    section_index=0,
                    is_full_page=True,
                ),
                content=content,
            )
            return ScrapeOutput(
                url=url,
                device=input_data.device,
                success=True,
                raw=raw,
                sections=[full_page_section],
                credits_used=raw.credits_used,
                processing_time_seconds=round(processing_time, 2),
            )
        except Exception as e:
            logger.error(f"Scraping failed for {url}: {e}")
            return ScrapeOutput(
                url=url,
                device=input_data.device,
                success=False,
                error_message=str(e),
                processing_time_seconds=round(time.time() - start_time, 2),
            )

    def scrape_page_for_context(
        self,
        url: str,
        device: str = "desktop",
        process_content: bool = True,
    ) -> Dict[str, Any]:
        """
        Context-oriented facade for callers outside the data layer.

        Returns a stable dict payload that includes raw scrape data and structured content.
        """
        output = self.scrape_page(
            PageScrapeInput(url=url, device=device, process_content=process_content)
        )
        raw_dict = output.raw.model_dump() if output.raw else None

        structured_content = None
        if output.sections:
            section_content = output.sections[0].content
            if section_content:
                structured_content = section_content.model_dump()

        # Defensive fallback to preserve existing cache behavior.
        if structured_content is None and output.raw and output.raw.html_content:
            base_url = extract_base_url(url)
            structured_content = extract_structured_data(
                output.raw.html_content,
                base_url,
            ).model_dump()

        return {
            "success": output.success,
            "error_message": output.error_message,
            "raw": raw_dict,
            "structured_content": structured_content,
        }

    def scrape_sections(self, input_data: SectionScrapeInput) -> ScrapeOutput:
        """
        Scrape URL with section detection.
        process_content=False: raw HTML + screenshot + sections (content from JS).
        process_content=True: sections with structured content + page_content (full-page extraction).
        """
        start_time = time.time()
        url = input_data.url
        if not url:
            return ScrapeOutput(
                url="",
                device=input_data.device,
                success=False,
                error_message="URL is required",
            )
        logger.info(f"Scraping URL (sections): {url}")
        try:
            raw = self._client.scrape_with_sections(
                url, input_data.device, input_data.user_xpaths
            )
            processing_time = time.time() - start_time
            page_content = None
            sections_list: list = []
            section_metadata = None
            if input_data.process_content and raw.html_content:
                base_url = extract_base_url(url)
                page_content = extract_structured_data(raw.html_content, base_url)
            if raw.sections_raw:
                sections_list, section_metadata = process_section_detection_result(
                    raw.sections_raw, upload_section_fn=None
                )
                if sections_list is None:
                    sections_list = []
            else:
                section_metadata = SectionDetectionMetadata(
                    success=False,
                    detection_method="disabled",
                    validation_passed=False,
                    pattern_count=0,
                    geometric_count=0,
                    raw_sections_count=0,
                    clean_sections_count=0,
                    wrappers_removed=0,
                    invisible_removed=0,
                )
            return ScrapeOutput(
                url=url,
                device=input_data.device,
                success=True,
                raw=raw,
                sections=sections_list,
                page_content=page_content,
                section_detection_metadata=section_metadata,
                credits_used=raw.credits_used,
                processing_time_seconds=round(processing_time, 2),
            )
        except Exception as e:
            logger.error(f"Scraping failed for {url}: {e}")
            return ScrapeOutput(
                url=url,
                device=input_data.device,
                success=False,
                error_message=str(e),
                processing_time_seconds=round(time.time() - start_time, 2),
            )
