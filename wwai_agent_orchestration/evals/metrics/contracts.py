"""Input/output contracts for eval metrics computation."""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class EvalMetricsInput(BaseModel):
    """Aggregated source artifacts needed to compute metrics for one eval set."""

    eval_set_id: str
    task_type: str
    runs: List[Dict[str, Any]] = Field(default_factory=list)
    human_feedback: List[Dict[str, Any]] = Field(default_factory=list)
    judge_results: List[Dict[str, Any]] = Field(default_factory=list)


class EvalMetricsResult(BaseModel):
    """Metrics output envelope returned by computation functions."""

    eval_set_id: str
    task_type: str

    # Run counts
    total_runs: int = 0  # Total eval runs in the set
    completed_runs: int = 0  # Runs that finished (status=completed)

    # Feedback counts
    human_feedback_count: int = 0  # Number of human feedback docs
    ai_feedback_count: int = 0  # Number of AI judge results

    # Pass rates (0–100 or None if no data)
    human_pass_pct: float | None = None  # % of human feedback that passed (overall_pass or derived)
    ai_pass_pct: float | None = None  # % of AI judge results that passed (score >= threshold)
    agreement_pct: float | None = None  # % of runs where human and AI verdicts match (overlap only)
    coverage_pct: float = 0.0  # Human feedback coverage: human_count / total_runs * 100

    # Task-specific
    task_kpis: Dict[str, Any] = Field(
        default_factory=dict,
        description="Taxonomy-driven KPIs (issue rates, distributions, etc.) per feedback category.",
    )

