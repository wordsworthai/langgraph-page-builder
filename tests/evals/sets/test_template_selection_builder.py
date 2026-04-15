from wwai_agent_orchestration.evals.sets.landing_page_builder.template_selection_builder import (
    build_template_selection_eval_set,
)


def test_template_selection_builder_cardinality_and_uniqueness():
    businesses = [f"biz_{i}" for i in range(36)]
    eval_set = build_template_selection_eval_set(
        eval_set_id="set_template_v1",
        version="v1",
        seed=11,
        business_ids=businesses,
    )
    assert len(eval_set.cases) == 144
    case_ids = {case.case_id for case in eval_set.cases}
    assert len(case_ids) == 144
    for case in eval_set.cases:
        tsi = case.workflow_inputs["template_selection_input"]
        assert "business_id" in tsi
        assert "website_context" in tsi
        assert "brand_context" not in tsi
        assert tsi["website_context"]["website_intention"]


def test_template_selection_builder_is_deterministic():
    businesses = [f"biz_{i}" for i in range(5)]
    first = build_template_selection_eval_set(
        eval_set_id="set_template_v1",
        version="v1",
        seed=3,
        business_ids=businesses,
    )
    second = build_template_selection_eval_set(
        eval_set_id="set_template_v1",
        version="v1",
        seed=3,
        business_ids=businesses,
    )
    assert [case.case_id for case in first.cases] == [case.case_id for case in second.cases]

