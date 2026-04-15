# data_providers/models/google_maps.py
"""
Google Maps data models for provider input/output.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# =============================================================================
# SUPPORTING TYPES
# =============================================================================

class ReviewSummary(BaseModel):
    """Cleaned review summary."""
    author: str
    rating: Optional[float] = None
    text: str
    relative_time: Optional[str] = None


class Coordinates(BaseModel):
    """Geographic coordinates."""
    lat: float
    lng: float


# =============================================================================
# INPUT / OUTPUT
# =============================================================================

class GoogleMapsInput(BaseModel):
    """Input for GoogleMapsProvider."""
    business_id: str


class GoogleMapsOutput(BaseModel):
    """
    Clean, pre-processed Google Maps data.
    
    All heavy transformation is done by the provider.
    Downstream nodes consume these clean fields directly.
    """
    
    # Identity
    place_id: Optional[str] = None
    display_name: str
    
    # Location
    formatted_address: Optional[str] = None
    coordinates: Optional[Coordinates] = None
    
    # Classification (pre-derived by provider)
    primary_type: Optional[str] = None
    primary_type_display: Optional[str] = None
    types: List[str] = Field(default_factory=list)
    derived_sector: Optional[str] = None
    
    # Contact
    phone: Optional[str] = None
    international_phone: Optional[str] = None
    website: Optional[str] = None
    google_maps_url: Optional[str] = None
    
    # Ratings
    rating: Optional[float] = None
    review_count: Optional[int] = None
    price_level: Optional[str] = None
    
    # Content (pre-extracted by provider)
    editorial_summary: Optional[str] = None
    hours: List[str] = Field(default_factory=list)  # Already formatted strings
    recent_reviews: List[ReviewSummary] = Field(default_factory=list)
    
    # Status
    business_status: Optional[str] = None
    is_operational: bool = True
    
    # Metadata
    data_source: str = "google_maps"
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        extra = "ignore"