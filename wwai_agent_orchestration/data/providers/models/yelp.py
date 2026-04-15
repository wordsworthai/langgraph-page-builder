# data_providers/models/yelp.py
"""
Yelp data models for provider input/output.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# =============================================================================
# INPUT / OUTPUT
# =============================================================================

class YelpInput(BaseModel):
    """Input for YelpProvider."""
    business_id: str
    yelp_url: Optional[str] = None  # If provided and not in DB, triggers API call


class YelpOutput(BaseModel):
    """
    Clean, pre-processed Yelp data.
    
    All heavy transformation is done by the provider.
    Downstream nodes consume these clean fields directly.
    """
    
    # Identity
    yelp_business_id: Optional[str] = None
    business_name: str
    alias: Optional[str] = None
    
    # Classification (pre-derived by provider)
    categories: List[str] = Field(default_factory=list)  # Already split from comma-separated
    derived_sector: Optional[str] = None
    
    # Ratings (already converted to proper types)
    rating: Optional[float] = None  # Converted from string
    review_count: Optional[int] = None
    price: Optional[str] = None
    
    # Contact
    phone: Optional[str] = None
    localized_phone: Optional[str] = None
    website: Optional[str] = None
    yelp_url: Optional[str] = None
    
    # Location
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    full_address: Optional[str] = None
    
    # Rich content (pre-extracted by provider)
    specialties: Optional[str] = None
    history: Optional[str] = None
    services: List[str] = Field(default_factory=list)  # Already split
    year_established: Optional[int] = None  # Already converted to int
    hours: Optional[str] = None
    
    # Status
    is_closed: bool = False
    
    # Metadata
    data_source: str = "yelp"
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    from_api: bool = False  # True if freshly scraped, False if from DB
    
    class Config:
        extra = "ignore"