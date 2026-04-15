# nodes/smb/screenshot_capture_node.py

"""
Screenshot Capture Node - Capture screenshots from HTML and upload to S3.

This node:
1. Takes HTML URL (S3 URL or local path) as input
2. Captures screenshots via Playwright
3. Uploads screenshots to S3
4. Returns screenshot URLs in state

Can accept either:
- compiled_html_s3_url: S3 URL of HTML file (preferred)
- compiled_html_path: Local path to HTML file (fallback)
"""

import os
import time
import tempfile
import shutil
from typing import Dict, Any, List, Optional
from langgraph.types import RunnableConfig

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.core.observability.logger import get_logger

from wwai_agent_orchestration.scraper.collectors import section_screenshots
from wwai_agent_orchestration.scraper.playwright_core.device_profiles import DeviceType
from wwai_agent_orchestration.scraper.collector_processors import screenshot_processor
from wwai_agent_orchestration.scraper import runner

logger = get_logger(__name__)


async def capture_screenshots_from_html(
    html_url_or_path: str,
    generation_version_id: str,
    *,
    ws_endpoint: str = "ws://localhost:3099/",
    headless: bool = True,
    dpr: float = 2.0,
    timeout: int = 20,
    profiles: List[DeviceType] = None,
    s3_bucket_name: Optional[str] = None,
    s3_bucket_location: Optional[str] = None,
    screenshot_output_folder: str = None,
    keep_temp_files: bool = False,
) -> Dict[str, Any]:
    """
    Standalone function to capture screenshots from HTML and upload to S3.
    
    Args:
        html_url_or_path: S3 URL or local path to HTML file
        generation_version_id: Generation version ID for this run
        ws_endpoint: Playwright WebSocket endpoint
        headless: Run browser in headless mode
        dpr: Device pixel ratio for screenshots
        timeout: Page load timeout in seconds
        profiles: List of device profiles to capture (defaults to [DESKTOP])
        s3_bucket_name: S3 bucket name (optional, uses default)
        s3_bucket_location: S3 bucket location (optional, uses default)
        screenshot_output_folder: Folder for screenshot output (optional, uses temp dir)
        keep_temp_files: If True, keep temporary files after completion (default: False)
    
    Returns:
        Dict with:
        - desktop_screenshots: List of dicts with section_id, index, s3_url, screenshot_path
        - mobile_screenshots: List of dicts with section_id, index, s3_url, screenshot_path
        - desktop_s3_url: First desktop screenshot URL (backward compatibility)
        - mobile_s3_url: First mobile screenshot URL (backward compatibility)
    """
    start_time = time.time()
    
    # Default values
    if profiles is None:
        profiles = [DeviceType.DESKTOP]
    
    # Setup screenshot output folder
    using_temp_dir = screenshot_output_folder is None
    if using_temp_dir:
        temp_dir = tempfile.mkdtemp(prefix=f"screenshot_capture_{generation_version_id}_")
        screenshot_folder = temp_dir
        logger.info(f"Created temporary directory for screenshots: {temp_dir}")
    else:
        screenshot_folder = screenshot_output_folder
        os.makedirs(screenshot_folder, exist_ok=True)
    
    try:
        # Capture screenshots
        logger.info("Capturing screenshots", html_source=html_url_or_path, profiles=[p.value for p in profiles])
        collectors = [
            section_screenshots.SectionScreenshotCollector(
                output_dir=screenshot_folder
            )
        ]
        
        collector_results = await runner.run_collectors(
            input_url_or_path=html_url_or_path,
            collectors=collectors,
            profiles=profiles,
            ws_endpoint=ws_endpoint,
            headless=headless,
            dpr=dpr,
            timeout=timeout,
        )
        
        # Upload screenshots to S3
        logger.info("Uploading screenshots to S3")
        screenshot_results = screenshot_processor.process_results_for_screenshot(
            results_by_profile=collector_results,
            s3_file_dir=f"ai_pages/{generation_version_id}",
            bucket_name=s3_bucket_name,
            bucket_location=s3_bucket_location,
        )
        
        duration_ms = (time.time() - start_time) * 1000
        
        logger.info(
            "Screenshot capture completed",
            generation_version_id=generation_version_id,
            desktop_count=len(screenshot_results.get("desktop_screenshots", [])),
            mobile_count=len(screenshot_results.get("mobile_screenshots", [])),
            duration_ms=round(duration_ms, 2)
        )
        
        return screenshot_results
        
    finally:
        # Clean up temporary directory if we created one and cleanup is requested
        if using_temp_dir and not keep_temp_files:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary directory {temp_dir}: {e}")


