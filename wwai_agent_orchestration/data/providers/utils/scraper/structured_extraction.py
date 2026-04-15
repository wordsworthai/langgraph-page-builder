# data/providers/utils/structured_extraction.py
"""
Structured data extraction from HTML.
Stateless: no MongoDB, GCP, or ScrapingBee. Input (html, base_url) -> SectionContent.
Used by WebScrapingProvider and scraper orchestrator.
"""

import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urljoin, urlunparse

from bs4 import BeautifulSoup, Comment

from wwai_agent_orchestration.data.providers.models.scraper import (
    WebsiteImageAsset,
    WebsiteVideoAsset,
    WebsiteEntityLink,
    ValidationStats,
    SectionContent,
)


# =============================================================================
# URL HELPERS
# =============================================================================

def extract_base_url(url: str) -> str:
    """Get scheme + netloc for resolving relative paths."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def strip_url_params(url: str) -> str:
    """Strip query parameters from URL."""
    if not url or "?" not in url:
        return url
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def resolve_relative_url(url: str, base_url: str) -> str:
    """Resolve relative URL against base."""
    if not url or url.startswith(("http://", "https://")):
        return url
    if url.startswith(("data:", "mailto:", "tel:", "javascript:", "#")):
        return url
    return urljoin(base_url, url)


# =============================================================================
# TEXT
# =============================================================================

def extract_clean_text(html_content: str) -> str:
    """Extract clean text: strip script, style, noscript, comments; normalize whitespace."""
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# =============================================================================
# DIMENSIONS
# =============================================================================

def _get_dimensions_from_tag(tag, width_attr: str = "width", height_attr: str = "height") -> tuple:
    """Extract width/height from HTML tag; return (width, height) as int or None."""
    width = tag.get(width_attr)
    height = tag.get(height_attr)
    try:
        w = int(re.sub(r"[^\d]", "", str(width))) if width and re.sub(r"[^\d]", "", str(width)) else None
        h = int(re.sub(r"[^\d]", "", str(height))) if height and re.sub(r"[^\d]", "", str(height)) else None
        return (w, h)
    except (ValueError, TypeError):
        return (None, None)


# =============================================================================
# IMAGES (Level 1 dedup by full src)
# =============================================================================

def extract_images(html_content: str, base_url: str) -> List[WebsiteImageAsset]:
    """Extract images from img tags and CSS background-url; Level 1 dedup by full src."""
    soup = BeautifulSoup(html_content, "html.parser")
    images_dict: Dict[str, WebsiteImageAsset] = {}

    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if not src:
            continue
        absolute_src = resolve_relative_url(src, base_url)
        base_src = strip_url_params(absolute_src)
        width, height = _get_dimensions_from_tag(img)
        alt = img.get("alt", "") or ""
        new_image = WebsiteImageAsset(
            src=absolute_src,
            base_src=base_src,
            alt=alt,
            width=width,
            height=height,
            loading=img.get("loading"),
            srcset=img.get("srcset"),
            type="img_tag",
        )
        if absolute_src in images_dict:
            existing = images_dict[absolute_src]
            if len(alt) > len(existing.alt or ""):
                images_dict[absolute_src] = new_image
        else:
            images_dict[absolute_src] = new_image

    for element in soup.find_all(attrs={"style": True}):
        style = element.get("style", "")
        bg_urls = re.findall(r'url\s*\(\s*["\']?([^"\')\s]+)["\']?\s*\)', style, re.IGNORECASE)
        for bg_url in bg_urls:
            absolute_url = resolve_relative_url(bg_url, base_url)
            base_src = strip_url_params(absolute_url)
            if absolute_url not in images_dict:
                images_dict[absolute_url] = WebsiteImageAsset(
                    src=absolute_url,
                    base_src=base_src,
                    alt="",
                    width=None,
                    height=None,
                    type="css_background",
                )

    return list(images_dict.values())


# =============================================================================
# VIDEOS
# =============================================================================

def extract_videos(html_content: str, base_url: str) -> List[WebsiteVideoAsset]:
    """Extract video tags and iframe embeds (YouTube, Vimeo, etc.)."""
    soup = BeautifulSoup(html_content, "html.parser")
    videos: List[WebsiteVideoAsset] = []

    for video in soup.find_all("video"):
        src = video.get("src")
        poster = video.get("poster")
        width, height = _get_dimensions_from_tag(video)
        sources = []
        for source in video.find_all("source"):
            source_src = source.get("src")
            if source_src:
                sources.append({
                    "src": resolve_relative_url(source_src, base_url),
                    "type": source.get("type", ""),
                })
        videos.append(
            WebsiteVideoAsset(
                src=resolve_relative_url(src, base_url) if src else None,
                type="video_tag",
                width=width,
                height=height,
                autoplay=video.get("autoplay") is not None,
                loop=video.get("loop") is not None,
                muted=video.get("muted") is not None,
                poster=resolve_relative_url(poster, base_url) if poster else None,
                sources=sources if sources else None,
            )
        )

    for iframe in soup.find_all("iframe"):
        iframe_src = iframe.get("src", "")
        if any(p in iframe_src.lower() for p in ["youtube", "vimeo", "wistia", "vidyard"]):
            width, height = _get_dimensions_from_tag(iframe)
            videos.append(
                WebsiteVideoAsset(
                    src=resolve_relative_url(iframe_src, base_url),
                    type="iframe_embed",
                    width=width,
                    height=height,
                )
            )

    return videos


# =============================================================================
# ENTITIES (links, dedup by base URL)
# =============================================================================

def extract_entities(html_content: str, base_url: str) -> List[WebsiteEntityLink]:
    """Extract link entities; dedup by base URL (params stripped)."""
    soup = BeautifulSoup(html_content, "html.parser")
    entities_dict: Dict[str, WebsiteEntityLink] = {}
    base_netloc = urlparse(base_url).netloc

    for link in soup.find_all("a", href=True):
        href = link.get("href")
        text = link.get_text(strip=True)
        if not href or href.startswith("#"):
            continue
        absolute_url = resolve_relative_url(href, base_url)
        base_entity_url = strip_url_params(absolute_url)
        if base_entity_url not in entities_dict:
            entities_dict[base_entity_url] = WebsiteEntityLink(
                url=base_entity_url,
                text=text,
                is_internal=urlparse(absolute_url).netloc == base_netloc,
            )

    return list(entities_dict.values())


# =============================================================================
# VALIDATION STATS
# =============================================================================

def calculate_validation_stats(
    clean_text: str,
    images: List[WebsiteImageAsset],
    videos: List[WebsiteVideoAsset],
    entities: List[WebsiteEntityLink],
) -> ValidationStats:
    """Compute validation stats from extracted data."""
    images_quality_count = sum(
        1
        for img in images
        if img.width and img.height and img.width >= 100 and img.height >= 100
    )
    return ValidationStats(
        page_text_length=len(clean_text),
        images_count=len(images),
        images_quality_count=images_quality_count,
        videos_count=len(videos),
        entities_count=len(entities),
    )


# =============================================================================
# LEVEL 2 DEDUP (optional)
# =============================================================================

def deduplicate_images_by_base_src(images: List[WebsiteImageAsset]) -> List[WebsiteImageAsset]:
    """Level 2 dedup: group by base_src, return best variant per group (by size + alt)."""
    if not images:
        return []
    groups: Dict[str, List[WebsiteImageAsset]] = {}
    for img in images:
        base = img.base_src
        if base not in groups:
            groups[base] = []
        groups[base].append(img)

    deduplicated: List[WebsiteImageAsset] = []
    for base_src, variants in groups.items():
        best_alt = max(
            (img.alt for img in variants if img.alt),
            key=len,
            default="",
        )
        best_variant = max(
            variants,
            key=lambda img: (
                (img.width or 0) * (img.height or 0),
                len(img.alt or ""),
            ),
        )
        deduplicated.append(
            WebsiteImageAsset(
                src=best_variant.src,
                base_src=best_variant.base_src,
                alt=best_alt,
                width=best_variant.width,
                height=best_variant.height,
                loading=best_variant.loading,
                srcset=best_variant.srcset,
                type=best_variant.type,
            )
        )
    return deduplicated


# =============================================================================
# MAIN API
# =============================================================================

def extract_structured_data(html_content: str, base_url: str) -> SectionContent:
    """
    Extract all content from full-page HTML.
    Returns typed SectionContent (clean_text, images, videos, entities, validation_stats).
    """
    clean_text = extract_clean_text(html_content)
    images = extract_images(html_content, base_url)
    videos = extract_videos(html_content, base_url)
    entities = extract_entities(html_content, base_url)
    validation_stats = calculate_validation_stats(clean_text, images, videos, entities)
    return SectionContent(
        clean_text=clean_text,
        images=images,
        videos=videos,
        entities=entities,
        validation_stats=validation_stats,
    )


def extract_section_content(section_html: str, base_url: str) -> SectionContent:
    """
    Extract content from a single section's HTML.
    Same logic as full-page extraction, scoped to section; no validation_stats.
    """
    clean_text = extract_clean_text(section_html)
    images = extract_images(section_html, base_url)
    videos = extract_videos(section_html, base_url)
    entities = extract_entities(section_html, base_url)
    return SectionContent(
        clean_text=clean_text,
        images=images,
        videos=videos,
        entities=entities,
        validation_stats=None,
    )
