"""
UI HTML builders for post-processing and autopopulation milestone nodes.
"""

from typing import Any, Dict, List, Optional

from wwai_agent_orchestration.utils.landing_page_builder.ui_logs._common import wrap_content
from wwai_agent_orchestration.utils.landing_page_builder.ui_logs.template_selection_ui import (
    section_breakdown_html,
)


def save_sections_html(section_count: int) -> str:
    """Build HTML for save template sections milestone."""
    inner = (
        '<div style="background: #f9fafb; '
        'padding: 10px 12px; border-radius: 4px;">'
        '<p style="color: #1f2937; margin: 0; font-size: 13px;">Template structure ready for content.</p>'
        "</div>"
    )
    return wrap_content(inner)


def loading_sections_html(
    section_mappings: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Build HTML for loading selected sections milestone."""
    if section_mappings:
        return section_breakdown_html(template_name="", section_mappings=section_mappings)
    inner = (
        '<div style="background: #f9fafb; '
        'padding: 10px 12px; border-radius: 4px;">'
        '<p style="color: #1f2937; margin: 0; font-size: 13px;">Sections loaded successfully.</p>'
        "</div>"
    )
    return wrap_content(inner)


def compilation_html() -> str:
    """Build HTML for template compilation milestone."""
    inner = (
        '<div style="background: #f9fafb; '
        'padding: 10px 12px; border-radius: 4px;">'
        '<p style="color: #1f2937; margin: 0; font-size: 13px;">Page compiled and ready.</p>'
        "</div>"
    )
    return wrap_content(inner)


def autopop_start_html() -> str:
    """Build HTML for content population start milestone."""
    inner = (
        '<div style="background: #f9fafb; '
        'padding: 10px 12px; border-radius: 4px;">'
        '<p style="color: #1f2937; margin: 0; font-size: 13px;">Adding content, images, and styling to your page.</p>'
        "</div>"
    )
    return wrap_content(inner)


def autopop_end_html() -> str:
    """Build HTML for content population end milestone."""
    inner = (
        '<div style="background: #f9fafb; '
        'padding: 10px 12px; border-radius: 4px;">'
        '<p style="color: #1f2937; margin: 0; font-size: 13px;">Your page content is ready.</p>'
        "</div>"
    )
    return wrap_content(inner)


def preparing_template_html() -> str:
    """Build HTML for autopopulation input builder milestone."""
    inner = (
        '<div style="background: #f9fafb; '
        'padding: 10px 12px; border-radius: 4px;">'
        '<p style="color: #1f2937; margin: 0; font-size: 13px;">Template data prepared for content generation.</p>'
        "</div>"
    )
    return wrap_content(inner)


def cache_lookup_html(
    template_name: Optional[str] = None,
    section_mappings: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Build HTML for template selection milestone (cache lookup or generation).

    When template_name and section_mappings are provided: show the finalized layout
    with L0/L1 section breakdown. When not provided: show neutral "Creating your
    custom layout" message. No cache references in user-facing copy.
    """
    if template_name and section_mappings:
        content = section_breakdown_html(template_name, section_mappings)
    else:
        content = (
            '<div style="background: #f9fafb; '
            'padding: 10px 12px; border-radius: 4px;">'
            '<p style="color: #1f2937; margin: 0; font-size: 13px;">Creating your custom layout.</p>'
            "</div>"
        )
    return wrap_content(content)


def container_color_html() -> str:
    """Build HTML for container color agent milestone."""
    inner = (
        '<div style="background: #f9fafb; '
        'padding: 10px 12px; border-radius: 4px;">'
        '<p style="color: #1f2937; margin: 0; font-size: 13px;">Background colors applied.</p>'
        "</div>"
    )
    return wrap_content(inner)


def semantic_names_html() -> str:
    """Build HTML for semantic names agent milestone."""
    inner = (
        '<div style="background: #f9fafb; '
        'padding: 10px 12px; border-radius: 4px;">'
        '<p style="color: #1f2937; margin: 0; font-size: 13px;">Styles applied.</p>'
        "</div>"
    )
    return wrap_content(inner)


def content_planner_html() -> str:
    """Build HTML for content planner milestone."""
    inner = (
        '<div style="background: #f9fafb; '
        'padding: 10px 12px; border-radius: 4px;">'
        '<p style="color: #1f2937; margin: 0; font-size: 13px;">Content plan ready.</p>'
        "</div>"
    )
    return wrap_content(inner)


def template_images_html() -> str:
    """Build HTML for template-level image agent milestone."""
    inner = (
        '<div style="background: #f9fafb; '
        'padding: 10px 12px; border-radius: 4px;">'
        '<p style="color: #1f2937; margin: 0; font-size: 13px;">Images selected.</p>'
        "</div>"
    )
    return wrap_content(inner)


def template_videos_html() -> str:
    """Build HTML for template-level video agent milestone."""
    inner = (
        '<div style="background: #f9fafb; '
        'padding: 10px 12px; border-radius: 4px;">'
        '<p style="color: #1f2937; margin: 0; font-size: 13px;">Videos selected.</p>'
        "</div>"
    )
    return wrap_content(inner)


def final_snapshot_html() -> str:
    """Build HTML for final snapshot milestone."""
    inner = (
        '<div style="background: #f9fafb; '
        'padding: 10px 12px; border-radius: 4px;">'
        '<p style="color: #1f2937; margin: 0; font-size: 13px;">All content ready.</p>'
        "</div>"
    )
    return wrap_content(inner)


def content_text_finalized_html() -> str:
    """Build HTML for text content finalization milestone."""
    inner = (
        '<div style="background: #f9fafb; '
        'padding: 10px 12px; border-radius: 4px;">'
        '<p style="color: #1f2937; margin: 0; font-size: 13px;">Text content ready.</p>'
        "</div>"
    )
    return wrap_content(inner)


def content_media_finalized_html() -> str:
    """Build HTML for media finalization milestone."""
    inner = (
        '<div style="background: #f9fafb; '
        'padding: 10px 12px; border-radius: 4px;">'
        '<p style="color: #1f2937; margin: 0; font-size: 13px;">Images and videos ready.</p>'
        "</div>"
    )
    return wrap_content(inner)
