"""
Pure merge utilities for combining parent template_json with a newly generated
section (replace mode only).

Used by template_compilation_node when in regenerate_section flow.
"""

from typing import Any, Dict, List, Tuple


def _normalize_mapping(mapping: List) -> List[Tuple[str, int]]:
    """Normalize mapping entries to (unique_id, index) tuples."""
    result: List[Tuple[str, int]] = []
    for e in mapping or []:
        if isinstance(e, (list, tuple)) and len(e) >= 2:
            result.append((str(e[0]), int(e[1])))
        elif isinstance(e, tuple):
            result.append((str(e[0]), int(e[1])))
    return result


def _build_merged_mapping_replace(
    source_mapping: List[Tuple[str, int]],
    new_mapping: List[Tuple[str, int]],
    replace_index: int,
) -> List[Tuple[str, int]]:
    """Replace entry at replace_index with new section's unique_id."""
    result = [(entry[0], idx) for idx, entry in enumerate(source_mapping)]
    if new_mapping:
        result[replace_index] = (new_mapping[0][0], replace_index)
    return result


def merge_parent_and_new_section_template_json(
    source_template_json: Dict[str, Any],
    source_mapping: List,
    new_template_json: Dict[str, Any],
    new_mapping: List,
    target_index: int,
) -> Tuple[Dict[str, Any], List[Tuple[str, int]]]:
    """
    Merge parent template_json with newly generated section template_json.

    Replaces the section at target_index: removes the old section's key from
    source before merging, then overwrites with the AI-generated content.

    Handles source_already_has_new_section (from add_section_in_place): in that
    case the new section key exists in source (Lorem placeholder); we overwrite
    with the AI-generated content.

    Args:
        source_template_json: Parent's template_json (keyed by unique_section_id).
        source_mapping: Parent's section_id_and_index_mapping.
        new_template_json: New section's template_json (single key).
        new_mapping: New section's section_id_and_index_mapping (one entry).
        target_index: 0-based position (replace_index).

    Returns:
        Merged (template_json, section_id_and_index_mapping) for populated_template_json_override.
    """
    source_template_json = dict(source_template_json)
    source_mapping_norm = _normalize_mapping(source_mapping)
    new_mapping_norm = _normalize_mapping(new_mapping)

    # Remove the old section's key from source
    if target_index < len(source_mapping_norm):
        old_unique_id = source_mapping_norm[target_index][0]
        if old_unique_id in source_template_json:
            del source_template_json[old_unique_id]

    # Merge: new overwrites source
    merged = {**source_template_json, **new_template_json}

    # Build merged section_id_and_index_mapping
    merged_mapping = _build_merged_mapping_replace(
        source_mapping_norm, new_mapping_norm, target_index
    )

    return merged, merged_mapping
