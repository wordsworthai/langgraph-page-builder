"""Deterministic tests for task policies in metrics."""

from wwai_agent_orchestration.evals.metrics import EvalMetricsInput, MetricsService

from tests.evals.metrics.fixtures import (
    landing_page_bundle,
    section_coverage_bundle,
    template_selection_bundle,
)


def test_template_selection_policy_metrics():
    service = MetricsService()
    result = service.compute(EvalMetricsInput(**template_selection_bundle()))
    assert result.task_type == "template_selection"
    assert result.total_runs == 2
    assert result.completed_runs == 1
    assert result.human_pass_pct == 50.0
    assert result.ai_pass_pct == 50.0
    assert result.agreement_pct == 100.0
    assert "intent_fit_issue_pct" in result.task_kpis
    assert "template_structure_issue_unanswered_pct" in result.task_kpis
    # All fixture feedback has explicit True/False; unanswered should be 0
    assert result.task_kpis["template_structure_issue_unanswered_pct"] == 0.0


def test_landing_page_policy_metrics():
    service = MetricsService()
    result = service.compute(EvalMetricsInput(**landing_page_bundle()))
    assert result.task_type == "landing_page"
    assert result.total_runs == 2
    assert result.completed_runs == 2
    assert result.human_pass_pct == 50.0
    assert result.ai_pass_pct == 50.0
    assert result.agreement_pct == 100.0
    assert "widget_code_issue_pct" in result.task_kpis
    assert "widget_code_issue_unanswered_pct" in result.task_kpis
    # Fixture has widget_code_issue for both docs; unanswered = 0
    assert result.task_kpis["widget_code_issue_unanswered_pct"] == 0.0


def test_section_coverage_policy_metrics():
    service = MetricsService()
    result = service.compute(EvalMetricsInput(**section_coverage_bundle()))
    assert result.task_type == "section_coverage"
    assert result.total_runs == 2
    assert "has_breaking_section_pct" in result.task_kpis
    assert "has_breaking_section_unanswered_pct" in result.task_kpis
    assert result.task_kpis["has_breaking_section_unanswered_pct"] == 0.0

