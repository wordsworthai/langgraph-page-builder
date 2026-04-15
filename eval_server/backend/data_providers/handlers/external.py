from typing import Any, Dict

from wwai_agent_orchestration.data.providers.scraping_bee_provider import WebScrapingProvider
from wwai_agent_orchestration.data.providers.gemini_provider import GeminiProvider

from data_providers.utils import require_arg, to_plain_object


def run_scraping_context(args: Dict[str, Any], allow_external: bool) -> Dict[str, Any]:
    if not allow_external:
        raise PermissionError("Web scraping is blocked. Enable external calls to proceed.")
    return WebScrapingProvider().scrape_page_for_context(
        url=require_arg(args, "url"),
        device=args.get("device", "desktop"),
        process_content=args.get("process_content", True),
    )


def run_gemini_page_intent(args: Dict[str, Any], allow_external: bool) -> Dict[str, Any]:
    if not allow_external:
        raise PermissionError("Gemini calls are blocked. Enable external calls to proceed.")
    result = GeminiProvider().get_page_intent(require_arg(args, "url"))
    return to_plain_object(result)


def run_gemini_context(args: Dict[str, Any], allow_external: bool) -> Dict[str, Any]:
    if not allow_external:
        raise PermissionError("Gemini calls are blocked. Enable external calls to proceed.")
    result = GeminiProvider().get_context(
        url=require_arg(args, "url"),
        custom_query=args.get("custom_query"),
    )
    return to_plain_object(result)

