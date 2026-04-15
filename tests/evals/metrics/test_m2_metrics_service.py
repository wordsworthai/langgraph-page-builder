"""M2 validation: MetricsService registry and dispatch."""

from wwai_agent_orchestration.evals.metrics import (
    EvalMetricsInput,
    EvalMetricsResult,
    MetricsService,
)
def test_metrics_service_fallback_to_generic_for_unknown_task():
    """M2-002: Verify fallback to generic function for unknown task types."""
    service = MetricsService()
    input_bundle = EvalMetricsInput(
        eval_set_id="set_1",
        task_type="unknown_task_type",
        runs=[{"status": "completed", "task_type": "x", "workflow_mode": "y"}],
        human_feedback=[],
        judge_results=[],
    )
    result = service.compute(input_bundle)
    assert result.eval_set_id == "set_1"
    assert result.task_type == "unknown_task_type"
    assert result.total_runs == 1
    assert result.completed_runs == 1
    assert result.human_feedback_count == 0
    assert result.ai_feedback_count == 0


def test_metrics_service_dispatches_registered_function():
    """M2-002: Register a custom task metric function and verify dispatch."""
    service = MetricsService()

    def custom_landing_metrics(input_bundle: EvalMetricsInput) -> EvalMetricsResult:
        return EvalMetricsResult(
            eval_set_id=input_bundle.eval_set_id,
            task_type=input_bundle.task_type,
            total_runs=999,
            completed_runs=888,
            human_feedback_count=0,
            ai_feedback_count=0,
            human_pass_pct=75.0,
            ai_pass_pct=80.0,
            coverage_pct=50.0,
        )

    service.register("landing_page", custom_landing_metrics)
    input_bundle = EvalMetricsInput(
        eval_set_id="set_1",
        task_type="landing_page",
        runs=[],
        human_feedback=[],
        judge_results=[],
    )
    result = service.compute(input_bundle)
    assert result.total_runs == 999
    assert result.completed_runs == 888
    assert result.human_pass_pct == 75.0
    assert result.ai_pass_pct == 80.0


def test_metrics_service_unregistered_uses_generic():
    """M2-002: Unregistered task type uses generic_metrics."""
    service = MetricsService()
    input_bundle = EvalMetricsInput(
        eval_set_id="set_1",
        task_type="template_selection",
        runs=[
            {"status": "completed", "task_type": "template_selection", "workflow_mode": "default"},
            {"status": "failed", "task_type": "template_selection", "workflow_mode": "default"},
        ],
        human_feedback=[{"feedback": {"overall_pass": True}}],
        judge_results=[{"result": {"average_score": 0.9, "parse_error": None}}],
    )
    result = service.compute(input_bundle)
    assert result.total_runs == 2
    assert result.completed_runs == 1
    assert result.human_feedback_count == 1
    assert result.ai_feedback_count == 1
    assert result.human_pass_pct == 100.0
    assert result.ai_pass_pct == 100.0
