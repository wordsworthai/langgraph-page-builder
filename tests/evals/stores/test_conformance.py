from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict

from wwai_agent_orchestration.evals.stores.interfaces import EvalStore
from wwai_agent_orchestration.evals.stores.local_jsonl_store import LocalJsonlEvalStore
from wwai_agent_orchestration.evals.stores.mongo_store import MongoEvalStore
from wwai_agent_orchestration.evals.types.eval_case import EvalCase
from wwai_agent_orchestration.evals.types.eval_set import EvalSet
from wwai_agent_orchestration.evals.types.run_record import RunRecord


class _UpdateResult:
    def __init__(self, acknowledged: bool = True):
        self.acknowledged = acknowledged
        self.modified_count = 1


class _FakeCursor:
    def __init__(self, data):
        self._data = list(data)

    def sort(self, fields):
        if isinstance(fields, list):
            for field, direction in reversed(fields):
                reverse = direction < 0
                self._data.sort(key=lambda row: row.get(field), reverse=reverse)
        else:
            field, direction = fields, 1
            self._data.sort(key=lambda row: row.get(field), reverse=direction < 0)
        return self

    def __iter__(self):
        return iter(self._data)


class _FakeCollection:
    def __init__(self):
        self._rows: Dict[str, dict] = {}

    def create_index(self, *_args, **_kwargs):
        return None

    def update_one(self, query, update, upsert=False):
        key = query.get("_id")
        existing = self._rows.get(key, {}) if key else {}
        row = {}
        row.update(existing)
        row.update(update.get("$setOnInsert", {}) if not existing else {})
        row.update(update.get("$set", {}))
        if key is None and upsert:
            key = row.get("_id")
        if key is not None:
            self._rows[key] = row
        return _UpdateResult()

    def find_one(self, query):
        for row in self._rows.values():
            if all(row.get(k) == v for k, v in query.items()):
                return row
        return None

    def find(self, query):
        rows = []
        for row in self._rows.values():
            if all(row.get(k) == v for k, v in query.items()):
                rows.append(row)
        return _FakeCursor(rows)

    def count_documents(self, query):
        return len(list(self.find(query)))


class _FakeDb:
    def __init__(self):
        self._collections: Dict[str, _FakeCollection] = {}

    def __getitem__(self, name: str):
        if name not in self._collections:
            self._collections[name] = _FakeCollection()
        return self._collections[name]


def _sample_eval_set() -> EvalSet:
    case = EvalCase(
        case_id="case_abc123",
        eval_set_id="set_1",
        eval_type="landing_page",
        workflow_mode="landing_page",
        set_inputs={
            "business_id": "biz_1",
            "business_index": 0,
            "website_intention": "lead_generation",
        },
        workflow_inputs={"website_intention": "lead_generation"},
    )
    return EvalSet(
        eval_set_id="set_1",
        eval_type="landing_page",
        version="v1",
        seed=5,
        cases=[case],
    )


def _sample_run_record() -> RunRecord:
    return RunRecord(
        run_id="run_abc123",
        thread_id="run_abc123",
        case_id="case_abc123",
        eval_set_id="set_1",
        task_type="landing_page",
        task_details={"business_id": "biz_1", "business_index": 0, "website_intention": "lead_generation"},
        inputs={"website_intention": "lead_generation"},
        status="completed",
    )


def _run_conformance(store: EvalStore):
    assert isinstance(store, EvalStore)

    eval_set = _sample_eval_set()
    run_record = _sample_run_record()

    assert store.save_eval_set(eval_set)
    assert store.save_run_record(run_record)
    assert store.save_output(
        eval_set_id="set_1",
        case_id="case_abc123",
        run_id="run_abc123",
        workflow_mode="landing_page",
        output={"generation_version_id": "gen_1"},
    )
    assert store.save_judge_result(
        eval_set_id="set_1",
        run_id="run_abc123",
        task_name="templateEval",
        result={"average_score": 8.5},
    )

    assert store.get_eval_set("set_1") is not None
    runs = store.get_run_records("set_1")
    assert len(runs) == 1
    outputs = store.get_outputs("set_1")
    assert len(outputs) == 1
    summary = store.get_eval_set_summary("set_1")
    assert summary["total"] == 1
    assert summary["completed"] == 1


def test_local_jsonl_store_conformance():
    with TemporaryDirectory() as tmp_dir:
        store = LocalJsonlEvalStore(root_dir=Path(tmp_dir))
        _run_conformance(store)


def test_mongo_store_conformance_with_fake_db():
    store = MongoEvalStore(db=_FakeDb())
    _run_conformance(store)

