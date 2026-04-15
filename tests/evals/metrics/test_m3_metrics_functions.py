"""M3 validation: generic metrics and task-specific extension hooks."""

from wwai_agent_orchestration.evals.metrics import (
    EvalMetricsInput,
    EvalMetricsResult,
    MetricsService,
    extend_generic_metrics,
    generic_metrics,
    landing_page_metrics,
    template_selection_metrics,
)


def test_generic_metrics_populates_all_fields_deterministically():
    """M3-001: Run synthetic input bundle and verify all output fields populated."""
    input_bundle = EvalMetricsInput(
        eval_set_id="set_1",
        task_type="template_selection",
        runs=[
            {"status": "completed", "task_type": "template_selection", "workflow_mode": "default"},
            {"status": "failed", "task_type": "template_selection", "workflow_mode": "default"},
        ],
        human_feedback=[
            {"feedback": {"overall_pass": True}},
            {"feedback": {"overall_pass": False}},
        ],
        judge_results=[
            {"result": {"average_score": 0.9, "parse_error": None}},
            {"result": {"average_score": 0.5, "parse_error": None}},
        ],
    )
    result = generic_metrics(input_bundle)
    assert result.eval_set_id == "set_1"
    assert result.task_type == "template_selection"
    assert result.total_runs == 2
    assert result.completed_runs == 1
    assert result.human_feedback_count == 2
    assert result.ai_feedback_count == 2
    assert result.human_pass_pct == 50.0
    assert result.ai_pass_pct == 50.0
    assert result.coverage_pct == 100.0


def test_generic_metrics_safe_percentages_for_empty_inputs():
    """M3-001: Generic metrics produce safe percentages for empty inputs."""
    input_bundle = EvalMetricsInput(
        eval_set_id="set_empty",
        task_type="unknown",
        runs=[],
        human_feedback=[],
        judge_results=[],
    )
    result = generic_metrics(input_bundle)
    assert result.total_runs == 0
    assert result.completed_runs == 0
    assert result.human_feedback_count == 0
    assert result.ai_feedback_count == 0
    assert result.human_pass_pct is None
    assert result.ai_pass_pct is None
    assert result.coverage_pct == 0.0


def test_extend_generic_metrics_applies_overrides():
    """M3-002: extend_generic_metrics merges task-specific overrides."""
    input_bundle = EvalMetricsInput(
        eval_set_id="set_1",
        task_type="custom",
        runs=[{"status": "completed", "task_type": "custom", "workflow_mode": "x"}],
        human_feedback=[],
        judge_results=[],
    )
    result = extend_generic_metrics(
        input_bundle,
        overrides={"human_pass_pct": 99.0, "ai_pass_pct": 88.0},
    )
    assert result.total_runs == 1
    assert result.human_pass_pct == 99.0
    assert result.ai_pass_pct == 88.0


def test_template_selection_metrics_uses_stricter_threshold():
    """M3-002: template_selection_metrics uses 0.8 AI pass threshold."""
    input_bundle = EvalMetricsInput(
        eval_set_id="set_1",
        task_type="template_selection",
        runs=[{"status": "completed", "task_type": "template_selection", "workflow_mode": "x"}],
        human_feedback=[],
        judge_results=[
            {"result": {"average_score": 0.75, "parse_error": None}},
            {"result": {"average_score": 0.85, "parse_error": None}},
        ],
    )
    generic_result = generic_metrics(input_bundle)
    task_result = template_selection_metrics(input_bundle)
    assert generic_result.ai_pass_pct == 100.0
    assert task_result.ai_pass_pct == 50.0


def test_landing_page_metrics_dispatched_via_service():
    """M3-002: Task-specific function dispatched when registered."""
    service = MetricsService()
    service.register("landing_page", landing_page_metrics)
    input_bundle = EvalMetricsInput(
        eval_set_id="set_1",
        task_type="landing_page",
        runs=[{"status": "completed", "task_type": "landing_page", "workflow_mode": "builder"}],
        human_feedback=[],
        judge_results=[],
    )
    result = service.compute(input_bundle)
    assert result.task_type == "landing_page"
    assert result.total_runs == 1
