"""
Template update request models for saving editor changes.
"""

from typing import Dict, Any, List, Optional

from pydantic import BaseModel


class SectionUpdate(BaseModel):
    """Template JSON update for a single section."""

    template_json_for_compiler: Dict[str, Any]


class SaveTemplateRequest(BaseModel):
    """Request to save template JSON updates."""

    section_updates: Dict[str, SectionUpdate]  # key = schema_section_id
    section_order: Optional[List[str]] = None  # ordered schema_section_ids
    deleted_sections: Optional[List[str]] = None  # schema_section_ids to remove
