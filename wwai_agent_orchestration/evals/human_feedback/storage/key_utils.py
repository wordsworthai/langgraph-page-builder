"""Local key helpers for feedback (no legacy imports)."""

from __future__ import annotations

import re
from dataclasses import dataclass


RUN_ID_PATTERN = re.compile(r"^run_[a-zA-Z0-9]+$")
CASE_ID_PATTERN = re.compile(r"^case_[a-zA-Z0-9]+$")


@dataclass(frozen=True)
class CanonicalFeedbackKeys:
    """Required identifiers for a feedback snapshot."""

    eval_set_id: str
    case_id: str
    run_id: str
    thread_id: str
    task_type: str


def validate_feedback_keys(keys: CanonicalFeedbackKeys) -> None:
    """Validate feedback key shape and required fields."""
    if not keys.eval_set_id:
        raise ValueError("eval_set_id must be non-empty")
    if not CASE_ID_PATTERN.match(keys.case_id):
        raise ValueError(f"Invalid case_id format: {keys.case_id}")
    if not RUN_ID_PATTERN.match(keys.run_id):
        raise ValueError(f"Invalid run_id format: {keys.run_id}")
    if not keys.thread_id:
        raise ValueError("thread_id must be non-empty")
    if not keys.task_type or not keys.task_type.strip():
        raise ValueError("task_type must be non-empty")


def build_feedback_doc_id(eval_set_id: str, run_id: str) -> str:
    """Build stable _id for latest feedback snapshot per run."""
    return f"feedback::{eval_set_id}::{run_id}"
