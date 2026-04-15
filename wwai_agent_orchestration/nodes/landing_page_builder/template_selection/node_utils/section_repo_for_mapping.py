"""
Section repo for mapping: prepare candidates for LLM, get sections from LLM response.

Prepares section candidates (filter repo to template L0/L1, sample up to N per type,
encode real IDs to human-readable for the LLM) and, after the LLM returns, gets real
sections from the response (decode IDs, enrich with screenshots, return dict).
"""

import random
from typing import Dict, Any, List, Tuple
from collections import defaultdict

from wwai_agent_orchestration.core.observability.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# Filter and sample candidates
# ============================================================================

def filter_section_repo_for_template(
    section_repo: List[Dict],
    template_sections: List[Dict],
    max_sections_per_l0_l1: int = 3,
) -> Dict[Tuple[str, str], List[Dict[str, str]]]:
    """
    Narrow section repo to this template's L0/L1 types and sample up to
    max_sections_per_l0_l1 per type. Returns dict (L0,L1) -> list of {id, layout_description}.
    """
    template_l0_l1_combinations = set()
    for section in template_sections:
        template_l0_l1_combinations.add((section['section_l0'], section['section_l1']))

    logger.info(
        f"Template has {len(template_l0_l1_combinations)} unique L0/L1 combinations",
        node="resolve_template_sections_from_repo"
    )

    repo_by_l0_l1 = defaultdict(list)
    for entry in section_repo:
        entry_section_l0 = entry.get('section_l0')
        entry_section_l1 = entry.get('section_l1')
        entry_id = entry.get('section_id', str(entry.get('_id')))
        entry_layout_desc = entry.get('section_layout_description', '')
        l0_l1_key = (entry_section_l0, entry_section_l1)
        repo_by_l0_l1[l0_l1_key].append({
            'id': entry_id,
            'layout_description': entry_layout_desc,
        })

    filtered_repo = {}
    for l0_l1_key in template_l0_l1_combinations:
        sections = repo_by_l0_l1.get(l0_l1_key, [])
        if not sections:
            logger.warning(
                f"No sections found for {l0_l1_key[0]} - {l0_l1_key[1]}",
                node="resolve_template_sections_from_repo"
            )
            continue
        if len(sections) <= max_sections_per_l0_l1:
            selected = sections
        else:
            selected = random.sample(sections, max_sections_per_l0_l1)
        filtered_repo[l0_l1_key] = selected

    total_sections = sum(len(sections) for sections in filtered_repo.values())
    logger.info(
        f"Filtered repo size: {total_sections} sections across {len(filtered_repo)} L0/L1 combinations",
        node="resolve_template_sections_from_repo"
    )

    return filtered_repo


# ============================================================================
# Encode / decode IDs for LLM
# ============================================================================

def encode_section_ids_for_llm(
    filtered_section_repo: Dict[Tuple[str, str], List[Dict[str, str]]]
) -> Tuple[Dict[Tuple[str, str], List[Dict[str, str]]], Dict[str, str]]:
    """
    Encode real section IDs to human-readable form (e.g. L0_L1_Idx) for the LLM.
    Returns (encoded_repo, id_mapping) so we can decode LLM output back to real section_id.
    """
    encoded_repo = {}
    id_mapping = {}

    for (section_l0, section_l1), sections_list in filtered_section_repo.items():
        encoded_sections = []

        for idx, section in enumerate(sections_list, start=1):
            original_id = section['id']
            l0_clean = section_l0.replace(' ', '_').replace('/', '_').replace('-', '_')
            l1_clean = section_l1.replace(' ', '_').replace('/', '_').replace('-', '_')
            human_readable_id = f"{l0_clean}_{l1_clean}_{idx}"
            id_mapping[human_readable_id] = original_id
            encoded_section = {
                'id': human_readable_id,
                'layout_description': section.get('layout_description', '')
            }
            encoded_sections.append(encoded_section)

        encoded_repo[(section_l0, section_l1)] = encoded_sections

    logger.debug(
        f"Encoded {len(id_mapping)} section IDs",
        node="resolve_template_sections_from_repo"
    )

    return encoded_repo, id_mapping


