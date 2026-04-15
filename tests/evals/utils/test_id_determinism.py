from wwai_agent_orchestration.evals.utils.hashing import (
    build_case_id,
    build_run_id,
    build_thread_id,
)


def test_case_id_is_stable_for_same_payload():
    kwargs = {
        "eval_set_version": "v1",
        "eval_type": "landing_page",
        "workflow_mode": "landing_page",
        "set_inputs": {"business_id": "biz_1"},
        "workflow_inputs": {"website_intention": "lead_generation", "palette_id": "friendly-1"},
    }
    first = build_case_id(**kwargs)
    second = build_case_id(**kwargs)
    assert first == second


def test_case_id_changes_when_input_changes():
    base = build_case_id(
        eval_set_version="v1",
        eval_type="landing_page",
        workflow_mode="landing_page",
        set_inputs={"business_id": "biz_1"},
        workflow_inputs={"website_intention": "lead_generation"},
    )
    changed = build_case_id(
        eval_set_version="v1",
        eval_type="landing_page",
        workflow_mode="landing_page",
        set_inputs={"business_id": "biz_1"},
        workflow_inputs={"website_intention": "local_discovery"},
    )
    assert base != changed


def test_run_id_and_thread_id_policy():
    run_id = build_run_id()
    assert run_id.startswith("run_")
    assert build_thread_id(run_id) == run_id

