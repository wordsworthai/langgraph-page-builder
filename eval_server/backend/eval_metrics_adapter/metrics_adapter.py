"""Legacy judge-based aggregate metrics adapter."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .eval_adapter import get_eval_results_for_set


def _compute_aggregate_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """General-purpose: total, completed, failed, avg_score, avg_compliance, score_distribution."""
    if not results:
        return {
            "total": 0,
            "completed": 0,
            "failed": 0,
            "avg_score": None,
            "avg_compliance": None,
            "score_distribution": {i: 0 for i in range(1, 11)},
        }

    total = len(results)
    completed = sum(1 for r in results if r.get("status") == "completed")
    failed = total - completed

    scores = []
    compliance_scores = []
    for r in results:
        output = r.get("output", {})
        avg_score = output.get("average_score")
        compliance = output.get("compliance_score")
        if avg_score is not None:
            scores.append(avg_score)
        if compliance is not None:
            compliance_scores.append(compliance)

    avg_score = round(sum(scores) / len(scores), 2) if scores else None
    avg_compliance = round(sum(compliance_scores) / len(compliance_scores), 2) if compliance_scores else None

    score_distribution = {i: 0 for i in range(1, 11)}
    for s in scores:
        bucket = max(1, min(10, int(round(s))))
        score_distribution[bucket] += 1

    return {
        "total": total,
        "completed": completed,
        "failed": failed,
        "avg_score": avg_score,
        "avg_compliance": avg_compliance,
        "score_distribution": score_distribution,
    }


def _compute_by_intent_metrics(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Task-specific: group by task_details.website_intention (landing_page pipeline)."""
    by_intent: Dict[str, Dict[str, Any]] = {}

    for r in results:
        output = r.get("output", {})
        task_details = r.get("task_details", {})
        avg_score = output.get("average_score")
        compliance = output.get("compliance_score")
        intent = task_details.get("website_intention", "unknown")

        if intent not in by_intent:
            by_intent[intent] = {"scores": [], "compliance": [], "count": 0}
        by_intent[intent]["count"] += 1
        if avg_score is not None:
            by_intent[intent]["scores"].append(avg_score)
        if compliance is not None:
            by_intent[intent]["compliance"].append(compliance)

    intent_metrics = {}
    for intent, data in by_intent.items():
        intent_metrics[intent] = {
            "count": data["count"],
            "avg_score": round(sum(data["scores"]) / len(data["scores"]), 2) if data["scores"] else None,
            "avg_compliance": round(sum(data["compliance"]) / len(data["compliance"]), 2) if data["compliance"] else None,
        }

    return intent_metrics


def get_eval_set_metrics(
    eval_set_id: str,
    task_name: str,
    mongo_uri: Optional[str] = None,
    db_name: str = "checkpointing_db",
) -> Dict[str, Any]:
    """Compute aggregate metrics for an eval set from judge results."""
    results = get_eval_results_for_set(
        eval_set_id=eval_set_id,
        task_name=task_name,
        mongo_uri=mongo_uri,
        db_name=db_name,
    )

    base = {
        "eval_set_id": eval_set_id,
        "task_name": task_name,
        **_compute_aggregate_metrics(results),
    }

    base["by_intent"] = _compute_by_intent_metrics(results)
    return base
