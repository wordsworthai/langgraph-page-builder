from wwai_agent_orchestration.evals.types import EvalCase, EvalSet, RunRecord


def test_eval_case_round_trip():
    case = EvalCase(
        case_id="case_123",
        eval_set_id="eval_set_a",
        eval_type="landing_page",
        workflow_mode="landing_page",
        set_inputs={
            "business_id": "biz_1",
            "business_index": 0,
            "website_intention": "lead_generation",
            "website_tone": "professional",
        },
        workflow_inputs={"foo": "bar"},
    )
    payload = case.model_dump()
    rebuilt = EvalCase(**payload)
    assert rebuilt.case_id == case.case_id
    assert rebuilt.workflow_inputs == {"foo": "bar"}


def test_eval_set_round_trip():
    case = EvalCase(
        case_id="case_1",
        eval_set_id="eval_set_a",
        eval_type="template_selection",
        workflow_mode="template_selection",
        set_inputs={"business_id": "biz_1"},
        workflow_inputs={},
    )
    eval_set = EvalSet(
        eval_set_id="eval_set_a",
        eval_type="template_selection",
        version="v1",
        seed=42,
        cases=[case],
    )
    dumped = eval_set.model_dump()
    rebuilt = EvalSet(**dumped)
    assert len(rebuilt.cases) == 1
    assert rebuilt.cases[0].workflow_mode == "template_selection"


def test_run_record_contains_task_details():
    record = RunRecord(
        run_id="run_1",
        thread_id="thread_1",
        case_id="case_1",
        eval_set_id="eval_set_a",
        task_type="landing_page",
        task_details={"business_id": "biz_1", "business_index": 0, "website_intention": "lead_generation"},
        status="running",
        inputs={"website_tone": "professional"},
    )
    payload = record.model_dump()
    assert payload["eval_set_id"] == "eval_set_a"
    assert payload["task_details"]["business_id"] == "biz_1"
    assert payload["status"] == "running"

