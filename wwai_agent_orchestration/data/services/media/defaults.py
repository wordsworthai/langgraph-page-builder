"""
Central defaults for media service.

Single source of truth for retrieval sources and other media config.
Change these values to adjust behavior across the codebase.
"""
from typing import List

# Image retrieval: which sources to fetch when matching images to slots
# Options: "generated", "stock", "google_maps"
# google_maps disabled by default (many links are broken)
DEFAULT_IMAGE_RETRIEVAL_SOURCES: List[str] = ["generated"]

# Video retrieval: videos come from stock only (no google_maps)
DEFAULT_VIDEO_RETRIEVAL_SOURCES: List[str] = ["stock"]
