"""Canonical key generation and task normalization helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass


RUN_ID_PATTERN = re.compile(r"^run_[a-zA-Z0-9]+$")
CASE_ID_PATTERN = re.compile(r"^case_[a-zA-Z0-9]+$")


def normalize_task_type(task_type: str) -> str:
    """Return task_type as-is (no normalization)."""
    return task_type


def build_eval_set_doc_id(eval_set_id: str) -> str:
    return f"evalset::{eval_set_id}"


def build_run_doc_id(eval_set_id: str, run_id: str) -> str:
    return f"run::{eval_set_id}::{run_id}"


def build_output_doc_id(eval_set_id: str, run_id: str, case_id: str) -> str:
    return f"output::{eval_set_id}::{run_id}::{case_id}"


def build_judge_doc_id(eval_set_id: str, run_id: str, task_name: str) -> str:
    return f"judge::{eval_set_id}::{run_id}::{task_name}"


@dataclass(frozen=True)
class CanonicalKeys:
    eval_set_id: str
    case_id: str
    run_id: str
    thread_id: str
    task_type: str


def validate_canonical_keys(keys: CanonicalKeys) -> None:
    """Validate key format and task type."""
    if not keys.eval_set_id:
        raise ValueError("eval_set_id must be non-empty")
    if not CASE_ID_PATTERN.match(keys.case_id):
        raise ValueError(f"Invalid case_id format: {keys.case_id}")
    if not RUN_ID_PATTERN.match(keys.run_id):
        raise ValueError(f"Invalid run_id format: {keys.run_id}")
    if not keys.thread_id:
        raise ValueError("thread_id must be non-empty")
    if not keys.task_type or not str(keys.task_type).strip():
        raise ValueError("task_type must be non-empty")

