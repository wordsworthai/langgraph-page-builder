from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional
from playwright.async_api import async_playwright, Browser


@asynccontextmanager
async def connect_or_launch(ws_endpoint: Optional[str] = None, *, headless: bool = True) -> AsyncIterator[Browser]:
    """
    Async context manager that yields a Playwright Browser.
    If ws_endpoint is provided, connects to that browser; otherwise launches a new headless browser.
    Ensures proper cleanup on exit.
    """
    async with async_playwright() as p:
        browser: Optional[Browser] = None
        try:
            if ws_endpoint:
                browser = await p.chromium.connect(ws_endpoint)
            else:
                browser = await p.chromium.launch(headless=headless)
            yield browser
        finally:
            if browser is not None:
                try:
                    await browser.close()
                except Exception:
                    pass


