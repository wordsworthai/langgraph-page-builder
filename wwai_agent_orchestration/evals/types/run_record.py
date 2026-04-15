"""Execution record contract for a single eval run attempt."""

from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

TaskType = Literal["trade_classification", "template_selection", "landing_page", "section_coverage", "color_palette", "curated_pages"]
RunStatus = Literal["created", "running", "completed", "failed"]


class RunRecord(BaseModel):
    """Record for one case execution attempt."""

    run_id: str = Field(..., description="Unique run attempt id.")
    thread_id: str = Field(..., description="Checkpoint thread id for this run.")
    case_id: str = Field(..., description="Deterministic case id this run executes.")
    eval_set_id: str = Field(..., description="Eval set identifier.")

    task_type: TaskType = Field(..., description="Task type to run.")
    task_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Task-specific metadata (e.g. business_id, business_index, website_intention for landing page evals).",
    )

    generation_version_id: Optional[str] = Field(
        None, description="Generated version ID from workflow."
    )
    request_id: Optional[str] = Field(
        None, description="Request/thread identifier for checkpoint resume."
    )

    inputs: Dict[str, Any] = Field(
        default_factory=dict,
        description="Input parameters used for this run.",
    )
    status: RunStatus = Field(
        default="created", description="Run status lifecycle state."
    )
    error_message: Optional[str] = Field(
        None, description="Error details for failed runs."
    )
    duration_ms: Optional[float] = Field(
        None, description="Execution duration in milliseconds."
    )
    attempt: int = Field(default=1, description="Attempt number for this case.")
    model_name: Optional[str] = Field(None, description="Model identifier used.")
    prompt_version: Optional[str] = Field(None, description="Prompt version if judge ran.")
    config_fingerprint: Optional[str] = Field(
        None, description="Hash of runtime config/prompt/model context."
    )

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