@NodeRegistry.register(
    name="screenshot_capture",
    description="Capture screenshots from HTML and upload to S3",
    max_retries=1,
    timeout=300,  # 5 minutes (screenshot capture can be slow)
    tags=["screenshot", "capture", "smb"]
)
async def screenshot_capture_node(
    state: Dict[str, Any],
    config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """
    LangGraph node to capture screenshots from HTML and upload to S3.
    
    Uses HTML from html_compilation_results (either S3 URL or local path).
    
    Args:
        state: Must contain:
            - generation_version_id: Generation version ID
            - html_compilation_results: Dict with compiled_html_s3_url or compiled_html_path
        config: Optional configuration:
            - ws_endpoint: Playwright WebSocket endpoint (default: "ws://localhost:3099/")
            - headless: Run browser in headless mode (default: True)
            - dpr: Device pixel ratio (default: 2.0)
            - timeout: Page load timeout (default: 20)
            - capture_mobile: Whether to capture mobile screenshots (default: False)
            - s3_bucket_name: S3 bucket name (optional)
            - s3_bucket_location: S3 bucket location (optional)
            - screenshot_output_folder: Folder for screenshot output (optional)
    
    Returns:
        State updates with:
        - screenshot_capture_results: Dict with desktop_screenshots, mobile_screenshots, etc.
    """
    start_time = time.time()
    
    config = config or {}
    generation_version_id = config.get("configurable", {}).get("thread_id") or (state.input.generation_version_id if state.input else None)
    if not generation_version_id:
        raise ValueError("generation_version_id not found in config or state.input")
    html_compilation_results = (state.post_process and state.post_process.html_compilation_results) or {}
    html_s3_url = html_compilation_results.get('compiled_html_s3_url') if isinstance(html_compilation_results, dict) else None
    html_local_path = html_compilation_results.get('compiled_html_path') if isinstance(html_compilation_results, dict) else None
    
    # Prefer S3 URL, fallback to local path
    html_url_or_path = html_s3_url or html_local_path
    
    if not html_url_or_path:
        raise ValueError(
            "No HTML source found. Expected html_compilation_results with "
            "compiled_html_s3_url or compiled_html_path in state"
        )
    
    logger.info(
        "Starting screenshot capture",
        generation_version_id=generation_version_id,
        html_source=html_url_or_path,
        using_s3_url=html_s3_url is not None,
        node="screenshot_capture"
    )
    
    # Get configuration
    ws_endpoint = config.get('ws_endpoint', 'ws://localhost:3099/')
    headless = config.get('headless', True)
    dpr = config.get('dpr', 2.0)
    timeout = config.get('timeout', 20)
    capture_mobile = config.get('capture_mobile', False)
    s3_bucket_name = config.get('s3_bucket_name')
    s3_bucket_location = config.get('s3_bucket_location')
    screenshot_output_folder = config.get('screenshot_output_folder')
    
    # Determine profiles
    profiles = [DeviceType.DESKTOP]
    if capture_mobile:
        profiles.append(DeviceType.MOBILE)
    
    # Execute screenshot capture
    try:
        screenshot_results = await capture_screenshots_from_html(
            html_url_or_path=html_url_or_path,
            generation_version_id=generation_version_id,
            ws_endpoint=ws_endpoint,
            headless=headless,
            dpr=dpr,
            timeout=timeout,
            profiles=profiles,
            s3_bucket_name=s3_bucket_name,
            s3_bucket_location=s3_bucket_location,
            screenshot_output_folder=screenshot_output_folder,
        )
        
        duration_ms = (time.time() - start_time) * 1000
        
        logger.info(
            "Screenshot capture completed",
            generation_version_id=generation_version_id,
            desktop_screenshots=len(screenshot_results.get("desktop_screenshots", [])),
            mobile_screenshots=len(screenshot_results.get("mobile_screenshots", [])),
            duration_ms=round(duration_ms, 2),
            node="screenshot_capture"
        )
        
        from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import PostProcessResult
        return {
            "post_process": PostProcessResult(screenshot_capture_results=screenshot_results),
        }
        
    except Exception as e:
        logger.error(
            "Screenshot capture failed",
            error=str(e),
            generation_version_id=generation_version_id,
            node="screenshot_capture"
        )
        raise
