import os
import re
from typing import List, Dict, Any, Optional
from wwai_agent_orchestration.scraper.collectors.base import Collector


def _sanitize_filename(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", name or "")
    return safe[:200]


class SectionScreenshotCollector(Collector):
    name = "section_screenshots"

    def __init__(
        self,
        *,
        output_dir: Optional[str] = None,
        selector_prefix: str = "shopify-section-",
        include_divs: bool = True,
        include_sections: bool = True,
        wait_for_selector_ms: int = 20000,
        scroll_pause_ms: int = 250,
        # Extra wait to give images time to load before capturing screenshots
        # Wait for network idle or timeout after 30 seconds.
        wait_for_images_ms: int = 30000,
    ) -> None:
        self.output_dir = output_dir
        self.selector_prefix = selector_prefix
        self.include_divs = include_divs
        self.include_sections = include_sections
        self.wait_for_selector_ms = wait_for_selector_ms
        self.scroll_pause_ms = scroll_pause_ms
        self.wait_for_images_ms = wait_for_images_ms

    async def collect(self, page, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Capture screenshots for elements matching Shopify section id prefix.
        Returns one record per element:
          {
            "index": int,
            "section_id": str,
            "screenshot_path": str
          }
        """
        # Build selector - support both patterns:
        # 1. shopify-section- (current HTML structure)
        # 2. shopify-section-template-- (legacy/alternative pattern)
        selectors: List[str] = []
        
        # Always support both common patterns if using default prefix
        if self.selector_prefix == "shopify-section-":
            prefixes_to_try = ["shopify-section-", "shopify-section-template--"]
        elif self.selector_prefix == "shopify-section-template--":
            prefixes_to_try = ["shopify-section-template--", "shopify-section-"]
        else:
            # Custom prefix - only use that one
            prefixes_to_try = [self.selector_prefix]
        
        for prefix in prefixes_to_try:
            if self.include_sections:
                selectors.append(f'section[id^="{prefix}"]')
            if self.include_divs:
                selectors.append(f'div[id^="{prefix}"]')
        
        selector = ", ".join(selectors) if selectors else 'section[id^="shopify-section-"], div[id^="shopify-section-template--"]'

        # Try to wait for presence but don't fail hard
        try:
            await page.wait_for_selector(selector, timeout=self.wait_for_selector_ms)
        except Exception:
            pass

        # Best-effort: wait for images/network to settle a bit so screenshots capture
        # fully-loaded content rather than placeholders.
        try:
            await page.wait_for_load_state("networkidle", timeout=self.wait_for_images_ms)
        except Exception:
            # Fallback: ignore if network doesn't go fully idle within timeout.
            pass

        elements = await page.query_selector_all(selector)
        
        # Wait for all images to load ONCE globally (instead of per element)
        # This is much more efficient than waiting 30s per element
        if elements:
            try:
                await page.wait_for_function(
                    "() => Array.from(document.images || []).every(img => img.complete)",
                    timeout=self.wait_for_images_ms,
                )
            except Exception:
                # If images are still not all complete, proceed anyway rather than failing.
                pass

        # Resolve output directory
        final_output_dir = self.output_dir
        if not final_output_dir:
            # Prefer context-provided dir if any
            final_output_dir = context.get("screenshot_output_dir")
        if not final_output_dir:
            # Fallback to CWD/screenshots
            final_output_dir = os.path.join(os.getcwd(), "screenshots")
        # Add device/profile subfolder to avoid collisions across devices
        profile_name = str(context.get("profile", "")).strip()
        if profile_name:
            final_output_dir = os.path.join(final_output_dir, profile_name)
        os.makedirs(final_output_dir, exist_ok=True)

        results: List[Dict[str, Any]] = []

        if not elements:
            return results

        for idx, el in enumerate(elements):
            try:
                section_id = await el.get_attribute("id") or f"section_{idx:03d}"
                await el.scroll_into_view_if_needed()
                # Short pause after scrolling to ensure element is in view
                # (images already loaded globally above, so we don't need to wait again)
                await page.wait_for_timeout(self.scroll_pause_ms)

                safe_id = _sanitize_filename(section_id)
                out_path = os.path.join(final_output_dir, f"{idx:03d}_{safe_id}.png")
                await el.screenshot(path=out_path)

                results.append(
                    {
                        "index": idx,
                        "section_id": section_id,
                        "screenshot_path": out_path,
                    }
                )
            except Exception:
                # Best-effort: continue on individual failures
                continue

        return results