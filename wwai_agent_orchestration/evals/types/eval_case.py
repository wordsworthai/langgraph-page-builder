"""Schema for a single deterministic eval case."""

from typing import Any, Dict, Literal

from pydantic import BaseModel, Field

EvalType = Literal["section_coverage", "template_selection", "landing_page", "color_palette", "curated_pages"]
WorkflowMode = Literal["preset_sections", "template_selection", "landing_page"]


class EvalCase(BaseModel):
    """A single immutable test input for one workflow execution."""

    case_id: str = Field(..., description="Deterministic case identifier.")
    eval_set_id: str = Field(..., description="Parent eval set id.")
    eval_type: EvalType = Field(..., description="Logical eval type.")
    workflow_mode: WorkflowMode = Field(..., description="Workflow factory mode.")
    set_inputs: Dict[str, Any] = Field(
        default_factory=dict,
        description="Eval-set metadata (business_id, business_index, website_intention, etc.).",
    )
    workflow_inputs: Dict[str, Any] = Field(
        default_factory=dict,
        description="Workflow inputs (preset_sections_input, landing_page_input, etc.).",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional non-input metadata for traceability/debugging.",
    )

