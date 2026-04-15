"""Shared utilities for metrics computation."""

from __future__ import annotations

from typing import Any, Dict

from wwai_agent_orchestration.evals.human_feedback.policy import derive_overall_pass
from wwai_agent_orchestration.evals.metrics.contracts import EvalMetricsInput


def safe_pct(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return (numerator / denominator) * 100.0


def is_human_pass(doc: Dict[str, Any]) -> bool:
    feedback = doc.get("feedback", {})
    if "overall_pass" in feedback:
        return feedback.get("overall_pass") is True
    try:
        return derive_overall_pass(str(doc.get("task_type", "")), feedback)
    except ValueError:
        return False


def is_ai_pass(doc: Dict[str, Any], score_threshold: float = 0.7) -> bool:
    result = doc.get("result", {})
    if result.get("parse_error"):
        return False
    score = result.get("average_score")
    if isinstance(score, (float, int)):
        return float(score) >= score_threshold
    return False


def agreement_pct(
    input_bundle: EvalMetricsInput,
    *,
    ai_threshold: float,
) -> float | None:
    by_run_feedback = {
        doc.get("run_id"): is_human_pass(
            {
                "feedback": doc.get("feedback", {}),
                "task_type": doc.get("task_type", input_bundle.task_type),
            }
        )
        for doc in input_bundle.human_feedback
        if doc.get("run_id")
    }
    by_run_ai = {
        doc.get("run_id"): is_ai_pass(doc, score_threshold=ai_threshold)
        for doc in input_bundle.judge_results
        if doc.get("run_id")
    }
    overlap = sorted(set(by_run_feedback.keys()) & set(by_run_ai.keys()))
    if not overlap:
        return None
    matches = sum(1 for run_id in overlap if by_run_feedback[run_id] == by_run_ai[run_id])
    return (matches / len(overlap)) * 100.0
