"""Validation tests for isolated human_feedback package."""

import pytest

from wwai_agent_orchestration.evals.human_feedback import (
    FeedbackService,
    HumanFeedbackSnapshot,
    MongoFeedbackStore,
    derive_overall_pass,
    get_allowed_keys,
    get_taxonomy,
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


def _make_snapshot(task_type: str, feedback: dict, schema_version: str = "v1"):
    return HumanFeedbackSnapshot(
        eval_set_id="evalset_1",
        case_id="case_abc123",
        run_id="run_abc123",
        thread_id="thread_xyz",
        task_type=task_type,
        feedback=feedback,
        feedback_schema_version=schema_version,
    )


def test_registry_exposes_taxonomy_for_all_tasks():
    for task_type in ["template_selection", "landing_page", "section_coverage", "color_palette"]:
        taxonomy = get_taxonomy(task_type=task_type)
        assert taxonomy.task_type == task_type
        assert len(get_allowed_keys(task_type)) > 0


def test_service_validates_keys_and_types():
    service = FeedbackService(store=MongoFeedbackStore(db=_Db()))
    snapshot = _make_snapshot(
        task_type="template_selection",
        feedback={"template_structure_issue": True, "comments": "looks okay"},
    )
    assert service.save_snapshot(snapshot) is True


def test_service_rejects_invalid_key():
    service = FeedbackService(store=MongoFeedbackStore(db=_Db()))
    snapshot = _make_snapshot(
        task_type="landing_page",
        feedback={"unknown_key": True},
    )
    with pytest.raises(ValueError, match="Invalid feedback keys"):
        service.save_snapshot(snapshot)


def test_service_rejects_invalid_value_type():
    service = FeedbackService(store=MongoFeedbackStore(db=_Db()))
    snapshot = _make_snapshot(
        task_type="template_selection",
        feedback={"template_structure_issue": "yes"},
    )
    with pytest.raises(ValueError, match="expects boolean value"):
        service.save_snapshot(snapshot)


def test_section_coverage_requires_required_field():
    service = FeedbackService(store=MongoFeedbackStore(db=_Db()))
    snapshot = _make_snapshot(
        task_type="section_coverage",
        feedback={},
    )
    with pytest.raises(ValueError, match="Missing required feedback keys"):
        service.save_snapshot(snapshot)


def test_derive_overall_pass_policies():
    assert not derive_overall_pass(
        "template_selection",
        {"template_structure_issue": True},
    )
    assert derive_overall_pass(
        "template_selection",
        {
            "template_structure_issue": False,
            "section_selection_issue": False,
            "section_ordering_issue": False,
            "section_count_issue": False,
            "intent_fit_issue": False,
        },
    )
    assert derive_overall_pass(
        "landing_page",
        {"overall_readiness": "pass"},
    )
    assert derive_overall_pass(
        "section_coverage",
        {"has_undesired_section": False},
    )
    assert derive_overall_pass("color_palette", {"has_breaking_section": False})
    assert not derive_overall_pass("color_palette", {"has_breaking_section": True})
