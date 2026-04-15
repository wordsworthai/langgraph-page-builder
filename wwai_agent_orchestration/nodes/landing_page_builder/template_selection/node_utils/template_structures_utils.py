"""
L0/L1 validation and template-format helpers for generate_template_structures.

Pure functions: build whitelist from allowed section types, validate template
sections against it, and transform LLM recommendation dict to list of template dicts.
"""

import uuid
from typing import Dict, Any, List, Tuple

from wwai_agent_orchestration.core.observability.logger import get_logger

logger = get_logger(__name__)


def build_valid_l0_l1_whitelist(filtered_type_details: List[Dict[str, Any]]) -> set:
    """Build set of allowed (L0, L1) tuples from type-detail dicts (section_type_l1 -> section_l0, section_subtype_l2 -> section_l1)."""
    valid_combinations = set()
    for type_detail in filtered_type_details:
        l0 = type_detail.get('section_type_l1', '')    # Maps to MongoDB section_l0
        l1 = type_detail.get('section_subtype_l2', '')  # Maps to MongoDB section_l1
        if l0 and l1:
            valid_combinations.add((l0, l1))
    return valid_combinations


def validate_templates_l0_l1(
    templates_dict: Dict[str, List],
    allowed_section_types: List[Dict[str, Any]],
) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Validate all L0/L1 combinations in generated templates.
    Builds the allowed (L0, L1) whitelist from allowed_section_types internally.

    Args:
        templates_dict: Dict mapping template_name -> list of sections
        allowed_section_types: Type-detail dicts (section_type_l1, section_subtype_l2) to build whitelist from

    Returns:
        Tuple of (is_valid, list_of_invalid_sections)
    """
    valid_l0_l1_combinations = build_valid_l0_l1_whitelist(allowed_section_types)
    invalid_sections = []

    for template_name, sections_list in templates_dict.items():
        # Get string template name
        template_name_str = (
            template_name.value if hasattr(template_name, 'value')
            else str(template_name)
        )

        for idx, section in enumerate(sections_list, 1):
            # Extract L0/L1 (handle both dict and object)
            if isinstance(section, dict):
                section_l0 = section.get('section_l0', '')
                section_l1 = section.get('section_l1', '')
            else:
                section_l0 = (
                    section.section_l0.value if hasattr(section.section_l0, 'value')
                    else str(section.section_l0)
                )
                section_l1 = (
                    section.section_l1.value if hasattr(section.section_l1, 'value')
                    else str(section.section_l1)
                )

            # Check if L0/L1 combination is valid
            if (section_l0, section_l1) not in valid_l0_l1_combinations:
                invalid_sections.append({
                    'template': template_name_str,
                    'section_index': idx,
                    'section_l0': section_l0,
                    'section_l1': section_l1
                })

    is_valid = len(invalid_sections) == 0
    return is_valid, invalid_sections


def transform_to_template_format(
    l0_l1_recommendations: Dict[str, List],
    query_hash: str,
    business_name: str
) -> List[Dict[str, Any]]:
    """
    Transform LLM output to template format.

    Handles Optional fields that may be None: section_index (fallback to enumerate),
    why and section_content_description (empty string). Returns list of template dicts
    with template_id, template_name, section_info, query_hash, business_name.
    """
    templates = []

    for template_name, sections_list in l0_l1_recommendations.items():
        # Get string template name
        template_name_str = (
            template_name.value if hasattr(template_name, 'value')
            else str(template_name)
        )

        # Convert sections to expected format
        # Use enumerate for robust indexing (safety net if LLM omits section_index)
        section_info = []
        for idx, section in enumerate(sections_list, start=1):
            # Handle both dict and object formats
            if isinstance(section, dict):
                # Get section_index, falling back to enumerate index if None or missing
                section_index = section.get('section_index')
                if section_index is None:
                    section_index = idx

                # Build reasoning from optional fields (handle None)
                content_desc = section.get('section_content_description') or ''
                why_text = section.get('why') or ''
                reasoning = f"Content: {content_desc} | Impact: {why_text}"

                section_info.append({
                    "section_index": section_index,
                    "section_l0": section.get('section_l0', ''),
                    "section_l1": section.get('section_l1', ''),
                    "reasoning": reasoning
                })
            else:
                # Object format - get section_index with fallback
                section_index = getattr(section, 'section_index', None)
                if section_index is None:
                    section_index = idx

                # Build reasoning from optional fields (handle None)
                content_desc = getattr(section, 'section_content_description', None) or ''
                why_text = getattr(section, 'why', None) or ''
                reasoning = f"Content: {content_desc} | Impact: {why_text}"

                section_info.append({
                    "section_index": section_index,
                    "section_l0": (
                        section.section_l0.value if hasattr(section.section_l0, 'value')
                        else str(getattr(section, 'section_l0', ''))
                    ),
                    "section_l1": (
                        section.section_l1.value if hasattr(section.section_l1, 'value')
                        else str(getattr(section, 'section_l1', ''))
                    ),
                    "reasoning": reasoning
                })

        # Create template entry
        template = {
            "template_id": str(uuid.uuid4()),
            "template_name": template_name_str,
            "section_info": section_info,
            "query_hash": query_hash,
            "business_name": business_name
        }
        templates.append(template)

    return templates
