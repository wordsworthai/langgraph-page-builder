"""Typed output payloads for supported eval workflow modes."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class TemplateSelectionOutput(BaseModel):
    """Final output payload for template selection eval runs."""

    workflow_mode: Literal["template_selection"] = "template_selection"
    template_id: Optional[str] = None
    selected_template_index: Optional[int] = None
    rationale: Optional[str] = None
    section_plan: Optional[List[Dict[str, Any]]] = None
    generation_version_id: Optional[str] = None
    html_url: Optional[str] = None
    raw_output: Dict[str, Any] = Field(default_factory=dict)


class PresetSectionsOutput(BaseModel):
    """Final output payload for preset sections (section coverage) runs."""

    workflow_mode: Literal["preset_sections"] = "preset_sections"
    section_ids: List[str] = Field(default_factory=list)
    generation_version_id: Optional[str] = None
    html_url: Optional[str] = None
    artifact_ref: Optional[str] = None
    raw_output: Dict[str, Any] = Field(default_factory=dict)


class LandingPageOutput(BaseModel):
    """Final output payload for end-to-end landing page runs."""

    workflow_mode: Literal["landing_page"] = "landing_page"
    generation_version_id: Optional[str] = None
    html_url: Optional[str] = None
    template_id: Optional[str] = None
    selected_sections: List[str] = Field(default_factory=list)
    artifact_ref: Optional[str] = None
    raw_output: Dict[str, Any] = Field(default_factory=dict)
