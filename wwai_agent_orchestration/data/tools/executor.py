"""
Tool executor for provider-backed function calling.
"""

import json
from typing import Any, Dict

from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.data.providers.business_profile_provider import BusinessProfileProvider
from wwai_agent_orchestration.data.providers.reviews_provider import ReviewsProvider
from wwai_agent_orchestration.data.providers.media_assets_provider import MediaAssetsProvider
from wwai_agent_orchestration.data.providers.scraping_bee_provider import WebScrapingProvider
from wwai_agent_orchestration.data.providers.gemini_provider import GeminiProvider

from wwai_agent_orchestration.data.providers.models.business_profile import BusinessProfileInput
from wwai_agent_orchestration.data.providers.models.reviews import ReviewsInput
from wwai_agent_orchestration.data.providers.models.media_assets import MediaAssetsInput
from wwai_agent_orchestration.data.providers.models.scraper import PageScrapeInput
from wwai_agent_orchestration.data.providers.models.gemini import GeminiInput

logger = get_logger(__name__)

_providers: Dict[str, Any] = {}


def _get_provider(name: str):
    if name not in _providers:
        if name == "business_profile":
            _providers[name] = BusinessProfileProvider()
        elif name == "reviews":
            _providers[name] = ReviewsProvider()
        elif name == "media_assets":
            _providers[name] = MediaAssetsProvider()
        elif name == "scraping_bee":
            _providers[name] = WebScrapingProvider()
        elif name == "gemini":
            _providers[name] = GeminiProvider()
    return _providers.get(name)


TOOL_MAPPING = {
    "get_business_profile": {"provider": "business_profile", "input_model": BusinessProfileInput},
    "get_reviews": {"provider": "reviews", "input_model": ReviewsInput},
    "get_media_assets": {"provider": "media_assets", "input_model": MediaAssetsInput},
    "scrape_website": {"provider": "scraping_bee", "input_model": PageScrapeInput},
    "analyze_page_intent": {"provider": "gemini", "input_model": GeminiInput},
}


def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"Executing tool: {tool_name} with args: {arguments}")

    if tool_name not in TOOL_MAPPING:
        raise ValueError(f"Unknown tool: {tool_name}")

    mapping = TOOL_MAPPING[tool_name]
    provider = _get_provider(mapping["provider"])
    input_model = mapping["input_model"]
    if not provider:
        raise ValueError(f"Provider not found for tool: {tool_name}")

    try:
        input_data = input_model(**arguments)
    except Exception as e:
        raise ValueError(f"Invalid arguments for {tool_name}: {e}") from e

    if tool_name == "scrape_website":
        result = provider.scrape_page_for_context(
            url=input_data.url,
            device=input_data.device,
            process_content=input_data.process_content,
        )
        return result

    result = provider.get(input_data)
    return result.model_dump()


def execute_tool_call(tool_call: Dict[str, Any]) -> Dict[str, Any]:
    name = tool_call.get("name")
    arguments = tool_call.get("arguments", {})
    if isinstance(arguments, str):
        arguments = json.loads(arguments)
    return execute_tool(name, arguments)


def get_available_tools() -> list[str]:
    return list(TOOL_MAPPING.keys())
