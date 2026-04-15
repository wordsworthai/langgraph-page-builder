"""
Gemini Provider.

Page intent extraction and custom URL context using Google Gemini.
URL-only, no DB. Two endpoints: get_page_intent, get_context.
"""

import os
import time
from wwai_agent_orchestration.core.observability.logger import get_logger
from typing import Optional
from datetime import datetime

from google import genai
from google.genai.types import GenerateContentConfig

from wwai_agent_orchestration.data.connectors.base_mongo_provider import BaseProvider
from wwai_agent_orchestration.data.providers.models.gemini import (
    GeminiInput,
    GeminiOutput,
    GeminiContext,
)

logger = get_logger(__name__)


GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_CONTEXT_MODEL = os.getenv("GEMINI_CONTEXT_MODEL", "gemini-2.5-flash")

PAGE_INTENT_PROMPT = """
Analyze this webpage URL and extract:

1. **Page Intent**: What is the primary purpose of this page? (e.g., product sale, lead generation, brand awareness, information, booking/scheduling)

2. **Business Description**: A concise 2-3 sentence description of what this business does, who they serve, and their main value proposition.

Respond in this exact format:
PAGE_INTENT: [one line description]
BUSINESS_DESCRIPTION: [2-3 sentences]
"""

DEFAULT_CONTEXT_QUERY = (
    "Summarize this webpage in one short paragraph. "
    "Include the page title and the main points or purpose of the page."
)


class GeminiProvider(BaseProvider):
    """Provider for Gemini AI page analysis."""

    def __init__(self):
        super().__init__()

        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            logger.warning("GEMINI_API_KEY not set")
            self.client = None
        else:
            self.client = genai.Client(api_key=gemini_api_key)
            logger.info("Gemini client initialized")

    def _response_text_from_candidates(self, response) -> str:
        text_parts = []
        candidates = getattr(response, "candidates", None) or []
        for cand in candidates:
            content = getattr(cand, "content", None)
            if content is None:
                continue
            parts = getattr(content, "parts", None) or []
            for part in parts:
                if hasattr(part, "text") and part.text:
                    text_parts.append(part.text)
        return "".join(text_parts)

    def get(self, input_data: GeminiInput) -> GeminiOutput:
        if not (input_data.url or "").strip():
            return GeminiOutput(
                url="",
                success=False,
                error_message="No URL provided",
            )
        return self.get_page_intent(input_data.url.strip())

    def get_page_intent(self, url: str) -> GeminiOutput:
        start_time = time.time()
        if not (url or "").strip():
            return GeminiOutput(
                url=url or "",
                success=False,
                error_message="No URL provided",
                processing_time_seconds=0,
            )
        url = url.strip()

        if not self.client:
            return GeminiOutput(
                url=url,
                success=False,
                error_message="GEMINI_API_KEY not configured",
                processing_time_seconds=round(time.time() - start_time, 2),
            )

        logger.info(f"Analyzing URL with Gemini (page intent): {url}")
        try:
            page_intent, business_description = self._analyze_page_intent(url)
            processing_time = time.time() - start_time
            return GeminiOutput(
                url=url,
                success=True,
                page_intent=page_intent,
                business_description=business_description,
                processing_time_seconds=round(processing_time, 2),
                analyzed_at=datetime.utcnow(),
            )
        except Exception as e:
            logger.error(f"Gemini page intent failed for {url}: {e}")
            return GeminiOutput(
                url=url,
                success=False,
                error_message=str(e),
                processing_time_seconds=round(time.time() - start_time, 2),
            )

    def _analyze_page_intent(self, url: str) -> tuple[Optional[str], Optional[str]]:
        tools = [{"url_context": {}}]
        prompt = f"Analyze this URL: {url}\n\n{PAGE_INTENT_PROMPT}"

        response = self.client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=GenerateContentConfig(tools=tools),
        )

        response_text = self._response_text_from_candidates(response)
        if not response_text:
            raise ValueError("Gemini returned no content (empty or blocked candidate)")

        page_intent = None
        business_description = None
        lines = response_text.strip().split("\n")
        for line in lines:
            if line.startswith("PAGE_INTENT:"):
                page_intent = line.replace("PAGE_INTENT:", "").strip()
            elif line.startswith("BUSINESS_DESCRIPTION:"):
                business_description = line.replace("BUSINESS_DESCRIPTION:", "").strip()

        if not page_intent and not business_description and response_text:
            business_description = response_text[:500]

        return page_intent, business_description

    def get_context(self, url: str, custom_query: Optional[str] = None) -> GeminiContext:
        if not self.client:
            return GeminiContext(
                query_used=custom_query or "default",
                response_text="Error: GEMINI_API_KEY not configured",
                url_context_metadata={},
                extraction_timestamp=datetime.utcnow(),
            )
        try:
            query = custom_query or DEFAULT_CONTEXT_QUERY
            tools = [{"url_context": {}}]
            full_prompt = f"Analyze this URL: {url}\n\n{query}"
            config = GenerateContentConfig(tools=tools)
            logger.info(f"Gemini get_context: model={GEMINI_CONTEXT_MODEL} url={url}")

            response = self.client.models.generate_content(
                model=GEMINI_CONTEXT_MODEL,
                contents=full_prompt,
                config=config,
            )
            response_text = self._response_text_from_candidates(response) or ""
            if not response_text:
                logger.warning(f"Gemini get_context: empty response for url={url}")

            candidates = getattr(response, "candidates", None) or []
            first_candidate = candidates[0] if candidates else None
            url_context_metadata = {}
            if first_candidate is not None and hasattr(first_candidate, "url_context_metadata"):
                meta = first_candidate.url_context_metadata
                if meta:
                    if isinstance(meta, dict):
                        url_context_metadata = meta
                    elif hasattr(meta, "__iter__") and not isinstance(meta, dict):
                        url_context_metadata = {
                            "url_metadata": [
                                {
                                    "retrieved_url": getattr(item, "retrieved_url", ""),
                                    "url_retrieval_status": getattr(item, "url_retrieval_status", ""),
                                }
                                for item in meta
                            ]
                        }
                    else:
                        url_context_metadata = {
                            "retrieved_url": getattr(meta, "retrieved_url", ""),
                            "url_retrieval_status": getattr(meta, "url_retrieval_status", ""),
                        }
            return GeminiContext(
                query_used=full_prompt,
                response_text=response_text,
                url_context_metadata=url_context_metadata,
                extraction_timestamp=datetime.utcnow(),
            )
        except Exception as e:
            logger.warning(f"Gemini context failed for {url}: {e}")
            return GeminiContext(
                query_used=custom_query or "default",
                response_text=f"Error: {str(e)}",
                url_context_metadata={},
                extraction_timestamp=datetime.utcnow(),
            )
