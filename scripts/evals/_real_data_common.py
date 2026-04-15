"""Shared helpers for real-data eval sample scripts."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_MONGO_URI = "mongodb://localhost:27020/"
DEFAULT_DB_NAME = "eval"
DEFAULT_SAMPLE_SIZE = 3


def timestamp_suffix() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, default=str))


def sample_business_ids(business_ids: Iterable[str], sample_size: int) -> List[str]:
    values = [business_id for business_id in business_ids if business_id]
    return values[:sample_size]

