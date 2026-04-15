"""
Section data context utilities.

Maps section IDs to the appropriate data_context (full vs nav) based on
section type (header/footer use nav context; body uses full context).
"""

from typing import Dict, List, Any

from wwai_agent_orchestration.constants.section_types import (
    HEADER_SECTION_L0_LIST,
    FOOTER_SECTION_L0_LIST,
)


def _build_section_id_to_l0(resolved_template_recommendations: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Build section_id -> section_l0 map from resolved_template_recommendations.

    Populates both bare section_id and section_id_{idx} keys so lookup works
    whether fanout uses agents_context.sections keys (section_id_index format
    from template_unique_section_id_map) or bare section_id.
    """
    if not resolved_template_recommendations:
        return {}
    section_mappings = resolved_template_recommendations[0].get("section_mappings", [])
    result: Dict[str, str] = {}
    for idx, m in enumerate(section_mappings):
        sid = m.get("section_id", "")
        l0 = m.get("section_l0", "")
        if sid:
            result[sid] = l0
            result[f"{sid}_{idx}"] = l0  # Match template_unique_section_id_map key format
    return result


def get_section_id_to_data_context_mapping(
    section_ids: List[str],
    resolved_template_recommendations: List[Dict[str, Any]],
    data_context_full: str,
    data_context_nav: str,
) -> Dict[str, str]:
    """
    Return mapping from section_id to the data_context string to use.

    Header/footer sections get data_context_nav; body sections get data_context_full.

    Args:
        section_ids: List of section IDs to process
        resolved_template_recommendations: Template recommendations with section_mappings
        data_context_full: Full context for body sections
        data_context_nav: Nav context for header/footer sections

    Returns:
        Dict mapping section_id -> data_context string
    """
    section_id_to_l0 = _build_section_id_to_l0(resolved_template_recommendations)
    header_l0_set = set(HEADER_SECTION_L0_LIST)
    footer_l0_set = set(FOOTER_SECTION_L0_LIST)

    def _resolve_section_l0(sid: str) -> str:
        """Resolve section_l0 from section_id, handling agents_context format (base_id_suffix)."""
        # Direct lookup first
        l0 = section_id_to_l0.get(sid, "")
        if l0:
            return l0
        # agents_context.sections keys may be base_id_suffix (e.g. 69666bcddb7c2f2d24b581da_b5ff736647871dfd)
        # Split by _ and try the first part (base section_id from section_mappings)
        if "_" in sid:
            base_id = sid.split("_", 1)[0]
            return section_id_to_l0.get(base_id, "")
        return ""

    result: Dict[str, str] = {}
    for section_id in section_ids:
        section_l0 = _resolve_section_l0(section_id)
        is_header_or_footer = section_l0 in header_l0_set or section_l0 in footer_l0_set
        chosen = data_context_nav if (is_header_or_footer and data_context_nav) else data_context_full
        result[section_id] = chosen
    return result
