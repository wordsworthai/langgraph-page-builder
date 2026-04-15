"""
UI HTML builders for template selection nodes.
"""

from typing import Dict, Any, List

from wwai_agent_orchestration.utils.landing_page_builder.ui_logs._common import (
    wrap_content,
    BADGE_PURPLE,
)


def section_breakdown_html(template_name: str, section_mappings: List[Dict[str, Any]]) -> str:
    """
    Build HTML for resolved template section breakdown (L0/L1).
    Shows all picked sections in order. Template name is not displayed.
    """
    section_items = []
    for idx, mapping in enumerate(section_mappings, 1):
        l0 = mapping.get("section_l0", "Unknown")
        l1 = mapping.get("section_l1", "Unknown")
        if l0 == l1:
            label = l0
        else:
            label = f"{l0} ({l1})"
        section_items.append(
            f'<div style="margin-bottom: 6px;">'
            f'<span style="color: #6b7280; font-size: 11px; margin-right: 8px;">{idx}.</span>'
            f'<span style="font-weight: 500; color: #374151; font-size: 12px;">{label}</span>'
            f"</div>"
        )

    inner = (
        '<div style="margin-bottom: 10px;">'
        '<p style="color: #6b7280; font-size: 12px; margin: 0 0 8px 0;">Your layout sections:</p>'
        "</div>"
        '<div style="background: #f9fafb; padding: 10px 12px; border-radius: 4px;">'
        f'{"".join(section_items)}'
        "</div>"
    )
    return wrap_content(inner)


def _section_label(mapping: Dict[str, Any]) -> str:
    """Format section L0/L1 as display label."""
    l0 = mapping.get("section_l0", "Unknown")
    l1 = mapping.get("section_l1", "Unknown")
    return f"{l0} ({l1})" if l0 != l1 else l0


def template_list_html(
    templates: List[Dict[str, Any]],
    intro_text: str = "Deciding between 3 templates. Here are the sections in each:",
) -> str:
    """
    Build HTML for template options list.
    Shows each template with its section names (L0/L1) instead of generic template_1, template_2.
    """
    template_items = []
    for idx, t in enumerate(templates, 1):
        section_info = t.get("section_info", [])
        section_labels = [_section_label(s) for s in section_info]
        section_count = len(section_labels)
        # Use "Option 1", "Option 2", "Option 3" instead of template_1, template_2
        option_label = f"Option {idx}"
        section_lines = "".join(
            f'<div style="margin-bottom: 4px; font-size: 12px; color: #374151;">'
            f'<span style="color: #6b7280; margin-right: 6px;">{i}.</span>{label}</div>'
            for i, label in enumerate(section_labels, 1)
        )
        template_items.append(
            '<div style="background: #f9fafb; padding: 10px 12px; border-radius: 4px; margin-bottom: 8px;">'
            '<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">'
            f'<span style="font-weight: 600; color: #1f2937; font-size: 13px;">{option_label}</span>'
            f'<span style="{BADGE_PURPLE}">{section_count} sections</span>'
            "</div>"
            f'<div style="padding-left: 4px;">{section_lines}</div>'
            "</div>"
        )

    inner = (
        f'<p style="color: #6b7280; margin: 0 0 12px 0; font-size: 13px;">{intro_text}</p>'
        '<div style="display: flex; flex-direction: column; gap: 0;">'
        f'{"".join(template_items)}'
        "</div>"
    )
    return wrap_content(inner)
