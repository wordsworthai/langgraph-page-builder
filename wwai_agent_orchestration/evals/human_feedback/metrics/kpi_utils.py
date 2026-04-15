"""Taxonomy-driven KPI computation for human feedback."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional

from wwai_agent_orchestration.evals.human_feedback.taxonomy.contracts import (
    TaskFeedbackTaxonomy,
)
from wwai_agent_orchestration.evals.human_feedback.utils import is_true


def _bool_issue_rate(feedback_docs: List[Dict[str, Any]], key: str) -> float:
    """
    Percentage of answered feedback docs where the given boolean category is True (issue reported).

    Denominator = docs with explicit True or False only (unanswered excluded).
    For taxonomy categories like template_structure_issue, True = problem, False = no issue.
    Returns share of reviewers who flagged an issue among those who answered.
    """
    answered = [
        d
        for d in feedback_docs
        if d.get("feedback", {}).get(key) is True
        or d.get("feedback", {}).get(key) is False
    ]
    if not answered:
        return 0.0
    issue_count = sum(
        1 for d in answered if is_true(d.get("feedback", {}).get(key))
    )
    return (issue_count / len(answered)) * 100.0


def _bool_unanswered_rate(feedback_docs: List[Dict[str, Any]], key: str) -> float:
    """
    Percentage of feedback docs that did not answer the given boolean category.

    Counts docs where value is not True or False (None, missing, or other).
    Denominator = total feedback docs. Higher = less coverage for this category.
    """
    if not feedback_docs:
        return 0.0
    unanswered_count = sum(
        1
        for d in feedback_docs
        if d.get("feedback", {}).get(key) not in (True, False)
    )
    return (unanswered_count / len(feedback_docs)) * 100.0


def _number_avg(feedback_docs: List[Dict[str, Any]], key: str) -> float:
    """
    Average of numeric values for the given number category.

    Excludes None, missing, and non-numeric values. Returns 0.0 if no valid values.
    """
    values = []
    for d in feedback_docs:
        v = d.get("feedback", {}).get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            values.append(float(v))
    if not values:
        return 0.0
    return sum(values) / len(values)


def _number_unanswered_rate(feedback_docs: List[Dict[str, Any]], key: str) -> float:
    """
    Percentage of feedback docs that did not provide a valid number for this category.
    """
    if not feedback_docs:
        return 0.0
    unanswered_count = sum(
        1
        for d in feedback_docs
        if not _is_valid_number(d.get("feedback", {}).get(key))
    )
    return (unanswered_count / len(feedback_docs)) * 100.0


def _is_valid_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _enum_distribution(
    feedback_docs: List[Dict[str, Any]],
    key: str,
    options: Optional[List[str]] = None,
) -> str:
    """
    Distribution of enum values as a string: "option1: count1, option2: count2, ...".

    Counts only values in options if provided; otherwise counts all non-empty values.
    Sorted by count descending, then by option order.
    """
    counts: Counter[str] = Counter()
    for d in feedback_docs:
        v = d.get("feedback", {}).get(key)
        if v is None or v == "":
            continue
        s = str(v).strip()
        if not s:
            continue
        if options is None or s in options:
            counts[s] += 1
    if not counts:
        return ""
    # Sort by count desc, then by option order if available
    sorted_items = sorted(
        counts.items(),
        key=lambda x: (-x[1], options.index(x[0]) if options and x[0] in options else 999),
    )
    return ", ".join(f"{k}: {v}" for k, v in sorted_items)


def _enum_unanswered_rate(
    feedback_docs: List[Dict[str, Any]],
    key: str,
    options: Optional[List[str]] = None,
) -> float:
    """
    Percentage of feedback docs that did not provide a valid enum value (in options).
    """
    if not feedback_docs:
        return 0.0
    unanswered_count = 0
    for d in feedback_docs:
        v = d.get("feedback", {}).get(key)
        if v is None or v == "":
            unanswered_count += 1
        elif options and str(v).strip() not in options:
            unanswered_count += 1
        # else: valid value in options (or no options = any non-empty is valid)
    return (unanswered_count / len(feedback_docs)) * 100.0


def compute_task_human_kpis_from_taxonomy(
    taxonomy: TaskFeedbackTaxonomy,
    feedback_docs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Compute KPIs for boolean, number, and enum categories in the taxonomy.

    Boolean: {key}_pct (issue rate), {key}_unanswered_pct
    Number: {key}_avg (average), {key}_unanswered_pct
    Enum: {key}_distribution (e.g. "pass: 5, fail: 2"), {key}_unanswered_pct
    """
    result: Dict[str, Any] = {}
    active_categories = sorted(
        (c for c in taxonomy.categories if c.active),
        key=lambda c: c.order,
    )
    for cat in active_categories:
        if cat.value_type == "boolean":
            result[f"{cat.key}_pct"] = _bool_issue_rate(feedback_docs, cat.key)
            result[f"{cat.key}_unanswered_pct"] = _bool_unanswered_rate(
                feedback_docs, cat.key
            )
        elif cat.value_type == "number":
            result[f"{cat.key}_avg"] = _number_avg(feedback_docs, cat.key)
            result[f"{cat.key}_unanswered_pct"] = _number_unanswered_rate(
                feedback_docs, cat.key
            )
        elif cat.value_type == "enum":
            dist = _enum_distribution(
                feedback_docs, cat.key, options=cat.options
            )
            result[f"{cat.key}_distribution"] = dist
            result[f"{cat.key}_unanswered_pct"] = _enum_unanswered_rate(
                feedback_docs, cat.key, options=cat.options
            )
    return result
