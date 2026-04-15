"""
Section media source utilities.

Determines which image slots should use LogoProvider vs media_service based on
section type (header/footer) and slot dimensions.
Fetches from both sources and merges results.
"""

from typing import Any, Dict, List, Tuple

from wwai_agent_orchestration.constants.section_types import (
    HEADER_SECTION_L0_LIST,
    FOOTER_SECTION_L0_LIST,
)
from wwai_agent_orchestration.data.providers.logo_provider import LogoProvider
from wwai_agent_orchestration.data.providers.models.logo import LogoInput
from wwai_agent_orchestration.data.services.media.media_service import media_service

LOGO_SLOT_MAX_WIDTH = 100
LOGO_SLOT_MAX_HEIGHT = 100


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
            result[f"{sid}_{idx}"] = l0
    return result


def _resolve_section_l0(section_id: str, section_id_to_l0: Dict[str, str]) -> str:
    """
    Resolve section_l0 from section_id, handling agents_context format (base_id_suffix).
    """
    l0 = section_id_to_l0.get(section_id, "")
    if l0:
        return l0
    if "_" in section_id:
        base_id = section_id.split("_", 1)[0]
        return section_id_to_l0.get(base_id, "")
    return ""


def partition_image_slots_by_source(
    slots: List[Dict[str, Any]],
    resolved_template_recommendations: List[Dict[str, Any]],
    max_logo_width: int = LOGO_SLOT_MAX_WIDTH,
    max_logo_height: int = LOGO_SLOT_MAX_HEIGHT,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Partition image slots into logo slots vs media_service slots.

    Logo slots: header/footer sections with width < max_logo_width and height < max_logo_height.
    Media service slots: everything else.

    Args:
        slots: List of slot dicts with width, height, slot_identity (section_id, element_id, etc.)
        resolved_template_recommendations: Template recommendations with section_mappings
        max_logo_width: Max width for logo slot (default 100)
        max_logo_height: Max height for logo slot (default 100)

    Returns:
        Tuple of (logo_slots, media_service_slots)
    """
    if not slots:
        return [], []

    section_id_to_l0 = _build_section_id_to_l0(resolved_template_recommendations)
    header_l0_set = set(HEADER_SECTION_L0_LIST)
    footer_l0_set = set(FOOTER_SECTION_L0_LIST)

    logo_slots: List[Dict[str, Any]] = []
    media_service_slots: List[Dict[str, Any]] = []

    for slot in slots:
        slot_identity = slot.get("slot_identity") or {}
        section_id = slot_identity.get("section_id", "")
        width = slot.get("width", 0)
        height = slot.get("height", 0)

        section_l0 = _resolve_section_l0(section_id, section_id_to_l0)
        is_header_or_footer = section_l0 in header_l0_set or section_l0 in footer_l0_set
        is_small = width < max_logo_width and height < max_logo_height

        if is_header_or_footer and is_small:
            logo_slots.append(slot)
        else:
            media_service_slots.append(slot)

    return logo_slots, media_service_slots


def _build_logo_results_for_slots(
    logo_slots: List[Dict[str, Any]],
    logo_url: str,
    logo_id: str,
    logo_width: int,
    logo_height: int,
    logo_aspect_ratio: float,
) -> List[Dict[str, Any]]:
    """
    Build ImageMatchResult-style dicts for logo slots.

    Each slot gets the same logo (mapper handles dedup).
    """
    shopify_image = {
        "id": logo_id,
        "src": logo_url,
        "alt": "",
        "width": logo_width,
        "height": logo_height,
        "aspect_ratio": logo_aspect_ratio,
    }
    results = []
    for slot in logo_slots:
        slot_identity = slot.get("slot_identity") or {}
        results.append({
            "slot_identity": slot_identity,
            "shopify_image": shopify_image,
            "match_metadata": None,
        })
    return results


def fetch_and_merge_image_recommendations(
    image_slots: List[Dict[str, Any]],
    resolved_template_recommendations: List[Dict[str, Any]],
    business_id: str,
    retrieval_sources: List[str],
    logger: Any,
) -> Dict[str, Any]:
    """
    Partition slots, fetch from logo/media_service, merge results.

    Returns image_recommendations dict with "response" key containing
    results, total_slots, matched_count, unmatched_count.
    """
    logo_slots, media_service_slots = partition_image_slots_by_source(
        image_slots, resolved_template_recommendations
    )

    logo_results: List[Dict[str, Any]] = []
    if logo_slots:
        logo_output = LogoProvider().get(LogoInput(business_id=business_id))
        if logo_output.has_logo and logo_output.primary_logo:
            logo = logo_output.primary_logo
            logo_results = _build_logo_results_for_slots(
                logo_slots,
                logo_url=logo.url,
                logo_id=logo.logo_id,
                logo_width=logo.width or 100,
                logo_height=logo.height or 100,
                logo_aspect_ratio=logo.aspect_ratio or 1.0,
            )
            logger.info(
                f"Using logo for {len(logo_slots)} small header/footer slots"
            )
        else:
            logger.warning(
                f"No logo found for business_id={business_id}, "
                f"{len(logo_slots)} logo slots will be unmatched"
            )

    media_service_results: List[Dict[str, Any]] = []
    if media_service_slots:
        logger.info(
            f"Fetching {len(media_service_slots)} image recommendations from media service"
        )
        media_response = media_service.match_images_for_slots(
            business_id=business_id,
            slots=media_service_slots,
            retrieval_sources=retrieval_sources,
            max_recommendations_per_slot=10,
        )
        media_service_results = media_response.get("results", [])

    all_results = logo_results + media_service_results
    matched_count = sum(1 for r in all_results if r.get("shopify_image"))
    image_response = {
        "results": all_results,
        "total_slots": len(image_slots),
        "matched_count": matched_count,
        "unmatched_count": len(image_slots) - matched_count,
    }
    logger.info(
        f"Fetched {matched_count}/{len(image_slots)} image recommendations "
        f"(logo: {len(logo_results)}, media: {len(media_service_results)})"
    )
    return {"response": image_response}
