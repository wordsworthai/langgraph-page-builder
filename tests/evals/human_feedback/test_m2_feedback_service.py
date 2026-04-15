"""M2 validation: FeedbackService key validation and save."""

import pytest

from wwai_agent_orchestration.evals.human_feedback import (
    FeedbackService,
    MongoFeedbackStore,
)

from tests.evals.human_feedback.test_m1_feedback import _Db, _make_snapshot


def test_feedback_service_saves_valid_snapshot():
    """M2-001: Save valid snapshot successfully."""
    db = _Db()
    store = MongoFeedbackStore(db=db)
    service = FeedbackService(store=store)
    # Use taxonomy-valid keys for landing_page; overall_pass is computed on the fly by metrics
    snap = _make_snapshot(feedback={"overall_readiness": "pass", "widget_code_issue": False})
    assert service.save_snapshot(snap) is True
    doc = store.get_feedback_by_run("run_abc123")
    assert doc is not None
    assert doc["feedback"]["overall_readiness"] == "pass"
    assert doc["feedback"]["widget_code_issue"] is False


def test_feedback_service_saves_with_valid_taxonomy_keys():
    """M2-001: Save with valid taxonomy keys passes."""
    db = _Db()
    store = MongoFeedbackStore(db=db)
    service = FeedbackService(store=store)
    snap = _make_snapshot(
        feedback={"overall_readiness": "pass", "comments": "ok"}
    )
    assert service.save_snapshot(snap) is True


def test_feedback_service_rejects_disallowed_keys():
    """M2-001: Attempt save with disallowed feedback keys and verify exception."""
    db = _Db()
    store = MongoFeedbackStore(db=db)
    service = FeedbackService(store=store)
    snap = _make_snapshot(
        feedback={"widget_code_issue": False, "forbidden_key": "bad"}
    )
    with pytest.raises(ValueError, match="Invalid feedback keys"):
        service.save_snapshot(snap)
