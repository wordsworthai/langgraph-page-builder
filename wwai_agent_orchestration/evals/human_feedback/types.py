"""Standalone human feedback contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class HumanFeedbackSnapshot(BaseModel):
    """Latest human feedback snapshot linked to one run."""

    eval_set_id: str = Field(..., description="Eval set identifier.")
    case_id: str = Field(..., description="Case identifier.")
    run_id: str = Field(..., description="Run identifier.")
    thread_id: str = Field(..., description="Checkpoint thread identifier.")
    task_type: str = Field(..., description="Task type.")

    feedback: Dict[str, Any] = Field(default_factory=dict)

    feedback_schema_version: str = Field(default="v1")
    updated_by: Optional[str] = Field(default=None)
    updated_at: datetime = Field(default_factory=_utcnow)
    created_at: datetime = Field(default_factory=_utcnow)