def decode_section_ids_from_llm(
    section_mappings: List[Dict[str, Any]],
    id_mapping: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Decode LLM-returned human-readable IDs to real section_id using id_mapping (join-back).
    Validates ID exists and L0/L1 consistency.
    """
    decoded_mappings = []

    for idx, section_mapping in enumerate(section_mappings, start=1):
        decoded_mapping = section_mapping.copy()
        human_readable_id = section_mapping.get('section_id', '')

        if human_readable_id not in id_mapping:
            logger.error(
                f"LLM hallucinated section_id at index {idx}",
                node="resolve_template_sections_from_repo",
                hallucinated_id=human_readable_id,
                section_mapping=section_mapping
            )
            raise ValueError(
                f"LLM generated invalid section_id: '{human_readable_id}' at section index {idx}. "
                f"This ID was not in the provided options."
            )

        id_parts = human_readable_id.rsplit('_', 1)
        if len(id_parts) != 2:
            raise ValueError(f"Invalid ID format: '{human_readable_id}' at section index {idx}")

        l0_l1_part = id_parts[0]
        section_l0 = section_mapping.get('section_l0', '')
        section_l1 = section_mapping.get('section_l1', '')
        l0_clean = section_l0.replace(' ', '_').replace('/', '_').replace('-', '_')
        l1_clean = section_l1.replace(' ', '_').replace('/', '_').replace('-', '_')
        expected_l0_l1_part = f"{l0_clean}_{l1_clean}"

        is_exception = (
            section_l1 == "Benefits Listicle with embedded products carousel, sticky product and media" and
            l0_l1_part == "Product_Highlights_Benefits_Listicle"
        )

        if not is_exception and l0_l1_part != expected_l0_l1_part:
            logger.error(
                f"L0/L1 mismatch at section index {idx}",
                node="resolve_template_sections_from_repo",
                expected=expected_l0_l1_part,
                actual=l0_l1_part
            )
            raise AssertionError(
                f"L0/L1 mismatch for section_id '{human_readable_id}' at index {idx}. "
                f"Expected '{expected_l0_l1_part}', got '{l0_l1_part}'."
            )

        decoded_mapping['section_id'] = id_mapping[human_readable_id]
        decoded_mappings.append(decoded_mapping)

    return decoded_mappings


# ============================================================================
# Screenshot enrichment
# ============================================================================

def get_section_screenshot_by_id(
    section_repo: List[Dict],
    section_id: str,
    section_l0: str,
    section_l1: str
) -> Tuple[str, str]:
    """
    Get desktop and mobile screenshot URLs for a section by id and L0/L1.
    """
    long_name = "Benefits Listicle with embedded products carousel, sticky product and media"
    short_name = "Benefits Listicle"

    for entry in section_repo:
        entry_id = str(entry.get('_id', entry.get('section_id')))
        entry_l0 = entry.get('section_l0')
        entry_l1 = entry.get('section_l1')
        desktop_url = entry.get('desktop_image_url')
        mobile_url = entry.get('mobile_image_url')

        if entry_id == section_id and entry_l0 == section_l0:
            if entry_l1 == section_l1:
                return desktop_url, mobile_url
            if (entry_l1 == long_name and section_l1 == short_name) or \
               (entry_l1 == short_name and section_l1 == long_name):
                return desktop_url, mobile_url

    assert False, (
        f"No entry found for section_id={section_id}, "
        f"section_l0={section_l0}, section_l1={section_l1}"
    )


# ============================================================================
# Public entry points
# ============================================================================

def prepare_section_candidates_for_llm(
    section_repo: List[Dict],
    template_sections: List[Dict],
    max_sections_per_l0_l1: int = 3,
) -> Tuple[Dict[Tuple[str, str], List[Dict[str, str]]], Dict[str, str]]:
    """
    Prepare section candidates and encode IDs for the LLM.
    Returns (encoded_repo, id_mapping). Use before the LLM call.
    """
    filtered_repo = filter_section_repo_for_template(
        section_repo=section_repo,
        template_sections=template_sections,
        max_sections_per_l0_l1=max_sections_per_l0_l1,
    )
    return encode_section_ids_for_llm(filtered_repo)


def get_sections_from_llm_response(
    section_mappings: List[Dict[str, Any]],
    id_mapping: Dict[str, str],
    section_repo: List[Dict],
    template_id: str,
    template_name: str,
) -> Dict[str, Any]:
    """
    Decode LLM response to real section IDs, enrich with screenshots.
    Returns dict with template_id, template_name, section_mappings. Use after the LLM call.
    """
    decoded_mappings = decode_section_ids_from_llm(section_mappings, id_mapping)

    for section_mapping in decoded_mappings:
        desktop_screenshot, mobile_screenshot = get_section_screenshot_by_id(
            section_repo=section_repo,
            section_id=section_mapping['section_id'],
            section_l0=section_mapping['section_l0'],
            section_l1=section_mapping['section_l1'],
        )
        section_mapping['desktop_screenshot'] = desktop_screenshot
        section_mapping['mobile_screenshot'] = mobile_screenshot

    return {
        "template_id": template_id,
        "template_name": template_name,
        "section_mappings": decoded_mappings,
    }
