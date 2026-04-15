"""Tests for section_media_source_utils."""
from wwai_agent_orchestration.constants.section_types import (
    HEADER_SECTION_L0_LIST,
    FOOTER_SECTION_L0_LIST,
)
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.content_nodes.media.utils.section_media_source_utils import (
    partition_image_slots_by_source,
)


def _slot(section_id: str, width: int, height: int, element_id: str = "el1", block_type: str = "image", block_index: int = 0):
    return {
        "width": width,
        "height": height,
        "slot_identity": {
            "section_id": section_id,
            "element_id": element_id,
            "block_type": block_type,
            "block_index": block_index,
        },
    }


def test_header_small_slot_goes_to_logo():
    """Header section + slot < 100x100 → logo_slots."""
    resolved = [
        {
            "section_mappings": [
                {"section_id": "nav_1", "section_l0": HEADER_SECTION_L0_LIST[0]},
            ]
        }
    ]
    slots = [_slot("nav_1", 80, 80)]
    logo_slots, media_slots = partition_image_slots_by_source(slots, resolved)
    assert len(logo_slots) == 1
    assert len(media_slots) == 0


def test_footer_small_slot_goes_to_logo():
    """Footer section + slot < 100x100 → logo_slots."""
    resolved = [
        {
            "section_mappings": [
                {"section_id": "foot_1", "section_l0": FOOTER_SECTION_L0_LIST[0]},
            ]
        }
    ]
    slots = [_slot("foot_1", 50, 50)]
    logo_slots, media_slots = partition_image_slots_by_source(slots, resolved)
    assert len(logo_slots) == 1
    assert len(media_slots) == 0


def test_header_large_slot_goes_to_media_service():
    """Header section + slot >= 100x100 → media_service_slots."""
    resolved = [
        {
            "section_mappings": [
                {"section_id": "nav_1", "section_l0": HEADER_SECTION_L0_LIST[0]},
            ]
        }
    ]
    slots = [_slot("nav_1", 200, 100)]
    logo_slots, media_slots = partition_image_slots_by_source(slots, resolved)
    assert len(logo_slots) == 0
    assert len(media_slots) == 1


def test_body_small_slot_goes_to_media_service():
    """Body section (Hero) + slot < 100x100 → media_service_slots."""
    resolved = [
        {
            "section_mappings": [
                {"section_id": "hero_1", "section_l0": "Hero"},
            ]
        }
    ]
    slots = [_slot("hero_1", 80, 80)]
    logo_slots, media_slots = partition_image_slots_by_source(slots, resolved)
    assert len(logo_slots) == 0
    assert len(media_slots) == 1


def test_section_id_with_suffix_resolves_to_base():
    """section_id with suffix (base_hash) resolves via base lookup → logo for header."""
    base_id = "69666d4adb7c2f2d24b582aa"
    resolved = [
        {
            "section_mappings": [
                {"section_id": base_id, "section_l0": "Navigation Bar"},
            ]
        }
    ]
    # agents_context.sections key format
    section_id_with_suffix = f"{base_id}_b5ff736647871dfd"
    slots = [_slot(section_id_with_suffix, 80, 80)]
    logo_slots, media_slots = partition_image_slots_by_source(slots, resolved)
    assert len(logo_slots) == 1
    assert len(media_slots) == 0


def test_empty_resolved_all_go_to_media_service():
    """Empty resolved_template_recommendations → all slots go to media_service."""
    slots = [_slot("nav_1", 80, 80)]
    logo_slots, media_slots = partition_image_slots_by_source(slots, [])
    assert len(logo_slots) == 0
    assert len(media_slots) == 1


def test_custom_threshold():
    """Custom max_logo_width/height changes partition."""
    resolved = [
        {
            "section_mappings": [
                {"section_id": "nav_1", "section_l0": "Navigation Bar"},
            ]
        }
    ]
    # 150x150: logo with default 100, media with 200
    slots = [_slot("nav_1", 150, 150)]
    logo_slots, media_slots = partition_image_slots_by_source(
        slots, resolved, max_logo_width=200, max_logo_height=200
    )
    assert len(logo_slots) == 1
    assert len(media_slots) == 0
