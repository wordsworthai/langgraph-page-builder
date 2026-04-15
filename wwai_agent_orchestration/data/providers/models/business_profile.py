# data_providers/models/business_profile.py
"""
Business Profile data models.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# =============================================================================
# SUPPORTING TYPES
# =============================================================================

class Address(BaseModel):
    """Structured address."""
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None


class Coordinates(BaseModel):
    """Geographic coordinates."""
    lat: float
    lng: float


class DayHours(BaseModel):
    """Hours for a single day."""
    day: str                    # "monday", "tuesday", etc.
    hours: str                  # "9:00 AM - 5:00 PM" or "Closed"


# =============================================================================
# INPUT / OUTPUT
# =============================================================================

class BusinessProfileInput(BaseModel):
    """Input for BusinessProfile retrieval."""
    business_id: str


class BusinessProfileOutput(BaseModel):
    """Derived business profile output."""
    
    # Identity
    business_id: str
    business_name: str
    display_name: Optional[str] = None
    tagline: Optional[str] = None
    description: Optional[str] = None
    
    # Classification
    industry: Optional[str] = None
    primary_category: Optional[str] = None
    categories: List[str] = Field(default_factory=list)
    
    # Contact
    phone: Optional[str] = None
    email: Optional[str] = None
    website_url: Optional[str] = None
    
    # Location
    address: Optional[Address] = None
    formatted_address: Optional[str] = None
    coordinates: Optional[Coordinates] = None
    google_maps_url: Optional[str] = None
    yelp_url: Optional[str] = None
    
    # Hours
    hours: Optional[List[DayHours]] = None
    
    # Services
    services: List[str] = Field(default_factory=list)
    specialties: Optional[str] = None
    price_level: Optional[str] = None
    
    # Status
    is_operational: bool = True
    year_established: Optional[int] = None
    
    # Ratings (aggregated)
    google_rating: Optional[float] = None
    google_review_count: Optional[int] = None
    yelp_rating: Optional[float] = None
    yelp_review_count: Optional[int] = None
    
    # Metadata
    data_sources: List[str] = Field(default_factory=list)  # ["google_maps", "yelp"]
    last_updated: datetime = Field(default_factory=datetime.utcnow)