"""Schema for deterministic eval case collections."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from wwai_agent_orchestration.evals.types.eval_case import EvalCase, EvalType


class EvalSet(BaseModel):
    """A deterministic collection of eval cases with generation metadata."""

    eval_set_id: str = Field(..., description="Stable eval set identifier.")
    eval_type: EvalType = Field(..., description="The type of eval represented by cases.")
    version: str = Field(..., description="Eval set version for reproducibility.")
    seed: int = Field(..., description="Seed used for deterministic sampling.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    description: Optional[str] = None
    cases: list[EvalCase] = Field(default_factory=list)

