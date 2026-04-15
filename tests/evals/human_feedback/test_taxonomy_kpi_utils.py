"""Tests for taxonomy_kpi_utils: answered-only denominator and unanswered rate."""

from wwai_agent_orchestration.evals.human_feedback.metrics.kpi_utils import (
    _bool_issue_rate,
    _bool_unanswered_rate,
    compute_task_human_kpis_from_taxonomy,
)
from wwai_agent_orchestration.evals.human_feedback.taxonomy.contracts import (
    TaskFeedbackTaxonomy,
    TaxonomyCategory,
)


def _doc(feedback: dict) -> dict:
    return {"feedback": feedback}


def test_bool_issue_rate_when_all_answered():
    """issue_rate uses answered-only denominator; 2/5 True = 40%."""
    docs = [
        _doc({"key": True}),
        _doc({"key": True}),
        _doc({"key": False}),
        _doc({"key": False}),
        _doc({"key": False}),
    ]
    issue = _bool_issue_rate(docs, "key")
    assert issue == 40.0  # 2/5 answered


def test_bool_rates_exclude_unanswered_from_denominator():
    """Unanswered docs are excluded; issue rate uses answered only."""
    docs = [
        _doc({"key": True}),
        _doc({"key": False}),
        _doc({"key": None}),  # unanswered
        _doc({}),  # missing
    ]
    # 1 True, 1 False among answered; 2 unanswered
    issue = _bool_issue_rate(docs, "key")
    unanswered = _bool_unanswered_rate(docs, "key")
    assert issue == 50.0  # 1/2 answered
    assert unanswered == 50.0  # 2/4 total


def test_bool_all_unanswered_returns_zero_for_issue():
    """All unanswered: issue_rate=0, unanswered_rate=100."""
    docs = [_doc({"key": None}), _doc({}), _doc({"key": "invalid"})]
    assert _bool_issue_rate(docs, "key") == 0.0
    assert _bool_unanswered_rate(docs, "key") == 100.0


def test_bool_empty_feedback_docs():
    """Empty list returns 0 for all rates."""
    assert _bool_issue_rate([], "key") == 0.0
    assert _bool_unanswered_rate([], "key") == 0.0


def test_bool_unanswered_rate_mixed():
    """unanswered_rate = (unanswered / total) * 100."""
    docs = [
        _doc({"key": True}),
        _doc({"key": False}),
        _doc({"key": None}),
        _doc({"key": None}),
        _doc({"key": None}),
    ]
    assert _bool_unanswered_rate(docs, "key") == 60.0  # 3/5


def test_compute_task_human_kpis_from_taxonomy_only_booleans():
    """Only boolean categories get _pct and _unanswered_pct metrics."""
    taxonomy = TaskFeedbackTaxonomy(
        task_type="test",
        categories=[
            TaxonomyCategory(key="flag_a", label="Flag A", value_type="boolean", order=1),
            TaxonomyCategory(key="flag_b", label="Flag B", value_type="boolean", order=2),
            TaxonomyCategory(key="notes", label="Notes", value_type="text", order=3),
        ],
    )
    docs = [
        _doc({"flag_a": True, "flag_b": False}),
        _doc({"flag_a": False, "flag_b": True}),
    ]
    result = compute_task_human_kpis_from_taxonomy(taxonomy, docs)
    assert "flag_a_pct" in result
    assert "flag_a_unanswered_pct" in result
    assert "flag_b_pct" in result
    assert "flag_b_unanswered_pct" in result
    assert "notes_pct" not in result
    assert "notes_unanswered_pct" not in result
    assert result["flag_a_pct"] == 50.0
    assert result["flag_a_unanswered_pct"] == 0.0
    assert result["flag_b_pct"] == 50.0
    assert result["flag_b_unanswered_pct"] == 0.0


def test_compute_task_human_kpis_from_taxonomy_number_avg():
    """Number categories get _avg and _unanswered_pct."""
    taxonomy = TaskFeedbackTaxonomy(
        task_type="test",
        categories=[
            TaxonomyCategory(key="score", label="Score", value_type="number", order=1),
        ],
    )
    docs = [
        _doc({"score": 10}),
        _doc({"score": 20}),
        _doc({"score": 30}),
        _doc({"score": None}),
        _doc({}),
    ]
    result = compute_task_human_kpis_from_taxonomy(taxonomy, docs)
    assert result["score_avg"] == 20.0  # (10+20+30)/3
    assert result["score_unanswered_pct"] == 40.0  # 2/5


def test_compute_task_human_kpis_from_taxonomy_enum_distribution():
    """Enum categories get _distribution and _unanswered_pct."""
    taxonomy = TaskFeedbackTaxonomy(
        task_type="test",
        categories=[
            TaxonomyCategory(
                key="readiness",
                label="Readiness",
                value_type="enum",
                options=["fail", "needs_work", "pass"],
                order=1,
            ),
        ],
    )
    docs = [
        _doc({"readiness": "pass"}),
        _doc({"readiness": "pass"}),
        _doc({"readiness": "fail"}),
        _doc({"readiness": None}),
        _doc({}),
    ]
    result = compute_task_human_kpis_from_taxonomy(taxonomy, docs)
    assert "pass: 2" in result["readiness_distribution"]
    assert "fail: 1" in result["readiness_distribution"]
    assert result["readiness_unanswered_pct"] == 40.0  # 2/5


def test_compute_task_human_kpis_from_taxonomy_skips_inactive():
    """Inactive categories are skipped."""
    taxonomy = TaskFeedbackTaxonomy(
        task_type="test",
        categories=[
            TaxonomyCategory(
                key="active_flag",
                label="Active",
                value_type="boolean",
                order=1,
                active=True,
            ),
            TaxonomyCategory(
                key="inactive_flag",
                label="Inactive",
                value_type="boolean",
                order=2,
                active=False,
            ),
        ],
    )
    docs = [_doc({"active_flag": True, "inactive_flag": False})]
    result = compute_task_human_kpis_from_taxonomy(taxonomy, docs)
    assert "active_flag_pct" in result
    assert "inactive_flag_pct" not in result
