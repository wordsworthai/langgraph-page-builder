# contracts/section_repo.py

"""
Pydantic schema for Section Repository Entry.
Represents a section from the developer_hub_prod MongoDB collection.
"""

from pydantic import BaseModel, Field, ConfigDict, field_serializer, field_validator, model_validator
from typing import Optional, List, Any
from datetime import datetime
from bson import ObjectId


class SectionRepositoryEntry(BaseModel):
    """
    Represents a section entry in the section repository with visual and structural metadata.
    
    UPDATED: Added field_serializer for all ObjectId fields to ensure LangGraph compatibility.
    """
    
    # ========================================================================
    # MongoDB Identity (REQUIRED)
    # ========================================================================
    id: ObjectId = Field(..., alias="_id", description="MongoDB ObjectId")
    
    # ========================================================================
    # Visual Assets (OPTIONAL)
    # ========================================================================
    desktop_image_url: Optional[str] = Field(None, description="Desktop screenshot URL")
    mobile_image_url: Optional[str] = Field(None, description="Mobile screenshot URL")
    
    # ========================================================================
    # Section Classification (OPTIONAL - but needed for filtering)
    # ========================================================================
    section_l0: Optional[str] = Field(None, description="L0 category")
    section_l1: Optional[str] = Field(None, description="L1 category")
    section_label: Optional[str] = Field(None, description="Human-readable label")

    tags: Optional[List[str]] = Field(None, description="Section tags (e.g., ['smb'])")
    tag: Optional[str] = Field(None, description="Legacy single tag field (will be converted to tags list)", exclude=True)
    semantic_tags: Optional[List[str]] = Field(None, description="Semantic tags (e.g., ['header'])")

    
    # ========================================================================
    # AI-Generated Metadata (OPTIONAL)
    # ========================================================================
    section_layout_description: Optional[str] = Field(None, description="Layout description")
    content_description: Optional[str] = Field(None, description="Content description from metadata")
    styling_description: Optional[str] = Field(None, description="Styling description from metadata")
    industry: Optional[str] = Field(None, description="Industry vertical")
    sub_industry: Optional[str] = Field(None, description="Sub-industry")
    template_name: Optional[str] = Field(None, description="Template classification")
    
    # ========================================================================
    # Page Context (OPTIONAL)
    # ========================================================================
    page_url: Optional[str] = Field(None, description="Page URL")
    source: Optional[str] = Field(None, description="Source/extraction method")
    
    # ========================================================================
    # Visual Dimensions (OPTIONAL)
    # ========================================================================
    desktop_height: Optional[int] = Field(None, description="Desktop height (pixels)")
    mobile_height: Optional[int] = Field(None, description="Mobile height (pixels)")
    desktop_width: Optional[int] = Field(None, description="Desktop width (pixels)")
    mobile_width: Optional[int] = Field(None, description="Mobile width (pixels)")
    
    # ========================================================================
    # DOM Location (OPTIONAL)
    # ========================================================================
    xpath: Optional[str] = Field(None, description="Short XPath selector")
    xpath_full: Optional[str] = Field(None, description="Full XPath")
    
    # ========================================================================
    # Visual Properties (OPTIONAL)
    # ========================================================================
    opacity: Optional[float] = Field(None, description="CSS opacity (0.0-1.0)")
    is_visible: Optional[bool] = Field(None, description="Section visibility")
    css_category: Optional[str] = Field(None, description="Size category")
    
    # ========================================================================
    # Position Information (OPTIONAL)
    # ========================================================================
    position: Optional[int] = Field(None, description="Position on page")
    start_percent: Optional[float] = Field(None, description="Start % of page height")
    end_percent: Optional[float] = Field(None, description="End % of page height")
    new_section_index: Optional[int] = Field(None, description="Cleaned section index")
    
    # ========================================================================
    # Content Flags (OPTIONAL)
    # ========================================================================
    hasCode: Optional[bool] = Field(None, description="Has code elements")
    hasSchema: Optional[bool] = Field(None, description="Has schema markup")
    
    # ========================================================================
    # Related Object IDs (OPTIONAL) - ALL ObjectId fields
    # ========================================================================
    task_id: Optional[ObjectId] = Field(None, description="Parent task ObjectId")
    copied_from_section_id: Optional[ObjectId] = Field(None, description="Source section if copied")
    code_instance_id: Optional[ObjectId] = Field(None, description="Code instance reference")
    schema_instance_id: Optional[ObjectId] = Field(None, description="Schema instance reference")
    designer_project_section_id: Optional[ObjectId] = Field(None, description="Designer project link")
    
    # ========================================================================
    # Metadata (OPTIONAL)
    # ========================================================================
    is_new: Optional[bool] = Field(None, description="Newly created section")
    notes: Optional[str] = Field(None, description="Additional notes")
    status: Optional[str] = Field(None, description="Section status (ACTIVE, etc.)")
    
    created_by: Optional[str] = Field(None, description="Creator identifier")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    metadata_id: Optional[ObjectId] = Field(None, description="Metadata document _id")
    original_section_id: Optional[ObjectId] = Field(None, description="Original section if copied")
    
    # ========================================================================
    # MODEL VALIDATORS - Handle field conversions
    # ========================================================================
    
    @model_validator(mode='before')
    @classmethod
    def convert_tag_to_tags(cls, data: Any) -> Any:
        """
        Convert legacy 'tag' (string) field to 'tags' (list) if tags is not already set.
        This handles MongoDB documents that have 'tag' instead of 'tags'.
        """
        if isinstance(data, dict):
            # If 'tag' exists and 'tags' doesn't, convert tag to tags list
            if 'tag' in data and 'tags' not in data:
                tag_value = data.get('tag')
                if tag_value is not None:
                    # Convert string to list, or if already list, use it
                    if isinstance(tag_value, str):
                        data['tags'] = [tag_value]
                    elif isinstance(tag_value, list):
                        data['tags'] = tag_value
                    else:
                        data['tags'] = [str(tag_value)]
        return data

    
