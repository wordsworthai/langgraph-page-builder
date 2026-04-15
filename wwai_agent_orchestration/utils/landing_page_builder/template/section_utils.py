"""
Pure data-transform utilities for template section classification and grouping.

No DB access -- just deterministic transforms on section data structures.
"""

import hashlib
from typing import Dict, Any, List, Tuple

from wwai_agent_orchestration.constants.section_types import HEADER_SECTION_L0_LIST, FOOTER_SECTION_L0_LIST


def classify_sections(
    section_mappings: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Split section_mappings into header, body, and footer groups based on section_l0.

    Returns:
        Tuple of (header_mappings, body_mappings, footer_mappings)
    """
    header, body, footer = [], [], []
    for mapping in section_mappings:
        l0 = mapping.get("section_l0", "")
        if l0 in HEADER_SECTION_L0_LIST:
            header.append(mapping)
        elif l0 in FOOTER_SECTION_L0_LIST:
            footer.append(mapping)
        else:
            body.append(mapping)
    return header, body, footer


def extract_section_ids(mappings: List[Dict[str, Any]]) -> List[str]:
    """Extract section_id values from a list of section mappings."""
    return [m.get("section_id") for m in mappings if m.get("section_id")]


def section_category(section_l0: str) -> str:
    """Return 'header', 'footer', or 'body' for a given section_l0 value."""
    if section_l0 in HEADER_SECTION_L0_LIST:
        return "header"
    if section_l0 in FOOTER_SECTION_L0_LIST:
        return "footer"
    return "body"


def validate_insert_mode(
    insert_index: int,
    existing_mappings: List[Dict[str, Any]],
    section_doc: Dict[str, Any],
) -> None:
    """
    Validate constraints for insert mode:
      - Cannot insert at top (index <= 0) or bottom (index >= N)
      - Cannot insert a header or footer section
    """
    n = len(existing_mappings)

    if insert_index <= 0:
        raise ValueError(
            f"Insert mode: insert_index must be > 0 (cannot insert at top). "
            f"Got {insert_index}. Use replace mode to change the header."
        )
    if insert_index >= n:
        raise ValueError(
            f"Insert mode: insert_index must be < {n} (cannot insert at bottom). "
            f"Got {insert_index}. Use replace mode to change the footer."
        )

    new_l0 = section_doc.get("section_l0", "")
    cat = section_category(new_l0)
    if cat != "body":
        raise ValueError(
            f"Insert mode: cannot insert a {cat} section (section_l0='{new_l0}'). "
            f"Only body sections can be inserted. Use replace mode to swap header/footer."
        )


def validate_replace_mode(
    replace_index: int,
    existing_mappings: List[Dict[str, Any]],
    section_doc: Dict[str, Any],
) -> None:
    """
    Validate constraints for replace mode:
      - replace_index must be in [0, N)
      - New section must be the same category as the one being replaced
    """
    n = len(existing_mappings)

    if replace_index < 0 or replace_index >= n:
        raise ValueError(
            f"Replace mode: replace_index must be in [0, {n}). Got {replace_index}."
        )

    old_l0 = existing_mappings[replace_index].get("section_l0", "")
    new_l0 = section_doc.get("section_l0", "")
    old_cat = section_category(old_l0)
    new_cat = section_category(new_l0)

    if old_cat != new_cat:
        raise ValueError(
            f"Replace mode: type mismatch. Section at index {replace_index} is "
            f"'{old_cat}' (section_l0='{old_l0}'), but the new section is "
            f"'{new_cat}' (section_l0='{new_l0}'). "
            f"Only same-type replacement is allowed."
        )


def partition_unique_map(
    full_map: Dict[str, str],
    section_ids: List[str],
    all_section_ids: List[str],
) -> Dict[str, str]:
    """
    Extract entries from the full template_unique_section_id_map that belong to
    a subset of section IDs, using the original index in the all_section_ids list.
    """
    subset_map = {}
    for original_index, sid in enumerate(all_section_ids):
        if sid in section_ids:
            lookup_key = f"{sid}_{original_index}"
            if lookup_key in full_map:
                subset_map[lookup_key] = full_map[lookup_key]
    return subset_map


def build_section_group(
    mappings: List[Dict[str, Any]],
    full_map: Dict[str, str],
    all_section_ids: List[str],
) -> Dict[str, Any]:
    """Build a section group dict (used for header/body/footer)."""
    ids = extract_section_ids(mappings)
    return {
        "section_ids": ids,
        "section_count": len(ids),
        "section_mappings": mappings,
        "template_unique_section_id_map": partition_unique_map(full_map, ids, all_section_ids),
    }


def get_merged_all_from_groups(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Derive merged group equivalent to former 'all' from header, body, footer.
    Always derives from groups; no fallback to doc.get('all').
    """
    header = doc.get("header") or {}
    body = doc.get("body") or {}
    footer = doc.get("footer") or {}

    section_ids = (
        list(header.get("section_ids", []))
        + list(body.get("section_ids", []))
        + list(footer.get("section_ids", []))
    )
    section_mappings = (
        list(header.get("section_mappings", []))
        + list(body.get("section_mappings", []))
        + list(footer.get("section_mappings", []))
    )
    unique_map = {
        **(header.get("template_unique_section_id_map") or {}),
        **(body.get("template_unique_section_id_map") or {}),
        **(footer.get("template_unique_section_id_map") or {}),
    }
    return {
        "section_ids": section_ids,
        "section_count": len(section_ids),
        "section_mappings": section_mappings,
        "template_unique_section_id_map": unique_map,
    }


def create_stable_mapping(
    section_ids: List[str],
    generation_version_id: str,
) -> Dict[str, str]:
    """
    Create a stable mapping from repo_section_id_index to unique_section_id.

    Uses a deterministic algorithm based on generation_version_id to ensure
    the same mapping is created for the same inputs.

    Args:
        section_ids: List of section IDs from resolved_template_recommendations
        generation_version_id: Generation version ID used as seed for determinism

    Returns:
        Dict mapping {section_id}_{index} -> unique_section_id
    """
    template_unique_section_id_map: Dict[str, str] = {}
    for index, section_id in enumerate(section_ids):
        hash_input = f"{generation_version_id}_{section_id}_{index}"
        hash_bytes = hashlib.sha256(hash_input.encode()).digest()
        unique_id_suffix = hash_bytes[:8].hex()
        unique_section_id = f"{section_id}_{unique_id_suffix}"
        lookup_key = f"{section_id}_{index}"
        template_unique_section_id_map[lookup_key] = unique_section_id
    return template_unique_section_id_map


def extract_ordered_unique_ids(group_map: Dict[str, str]) -> List[str]:
    """
    Extract unique-section-id values from a group map, ordered by the
    original index encoded in each key (format: ``{section_id}_{index}``).
    """
    if not group_map:
        return []
    entries = []
    for key, value in group_map.items():
        last_underscore = key.rfind("_")
        if last_underscore > 0:
            try:
                idx = int(key[last_underscore + 1:])
                entries.append((idx, value))
            except ValueError:
                entries.append((0, value))
        else:
            entries.append((0, value))
    entries.sort(key=lambda x: x[0])
    return [value for _, value in entries]


def create_stable_mapping_with_insert(
    new_section_ids: List[str],
    generation_version_id: str,
    source_unique_map: Dict[str, str],
    source_section_ids: List[str],
    inserted_section_id: str,
    insert_index: int,
) -> Dict[str, str]:
    """
    Build a template_unique_section_id_map for a section list that has one new
    section inserted, preserving the hash *values* of existing sections.

    Only the map keys are re-indexed to match the new positions, and a fresh
    hash is generated for the inserted section.
    """
    old_value_by_key: Dict[str, str] = {}
    for old_idx, sid in enumerate(source_section_ids):
        key = f"{sid}_{old_idx}"
        if key in source_unique_map:
            old_value_by_key[key] = source_unique_map[key]

    new_map: Dict[str, str] = {}
    source_cursor = 0
    for new_idx, sid in enumerate(new_section_ids):
        new_key = f"{sid}_{new_idx}"
        if new_idx == insert_index and sid == inserted_section_id:
            # Use "_inserted" suffix so hash never collides with source's value
            # for the position being shifted (source uses same gen_sid_idx).
            # occurrence_count ensures uniqueness when inserting same section
            # multiple times at the same index.
            occurrence_count = sum(1 for s in source_section_ids if s == inserted_section_id)
            hash_input = f"{generation_version_id}_{sid}_{new_idx}_inserted_{occurrence_count}"
            hash_bytes = hashlib.sha256(hash_input.encode()).digest()
            unique_id_suffix = hash_bytes[:8].hex()
            new_map[new_key] = f"{sid}_{unique_id_suffix}"
        else:
            old_key = f"{source_section_ids[source_cursor]}_{source_cursor}"
            new_map[new_key] = old_value_by_key.get(old_key, "")
            source_cursor += 1

    return new_map


def create_stable_mapping_with_replace(
    section_ids: List[str],
    generation_version_id: str,
    source_unique_map: Dict[str, str],
    source_section_ids: List[str],
    replace_index: int,
) -> Dict[str, str]:
    """
    Build a template_unique_section_id_map after replacing the section at
    replace_index. Preserves hash values for all other positions; only
    the replaced position gets a fresh hash (unless same section_id, e.g.
    regenerate content or frontend no-op).
    """
    new_map: Dict[str, str] = {}
    for idx, sid in enumerate(section_ids):
        key = f"{sid}_{idx}"
        if idx == replace_index:
            source_sid = source_section_ids[replace_index]
            if source_sid == sid:
                # Same section (regenerate content or frontend no-op): preserve mapping
                old_key = f"{source_sid}_{idx}"
                existing = source_unique_map.get(old_key, "")
                if existing:
                    new_map[key] = existing
                else:
                    hash_input = f"{generation_version_id}_{sid}_{idx}"
                    hash_bytes = hashlib.sha256(hash_input.encode()).digest()
                    new_map[key] = f"{sid}_{hash_bytes[:8].hex()}"
            else:
                # Different section: generate fresh hash
                hash_input = f"{generation_version_id}_{sid}_{idx}"
                hash_bytes = hashlib.sha256(hash_input.encode()).digest()
                new_map[key] = f"{sid}_{hash_bytes[:8].hex()}"
        else:
            old_key = f"{source_section_ids[idx]}_{idx}"
            new_map[key] = source_unique_map.get(old_key, "")
    return new_map
