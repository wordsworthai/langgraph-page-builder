"""M1 validation: canonical feedback model and Mongo store."""

import pytest

from wwai_agent_orchestration.evals.human_feedback import (
    HumanFeedbackSnapshot,
    MongoFeedbackStore,
)


class _UpdateResult:
    modified_count = 1
    acknowledged = True


class _Cursor:
    def __init__(self, rows):
        self._rows = list(rows)

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


class _Db:
    def __init__(self):
        self.cols = {}

    def __getitem__(self, name):
        if name not in self.cols:
            self.cols[name] = _Collection()
        return self.cols[name]


def _make_snapshot(
    eval_set_id="evalset_1",
    case_id="case_abc123",
    run_id="run_abc123",
    thread_id="thread_xyz",
    task_type="landing_page",
    feedback=None,
):
    return HumanFeedbackSnapshot(
        eval_set_id=eval_set_id,
        case_id=case_id,
        run_id=run_id,
        thread_id=thread_id,
        task_type=task_type,
        feedback=feedback or {},
    )


# --- EVAL-FM-M1-001: Canonical feedback snapshot model ---


def test_human_feedback_snapshot_instantiates_with_required_fields():
    """M1-001: Instantiate model with all required fields."""
    snap = _make_snapshot()
    assert snap.eval_set_id == "evalset_1"
    assert snap.case_id == "case_abc123"
    assert snap.run_id == "run_abc123"
    assert snap.thread_id == "thread_xyz"
    assert snap.task_type == "landing_page"
    assert snap.feedback == {}
    assert snap.feedback_schema_version == "v1"


def test_human_feedback_snapshot_supports_category_keyed_feedback():
    """M1-001: Feedback payload is category-keyed dict."""
    snap = _make_snapshot(
        feedback={"widget_code_issue": True, "ai_copy_issue": "minor typo"}
    )
    assert snap.feedback["widget_code_issue"] is True
    assert snap.feedback["ai_copy_issue"] == "minor typo"


# --- EVAL-FM-M1-002: Mongo store ---


def test_mongo_feedback_store_save_and_get_by_run():
    """M1-002: Save snapshot and retrieve by run_id."""
    db = _Db()
    store = MongoFeedbackStore(db=db)
    snap = _make_snapshot(feedback={"overall_pass": True})
    assert store.save_feedback(snap) is True
    doc = store.get_feedback_by_run("run_abc123")
    assert doc is not None
    assert doc["run_id"] == "run_abc123"
    assert doc["eval_set_id"] == "evalset_1"
    assert doc["feedback"]["overall_pass"] is True


def test_mongo_feedback_store_upsert_overwrites_latest_snapshot():
    """M1-002: Save snapshot twice for same run; latest overwrites."""
    db = _Db()
    store = MongoFeedbackStore(db=db)
    snap1 = _make_snapshot(feedback={"overall_pass": False})
    snap2 = _make_snapshot(feedback={"overall_pass": True, "notes": "fixed"})
    store.save_feedback(snap1)
    store.save_feedback(snap2)
    doc = store.get_feedback_by_run("run_abc123")
    assert doc["feedback"]["overall_pass"] is True
    assert doc["feedback"]["notes"] == "fixed"


def test_mongo_feedback_store_get_for_eval_set():
    """M1-002: Query all feedback for an eval set; one doc per run."""
    db = _Db()
    store = MongoFeedbackStore(db=db)
    store.save_feedback(_make_snapshot(run_id="run_a", eval_set_id="set_1"))
    store.save_feedback(_make_snapshot(run_id="run_b", eval_set_id="set_1"))
    store.save_feedback(_make_snapshot(run_id="run_c", eval_set_id="set_2"))
    docs = store.get_feedback_for_eval_set("set_1")
    assert len(docs) == 2
    run_ids = {d["run_id"] for d in docs}
    assert run_ids == {"run_a", "run_b"}


def test_mongo_feedback_store_get_for_task():
    """M1-002: Query by task_type with optional eval_set_id filter."""
    db = _Db()
    store = MongoFeedbackStore(db=db)
    store.save_feedback(
        _make_snapshot(run_id="run_1", eval_set_id="set_1", task_type="landing_page")
    )
    store.save_feedback(
        _make_snapshot(run_id="run_2", eval_set_id="set_1", task_type="template_selection")
    )
    store.save_feedback(
        _make_snapshot(run_id="run_3", eval_set_id="set_2", task_type="landing_page")
    )
    docs = store.get_feedback_for_task(task_type="landing_page")
    assert len(docs) == 2
    docs_scoped = store.get_feedback_for_task(
        task_type="landing_page", eval_set_id="set_1"
    )
    assert len(docs_scoped) == 1
    assert docs_scoped[0]["run_id"] == "run_1"