# ========================================================================
    # FIELD VALIDATORS - Convert strings to ObjectIds during input
    # ========================================================================
    
    @field_validator(
        'task_id',
        'copied_from_section_id', 
        'code_instance_id',
        'schema_instance_id',
        'designer_project_section_id',
        'metadata_id',
        'original_section_id',
        mode='before'
    )
    @classmethod
    def convert_str_to_objectid(cls, v):
        """Convert string ObjectIds to ObjectId instances during validation."""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return ObjectId(v)
            except Exception:
                return None  # Invalid ObjectId string → None
        return v  # Already ObjectId or other type
    
    # ========================================================================
    # FIELD SERIALIZERS - Convert ObjectIds to strings for LangGraph
    # ========================================================================
    
    @field_serializer('id')
    def serialize_id(self, value: ObjectId, _info) -> str:
        """Convert main ObjectId to string."""
        return str(value)
    
    @field_serializer('task_id')
    def serialize_task_id(self, value: Optional[ObjectId], _info) -> Optional[str]:
        """Convert task_id ObjectId to string."""
        return str(value) if value else None
    
    @field_serializer('copied_from_section_id')
    def serialize_copied_from_section_id(self, value: Optional[ObjectId], _info) -> Optional[str]:
        """Convert copied_from_section_id ObjectId to string."""
        return str(value) if value else None
    
    @field_serializer('code_instance_id')
    def serialize_code_instance_id(self, value: Optional[ObjectId], _info) -> Optional[str]:
        """Convert code_instance_id ObjectId to string."""
        return str(value) if value else None
    
    @field_serializer('schema_instance_id')
    def serialize_schema_instance_id(self, value: Optional[ObjectId], _info) -> Optional[str]:
        """Convert schema_instance_id ObjectId to string."""
        return str(value) if value else None
    
    @field_serializer('designer_project_section_id')
    def serialize_designer_project_section_id(self, value: Optional[ObjectId], _info) -> Optional[str]:
        """Convert designer_project_section_id ObjectId to string."""
        return str(value) if value else None
    
    @field_serializer('metadata_id')
    def serialize_metadata_id(self, value: Optional[ObjectId], _info) -> Optional[str]:
        """Convert metadata_id ObjectId to string."""
        return str(value) if value else None
    
    @field_serializer('original_section_id')
    def serialize_original_section_id(self, value: Optional[ObjectId], _info) -> Optional[str]:
        """Convert original_section_id ObjectId to string."""
        return str(value) if value else None
    
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        arbitrary_types_allowed=True, 
        populate_by_name=True
    )
    
    @property
    def section_id_str(self) -> str:
        """Get string representation of MongoDB ObjectId."""
        return str(self.id)


