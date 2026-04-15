"""Shared helpers for metrics scripts."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_MONGO_URI = "mongodb://localhost:27020/"
DEFAULT_DB_NAME = "eval"
FEEDBACK_COLLECTION = "human_feedback"
RUNS_COLLECTION = "eval_runs"
JUDGE_COLLECTION = "eval_judge_results"
EVAL_SETS_COLLECTION = "eval_sets"


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, default=str))
