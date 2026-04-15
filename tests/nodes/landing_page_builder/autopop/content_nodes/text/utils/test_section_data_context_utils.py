"""Tests for section_data_context_utils."""
from wwai_agent_orchestration.constants.section_types import (
    HEADER_SECTION_L0_LIST,
    FOOTER_SECTION_L0_LIST,
)
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.content_nodes.text.utils.section_data_context_utils import (
    get_section_id_to_data_context_mapping,
)


def test_header_footer_sections_get_nav_context_with_bare_section_id():
    """Bare section_id (e.g. from section_mappings) maps to data_context_nav for header/footer."""
    resolved = [
        {
            "section_mappings": [
                {"section_id": "nav_1", "section_l0": HEADER_SECTION_L0_LIST[0]},
                {"section_id": "hero_1", "section_l0": "Hero"},
                {"section_id": "foot_1", "section_l0": FOOTER_SECTION_L0_LIST[0]},
            ]
        }
    ]
    section_ids = ["nav_1", "hero_1", "foot_1"]
    data_context_full = "full context with reviews"
    data_context_nav = "nav context without reviews"

    result = get_section_id_to_data_context_mapping(
        section_ids=section_ids,
        resolved_template_recommendations=resolved,
        data_context_full=data_context_full,
        data_context_nav=data_context_nav,
    )

    assert result["nav_1"] == data_context_nav
    assert result["hero_1"] == data_context_full
    assert result["foot_1"] == data_context_nav


def test_header_footer_sections_get_nav_context_with_indexed_section_id():
    """section_id_0, section_id_1 format (from agents_context.sections) maps to data_context_nav for header/footer."""
    resolved = [
        {
            "section_mappings": [
                {"section_id": "69666d4adb7c2f2d24b582aa_ff0c11e300b6b14d", "section_l0": HEADER_SECTION_L0_LIST[0]},
                {"section_id": "hero_section_id", "section_l0": "Hero"},
            ]
        }
    ]
    # Simulate agents_context.sections.keys() which may use section_id_index format
    section_ids = ["69666d4adb7c2f2d24b582aa_ff0c11e300b6b14d_0", "hero_section_id_1"]
    data_context_full = "full context with reviews"
    data_context_nav = "nav context without reviews"

    result = get_section_id_to_data_context_mapping(
        section_ids=section_ids,
        resolved_template_recommendations=resolved,
        data_context_full=data_context_full,
        data_context_nav=data_context_nav,
    )

    assert result["69666d4adb7c2f2d24b582aa_ff0c11e300b6b14d_0"] == data_context_nav
    assert result["hero_section_id_1"] == data_context_full


def test_both_bare_and_indexed_formats_map_correctly():
    """Both section_id and section_id_0 should map to same context for Navigation Bar."""
    resolved = [
        {
            "section_mappings": [
                {"section_id": "nav_bar_id", "section_l0": "Navigation Bar"},
            ]
        }
    ]
    section_ids = ["nav_bar_id", "nav_bar_id_0"]
    data_context_full = "full"
    data_context_nav = "nav"

    result = get_section_id_to_data_context_mapping(
        section_ids=section_ids,
        resolved_template_recommendations=resolved,
        data_context_full=data_context_full,
        data_context_nav=data_context_nav,
    )

    assert result["nav_bar_id"] == data_context_nav
    assert result["nav_bar_id_0"] == data_context_nav
