import asyncio
import http.server
import os
import re
import socketserver
import threading
from contextlib import asynccontextmanager
from typing import AsyncIterator, Any, Dict, Optional, Tuple
from playwright.async_api import Browser, BrowserContext, Page


def _start_static_server(directory: str, port: int = 0) -> Tuple[socketserver.TCPServer, int]:
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

    handler = lambda *args, **kwargs: QuietHandler(*args, directory=directory, **kwargs)
    httpd = socketserver.TCPServer(("", port), handler)
    actual_port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, actual_port


@asynccontextmanager
async def open_page(
    input_url_or_path: str,
    browser: Browser,
    profile: Dict[str, Any],
    *,
    serve_local: bool = True,
    ws_endpoint: Optional[str] = None,
) -> AsyncIterator[Page]:
    """
    Async context manager that returns an opened Page for given input.
    - If input is a URL (http/https), uses it directly.
    - If input is a local path and serve_local=True, starts a temporary HTTP server and navigates to it.
    The Page and any temp HTTP server are cleaned up on exit.
    """
    raw_input = (input_url_or_path or "").strip()
    is_url_input = bool(re.match(r"^https?://", raw_input, flags=re.IGNORECASE))
    page_url: str
    httpd = None

    if is_url_input or not serve_local:
        page_url = raw_input
    else:
        local_path = os.path.abspath(raw_input)
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"File not found: {local_path}")
        root_dir = os.path.dirname(local_path)
        filename = os.path.basename(local_path)
        httpd, port = _start_static_server(root_dir, port=0)
        host_for_browser = "host.docker.internal" if ws_endpoint else "127.0.0.1"
        await asyncio.sleep(0.1)
        page_url = f"http://{host_for_browser}:{port}/{filename}"

    context_args: Dict[str, Any] = {
        "viewport": profile.get("viewport"),
        "device_scale_factor": profile.get("device_scale_factor", 2.0),
        "is_mobile": profile.get("is_mobile", False),
    }
    ua = profile.get("user_agent")
    if ua:
        context_args["user_agent"] = ua

    context: Optional[BrowserContext] = None
    page: Optional[Page] = None
    try:
        context = await browser.new_context(**context_args)
        page = await context.new_page()
        await page.goto(page_url, wait_until="load")
        yield page
    finally:
        try:
            if context is not None:
                await context.close()
        except Exception:
            pass
        if httpd is not None:
            try:
                httpd.shutdown()
            except Exception:
                pass


