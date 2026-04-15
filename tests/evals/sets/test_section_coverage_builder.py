from wwai_agent_orchestration.constants.section_types import (
    FOOTER_SECTION_L0_LIST,
    HEADER_SECTION_L0_LIST,
)
from wwai_agent_orchestration.evals.sets.landing_page_builder.section_coverage_builder import (
    build_section_coverage_eval_set,
)


def _sample_sections():
    return [
        {"section_id": "h_1", "section_l0": HEADER_SECTION_L0_LIST[0]},
        {"section_id": "f_1", "section_l0": FOOTER_SECTION_L0_LIST[0]},
        {"section_id": "m_1", "section_l0": "Hero"},
        {"section_id": "m_2", "section_l0": "About"},
        {"section_id": "m_3", "section_l0": "Services"},
        {"section_id": "m_4", "section_l0": "Testimonials"},
    ]


def test_section_coverage_builder_ensures_middle_coverage_and_order():
    eval_set = build_section_coverage_eval_set(
        eval_set_id="set_sc_v1",
        version="v1",
        seed=1,
        business_ids=["biz_a", "biz_b"],
        middle_section_count=2,
        sections=_sample_sections(),
    )

    observed_middle_sections = set()
    for case in eval_set.cases:
        psi = case.workflow_inputs["preset_sections_input"]
        section_ids = psi["section_ids"]
        assert section_ids[0] == "h_1"
        assert section_ids[-1] == "f_1"
        for section_id in section_ids[1:-1]:
            observed_middle_sections.add(section_id)
        assert "website_context" in psi
        assert "brand_context" in psi
        assert psi["website_context"]["website_intention"] is not None
        assert psi["brand_context"]["font_family"] is not None

    assert observed_middle_sections == {"m_1", "m_2", "m_3", "m_4"}


def test_section_coverage_builder_is_deterministic():
    kwargs = {
        "eval_set_id": "set_sc_v1",
        "version": "v1",
        "seed": 13,
        "business_ids": ["biz_a", "biz_b", "biz_c"],
        "middle_section_count": 2,
        "sections": _sample_sections(),
    }
    first = build_section_coverage_eval_set(**kwargs)
    second = build_section_coverage_eval_set(**kwargs)
    assert [case.case_id for case in first.cases] == [case.case_id for case in second.cases]


def _sample_sections_with_multiple_headers_footers():
    return [
        {"section_id": "h_1", "section_l0": HEADER_SECTION_L0_LIST[0]},
        {"section_id": "h_2", "section_l0": HEADER_SECTION_L0_LIST[0]},
        {"section_id": "f_1", "section_l0": FOOTER_SECTION_L0_LIST[0]},
        {"section_id": "f_2", "section_l0": FOOTER_SECTION_L0_LIST[0]},
        {"section_id": "m_1", "section_l0": "Hero"},
        {"section_id": "m_2", "section_l0": "About"},
    ]


def test_section_coverage_builder_rotates_headers_and_footers():
    """With multiple headers and footers, every one is used at least once."""
    eval_set = build_section_coverage_eval_set(
        eval_set_id="set_sc_v1",
        version="v1",
        seed=1,
        business_ids=["biz_a", "biz_b"],
        middle_section_count=2,
        sections=_sample_sections_with_multiple_headers_footers(),
    )

    observed_headers = set()
    observed_footers = set()
    observed_middle = set()
    for case in eval_set.cases:
        psi = case.workflow_inputs["preset_sections_input"]
        section_ids = psi["section_ids"]
        observed_headers.add(section_ids[0])
        observed_footers.add(section_ids[-1])
        for section_id in section_ids[1:-1]:
            observed_middle.add(section_id)

    assert observed_headers == {"h_1", "h_2"}
    assert observed_footers == {"f_1", "f_2"}
    assert observed_middle == {"m_1", "m_2"}

