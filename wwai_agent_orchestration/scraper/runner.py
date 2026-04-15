from typing import List, Dict, Any, Optional
from wwai_agent_orchestration.scraper.playwright_core.browser import connect_or_launch
from wwai_agent_orchestration.scraper.playwright_core.device_profiles import DeviceType, get_profile
from wwai_agent_orchestration.scraper.playwright_core.page_loader import open_page
from wwai_agent_orchestration.scraper.collectors.base import Collector


async def run_collectors(
    input_url_or_path: str,
    collectors: List[Collector],
    profiles: List[DeviceType],
    *,
    ws_endpoint: Optional[str] = None,
    headless: bool = True,
    dpr: float = 2.0,
    timeout: int = 20,
    shared_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """
    Run multiple collectors across one or more device profiles.
    Returns:
      { "<profile>": { "<collector_name>": [records...] } }
    """
    results: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    async with connect_or_launch(ws_endpoint, headless=headless) as browser:
        for dt in profiles:
            prof = get_profile(dt, dpr=dpr)
            ctx = {"timeout": timeout, **(shared_context or {}), "profile": dt.value}
            async with open_page(input_url_or_path, browser, prof, serve_local=True, ws_endpoint=ws_endpoint) as page:
                per_collector: Dict[str, List[Dict[str, Any]]] = {}
                for c in collectors:
                    try:
                        data = await c.collect(page, ctx)
                        per_collector[c.name] = data
                    except Exception:
                        per_collector[c.name] = []
                results[dt.value] = per_collector
    return results


