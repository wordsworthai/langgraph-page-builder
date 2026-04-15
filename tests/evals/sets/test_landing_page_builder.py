from wwai_agent_orchestration.evals.sets.landing_page_builder.landing_page_builder import (
    build_landing_page_eval_set,
)


def test_landing_page_builder_one_case_per_business():
    businesses = [f"biz_{i}" for i in range(10)]
    eval_set = build_landing_page_eval_set(
        eval_set_id="set_lp_v1",
        version="v1",
        seed=7,
        business_ids=businesses,
    )
    assert len(eval_set.cases) == len(businesses)
    assert all(case.workflow_mode == "landing_page" for case in eval_set.cases)
    for case in eval_set.cases:
        lpi = case.workflow_inputs["landing_page_input"]
        assert "business_id" in lpi
        assert "website_context" in lpi
        assert "brand_context" in lpi
        assert lpi["website_context"]["website_intention"]
        assert "palette" in lpi["brand_context"] or "font_family" in lpi["brand_context"]


def test_landing_page_builder_is_deterministic():
    businesses = [f"biz_{i}" for i in range(8)]
    first = build_landing_page_eval_set(
        eval_set_id="set_lp_v1",
        version="v1",
        seed=9,
        business_ids=businesses,
    )
    second = build_landing_page_eval_set(
        eval_set_id="set_lp_v1",
        version="v1",
        seed=9,
        business_ids=businesses,
    )
    assert [case.case_id for case in first.cases] == [case.case_id for case in second.cases]

