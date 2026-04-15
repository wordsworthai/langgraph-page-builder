"""
Shared CSS constants and helpers for LPB UI execution log HTML.
Used by template_selection_ui and data_collection_ui.
"""

from typing import Optional

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry

# Border colors for cards
COLOR_BLUE = "#3b82f6"
COLOR_GOOGLE = "#4285f4"
COLOR_YELP = "#d32323"
COLOR_PURPLE = "#8b5cf6"
COLOR_PINK = "#ec4899"

# Card base style (add border-left color inline)
CARD_BASE = "background: #f9fafb; padding: 10px 12px; border-radius: 4px;"
BADGE_BLUE = "background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 500;"
BADGE_PURPLE = "background: #e0e7ff; color: #4338ca; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 500;"


def wrap_content(html: str, line_height: str = "1.5") -> str:
    """Wrap raw HTML in the standard base div."""
    return f'<div style="font-size: 13px; line-height: {line_height};">{html}</div>'


def make_ui_execution_log_entry(
    node_name: str,
    output_summary: str,
    instance_id: Optional[str] = None,
    display_name: Optional[str] = None,
    show_output: bool = True,
) -> dict:
    """
    Build the dict entry for ui_execution_log.
    Includes instance_id only when provided (e.g. for parallel node instances).
    display_name and show_output allow the consumer to render without NodeRegistry lookup.
    """
    entry: dict = {
        "node_name": node_name,
        "output_summary": output_summary,
        "output_type": "html",
        "show_output": show_output,
    }
    if instance_id is not None:
        entry["instance_id"] = instance_id
    if display_name is not None:
        entry["display_name"] = display_name
    return entry


def make_ui_execution_log_entry_from_registry(
    node_name: str,
    output_summary: str,
    instance_id: Optional[str] = None,
) -> dict:
    """
    Build ui_execution_log entry with display_name and show_output from NodeRegistry.
    Use this when the node is registered and you want registry-driven metadata.
    """
    metadata = NodeRegistry.get_metadata_safe(node_name)
    display_name = metadata.get_display_name() if metadata else None
    show_output = metadata.show_output if metadata else True
    return make_ui_execution_log_entry(
        node_name=node_name,
        output_summary=output_summary,
        instance_id=instance_id,
        display_name=display_name,
        show_output=show_output,
    )
