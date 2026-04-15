# data/providers/utils/section_processing.py
"""
Process section detection result from ScrapingBee JS.
Turns raw JS result into List[Section] + SectionDetectionMetadata.
Optional upload_section_fn(html_content, section_id) -> url for GCP upload (caller provides).
"""

from typing import Optional, List, Tuple, Callable, Dict, Any

from wwai_agent_orchestration.data.providers.models.scraper import (
    Section,
    SectionInfo,
    SectionContent,
    SectionDetectionMetadata,
    WebsiteImageAsset,
    WebsiteVideoAsset,
    WebsiteEntityLink,
)


def _strip_url_params(url: str) -> str:
    """Strip query parameters from URL."""
    if not url or "?" not in url:
        return url
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def process_section_detection_result(
    raw_result: Dict[str, Any],
    upload_section_fn: Optional[Callable[[str, str], Optional[str]]] = None,
) -> Tuple[Optional[List[Section]], SectionDetectionMetadata]:
    """
    Process ScrapingBee section detection JS result.

    Args:
        raw_result: Dict from JS (success, detection_method, sections, validation, cleaning, etc.).
        upload_section_fn: Optional (html_content, section_id) -> public URL. If None, html_url on sections is None.

    Returns:
        (sections, metadata). sections is None if no sections or on error; metadata is always returned.
    """
    try:
        success = raw_result.get("success", False)
        detection_method = raw_result.get("detection_method", "unknown")
        validation_passed = raw_result.get("validation_passed", False)
        pattern_count = raw_result.get("pattern_count", 0)
        geometric_count = raw_result.get("geometric_count", 0)
        error = raw_result.get("error")

        user_provided_count = raw_result.get("user_provided_count", 0)
        user_matched_count = raw_result.get("user_matched_count", 0)
        user_failed_xpaths = raw_result.get("user_failed_xpaths", [])

        validation = raw_result.get("validation", {})
        height_coverage = validation.get("coverage")
        page_height = validation.get("pageHeight")
        coverage_reason = validation.get("reason")

        cleaning = raw_result.get("cleaning", {})
        raw_count = cleaning.get("raw_count", 0)
        clean_count = cleaning.get("clean_count", 0)
        wrappers_removed = cleaning.get("wrappers_removed", 0)
        invisible_removed = cleaning.get("invisible_removed", 0)

        section_metadata = SectionDetectionMetadata(
            success=success,
            detection_method=detection_method,
            validation_passed=validation_passed,
            height_coverage=height_coverage,
            page_height=page_height,
            coverage_reason=coverage_reason,
            pattern_count=pattern_count,
            geometric_count=geometric_count,
            raw_sections_count=raw_count,
            clean_sections_count=clean_count,
            wrappers_removed=wrappers_removed,
            invisible_removed=invisible_removed,
            user_provided_count=user_provided_count,
            user_matched_count=user_matched_count,
            user_failed_xpaths=user_failed_xpaths,
            error=error,
        )

        sections_raw = raw_result.get("sections", [])
        if not sections_raw:
            return None, section_metadata

        processed_sections: List[Section] = []
        for section_raw in sections_raw:
            try:
                section_html_url = None
                if upload_section_fn and section_raw.get("html_content"):
                    section_html_url = upload_section_fn(
                        section_raw["html_content"],
                        section_raw["section_id"],
                    )

                section_images = [
                    WebsiteImageAsset(
                        src=img["src"],
                        base_src=_strip_url_params(img.get("src", "")),
                        alt=img.get("alt", ""),
                        width=img.get("width"),
                        height=img.get("height"),
                        loading=img.get("loading"),
                        srcset=img.get("srcset"),
                        type="img_tag",
                    )
                    for img in section_raw.get("images", [])
                ]
                section_videos = [
                    WebsiteVideoAsset(
                        src=vid.get("src"),
                        type=vid.get("type", "video_tag"),
                        width=vid.get("width"),
                        height=vid.get("height"),
                        autoplay=vid.get("autoplay"),
                        loop=vid.get("loop"),
                        muted=vid.get("muted"),
                        poster=vid.get("poster"),
                        sources=vid.get("sources"),
                    )
                    for vid in section_raw.get("videos", [])
                ]
                section_entities = [
                    WebsiteEntityLink(
                        url=entity["url"],
                        text=entity["text"],
                        is_internal=entity["is_internal"],
                    )
                    for entity in section_raw.get("entities", [])
                ]

                info = SectionInfo(
                    section_id=section_raw["section_id"],
                    section_index=section_raw["section_index"],
                    is_full_page=False,
                    xpath=section_raw.get("xpath"),
                    xpath_full=section_raw.get("xpath_full"),
                    section_type=section_raw.get("type"),
                    src=section_raw.get("src"),
                    html_url=section_html_url,
                    html_size_kb=section_raw.get("html_size_kb"),
                    css_properties=section_raw.get("css_properties"),
                    attributes=section_raw.get("attributes"),
                )
                content = SectionContent(
                    clean_text=section_raw.get("clean_text"),
                    images=section_images,
                    videos=section_videos,
                    entities=section_entities,
                    validation_stats=None,
                )
                processed_sections.append(Section(info=info, content=content))
            except Exception:
                continue

        return processed_sections, section_metadata

    except Exception as e:
        return None, SectionDetectionMetadata(
            success=False,
            detection_method="error",
            validation_passed=False,
            pattern_count=0,
            geometric_count=0,
            raw_sections_count=0,
            clean_sections_count=0,
            wrappers_removed=0,
            invisible_removed=0,
            user_provided_count=0,
            user_matched_count=0,
            user_failed_xpaths=[],
            error=str(e),
        )
