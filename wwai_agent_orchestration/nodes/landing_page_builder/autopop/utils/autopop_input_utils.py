"""
Shared utilities for autopopulation input builder nodes.

Extracted from autopopulation_input_builder to be reusable by both the
standard node and the add_section variant.
"""

from typing import Dict, Any, List, Optional

from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState


def get_use_mock_autopopulation(execution_config: Any) -> bool:
    """Extract use_mock_autopopulation flag from execution_config."""
    if not execution_config:
        return True
    if hasattr(execution_config, "autopop"):
        return execution_config.autopop.use_mock_autopopulation
    if isinstance(execution_config, dict):
        autopop = execution_config.get("autopop") or {}
        return autopop.get("use_mock_autopopulation", True) if isinstance(autopop, dict) else True
    return True


def get_palette_and_fonts_input(state: LandingPageWorkflowState) -> Optional[Dict[str, Any]]:
    """Build palette_and_fonts_input dict from state.input.brand_context."""
    if not state.input:
        return None
    p = state.input.brand_context.palette if state.input.brand_context else None
    f = state.input.brand_context.font_family if state.input.brand_context else None
    if p is not None or f is not None:
        return {"palette_input": p, "font_family": f}
    return None


def get_section_ids_from_resolved_template_recommendations(state: LandingPageWorkflowState) -> List[str]:
    """Extract section_ids from resolved_template_recommendations."""
    resolved = state.resolved_template_recommendations
    if not resolved:
        raise ValueError("No resolved_template_recommendations found")
    first_template = resolved[0]
    section_mappings = first_template.get("section_mappings", [])
    section_ids = [m.get("section_id") for m in section_mappings if m.get("section_id")]
    if not section_ids:
        raise ValueError("No section IDs found in first template")
    return section_ids
