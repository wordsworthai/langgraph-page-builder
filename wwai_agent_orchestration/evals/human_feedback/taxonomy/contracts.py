"""Contracts for feedback taxonomy."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


ValueType = Literal["boolean", "text", "enum", "number"]
Severity = Literal["blocker", "major", "minor"]
FeedbackMode = Literal["boolean", "categories", "mixed"]


class TaxonomyCategory(BaseModel):
    """Single feedback category definition."""

    key: str
    label: str
    value_type: ValueType
    required: bool = False
    weight: float = 1.0
    severity: Severity = "minor"
    placeholder: Optional[str] = None
    icon: Optional[str] = None
    options: Optional[List[str]] = None
    order: int = 0
    active: bool = True


class TaskFeedbackTaxonomy(BaseModel):
    """Task-scoped taxonomy definition."""

    task_type: str
    schema_version: str = "v1"
    mode: FeedbackMode = "categories"
    categories: List[TaxonomyCategory] = Field(default_factory=list)
    display_name: Optional[str] = None
    description: Optional[str] = None
    updated_at: datetime = Field(default_factory=_utcnow)
