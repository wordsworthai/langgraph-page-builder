from wwai_agent_orchestration.evals.stores.local_jsonl_store import LocalJsonlEvalStore
from wwai_agent_orchestration.evals.types.run_record import RunRecord


def test_local_jsonl_store_filters_by_status(tmp_path):
    store = LocalJsonlEvalStore(root_dir=tmp_path)
    completed = RunRecord(
        run_id="run_1a",
        thread_id="run_1a",
        case_id="case_1a",
        eval_set_id="set_2",
        task_type="landing_page",
        task_details={"business_id": "biz_1", "business_index": 0},
        inputs={},
        status="completed",
    )
    failed = RunRecord(
        run_id="run_2a",
        thread_id="run_2a",
        case_id="case_2a",
        eval_set_id="set_2",
        task_type="landing_page",
        task_details={"business_id": "biz_2", "business_index": 1},
        inputs={},
        status="failed",
    )
    store.save_run_record(completed)
    store.save_run_record(failed)

    completed_records = store.get_run_records("set_2", status="completed")
    assert len(completed_records) == 1
    assert completed_records[0]["run_id"] == "run_1a"

