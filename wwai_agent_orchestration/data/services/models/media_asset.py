"""
Media asset domain model.
section_l0/l1 removed.
"""
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict


class MediaAsset(BaseModel):
    """Domain model for media assets used in matching."""
    
    model_config = ConfigDict(frozen=True)
    
    # Core attributes
    src: str = Field(description="Source URL of the media asset")
    width: Optional[int] = Field(None, description="Width in pixels")
    height: Optional[int] = Field(None, description="Height in pixels")
    media_type: Literal["image", "video"] = Field("image", description="Type of media")
    
    # Metadata container for provider context, match info, etc.
    meta: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @field_validator("width", "height", mode="before")
    @classmethod
    def validate_dimensions(cls, v):
        if v is not None:
            if not isinstance(v, int) or v <= 0:
                raise ValueError("Dimensions must be positive integers")
        return v
    
    @field_validator("src", mode="before")
    @classmethod
    def validate_src(cls, v):
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("Source URL cannot be empty")
        return v.strip()
    
    def aspect_ratio(self) -> Optional[float]:
        """Calculate aspect ratio."""
        if self.width and self.height and self.width > 0 and self.height > 0:
            return self.width / self.height
        return None
    
    def orientation(self) -> str:
        """Determine orientation: square, landscape, or portrait."""
        if not self.width or not self.height:
            return "unknown"
        if self.width == self.height:
            return "square"
        return "landscape" if self.width > self.height else "portrait"