"""
Screenshot utilities for URL context extraction.

Compress, upload to S3, and fetch screenshots for LLM vision APIs.
Reusable across page_context_extractor and other consumers.
"""

import base64
import io
import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional

import httpx
from PIL import Image

from template_json_builder.utils.s3_upload import get_s3_client, upload_file_to_s3

from wwai_agent_orchestration.core.observability.logger import get_logger

logger = get_logger(__name__)

SCREENSHOT_MAX_WIDTH = 1280
SCREENSHOT_JPEG_QUALITY = 82


def compress_screenshot_to_jpeg_bytes(screenshot_base64: str) -> Optional[bytes]:
    """
    Compress screenshot to JPEG bytes. Resizes to max width 1280px, ~200-400KB.
    """
    if not screenshot_base64:
        return None
    try:
        img_bytes = base64.b64decode(screenshot_base64)
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    except Exception as e:
        logger.warning(f"Failed to decode/load screenshot for compression: {e}")
        return None

    w, h = img.size
    if w > SCREENSHOT_MAX_WIDTH:
        ratio = SCREENSHOT_MAX_WIDTH / w
        new_h = int(h * ratio)
        img = img.resize((SCREENSHOT_MAX_WIDTH, new_h), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=SCREENSHOT_JPEG_QUALITY, optimize=True)
    return buf.getvalue()


def upload_screenshot_to_s3(
    jpeg_bytes: bytes,
    generation_version_id: Optional[str] = None,
) -> Optional[str]:
    """Upload compressed JPEG to S3. Returns S3 URL or None."""
    if not jpeg_bytes:
        return None
    prefix = generation_version_id or str(uuid.uuid4())[:8]
    s3_file_dir = f"url_context_screenshots/{prefix}"

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(jpeg_bytes)
        local_path = f.name

    try:
        s3_client, s3_err = get_s3_client()
        if s3_client is None:
            logger.error(f"Failed to create S3 client: {s3_err}")
            return None

        status = upload_file_to_s3(
            client=s3_client,
            local_filename=local_path,
            s3_file_dir=s3_file_dir,
            filename_prefix="page_screenshot",
            bucket_name=os.environ.get("S3_BUCKET_NAME", ""),
            bucket_location=os.environ.get("S3_BUCKET_REGION", ""),
            overwrite=True,
            content_type="image/jpeg",
        )

        if not status.status:
            logger.error(f"Failed to upload screenshot to S3: {status.message}")
            return None

        s3_url = status.response.get("s3_url")
        logger.info("Uploaded screenshot to S3", s3_url=s3_url)
        return s3_url
    finally:
        try:
            Path(local_path).unlink(missing_ok=True)
        except Exception:
            pass


def s3_url_to_base64_data_url(s3_url: str) -> Optional[str]:
    """
    Download image from S3 URL and return as base64 data URL for LLM vision APIs.
    """
    if not s3_url or not s3_url.startswith("http"):
        return None
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(s3_url)
            resp.raise_for_status()
        img_bytes = resp.content
        b64 = base64.b64encode(img_bytes).decode("ascii")
        return f"data:image/jpeg;base64,{b64}"
    except Exception as e:
        logger.warning(f"Failed to fetch S3 image as base64: {e}")
        return None
