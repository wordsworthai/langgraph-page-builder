from wwai_agent_orchestration.evals.stores.mongo_store import MongoEvalStore
from wwai_agent_orchestration.evals.types.run_record import RunRecord


class _UpdateResult:
    modified_count = 1
    acknowledged = True


class _Cursor:
    def __init__(self, rows):
        self._rows = list(rows)

    def sort(self, _fields):
        return self

    def __iter__(self):
        return iter(self._rows)


class _Collection:
    def __init__(self):
        self.rows = {}

    def create_index(self, *_args, **_kwargs):
        return None

    def update_one(self, query, update, upsert=False):
        key = query.get("_id")
        if key is None and upsert:
            key = update.get("$set", {}).get("_id")
        row = {}
        row.update(self.rows.get(key, {}))
        row.update(update.get("$setOnInsert", {}) if key not in self.rows else {})
        row.update(update.get("$set", {}))
        self.rows[key] = row
        return _UpdateResult()

    def find(self, query):
        rows = []
        for row in self.rows.values():
            if all(row.get(k) == v for k, v in query.items()):
                rows.append(row)
        return _Cursor(rows)

    def find_one(self, query):
        for row in self.rows.values():
            if all(row.get(k) == v for k, v in query.items()):
                return row
        return None

    def count_documents(self, query):
        return len(list(self.find(query)))


class _Db:
    def __init__(self):
        self.cols = {}

    def __getitem__(self, name):
        if name not in self.cols:
            self.cols[name] = _Collection()
        return self.cols[name]


def test_mongo_store_saves_and_summarizes_runs():
    store = MongoEvalStore(db=_Db())
    run_record = RunRecord(
        run_id="run_abc123",
        thread_id="run_abc123",
        case_id="case_abc123",
        eval_set_id="set_3",
        task_type="landing_page",
        task_details={"business_id": "biz_1", "business_index": 0},
        inputs={},
        status="completed",
    )
    store.save_run_record(run_record)
    summary = store.get_eval_set_summary("set_3")
    assert summary["total"] == 1
    assert summary["completed"] == 1

