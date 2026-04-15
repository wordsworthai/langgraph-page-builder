# data_providers/models/scraped_photos.py
"""
Scraped Photos data models.

Models for:
- Business Photos (from Google Maps)
- Review Photos (from Yelp reviews)
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# =============================================================================
# BUSINESS PHOTOS (Google Maps)
# =============================================================================

class BusinessPhotosInput(BaseModel):
    """Input for BusinessPhotosProvider."""
    business_id: str
    max_results: Optional[int] = None


class BusinessPhotoItem(BaseModel):
    """Single business photo from Google Maps."""
    photo_id: str                        # Generated from index or URL hash
    url: str
    width: int
    height: int
    aspect_ratio: Optional[float] = None
    index: Optional[int] = None          # Original index from Google Maps
    source: str = "google_maps"


class BusinessPhotosOutput(BaseModel):
    """Business photos output."""
    items: List[BusinessPhotoItem] = Field(default_factory=list)
    total_count: int = 0
    
    # Metadata
    place_id: Optional[str] = None       # Google Maps place ID
    business_name: Optional[str] = None
    data_source: str = "google_maps"
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# REVIEW PHOTOS (Yelp)
# =============================================================================

class ReviewPhotosInput(BaseModel):
    """Input for ReviewPhotosProvider."""
    business_id: str
    max_results: Optional[int] = None
    min_rating: Optional[int] = None     # Filter by minimum review rating


class ReviewPhotoItem(BaseModel):
    """Single photo from a Yelp review."""
    photo_id: str                        # Generated from URL
    url: str
    
    # Review context
    review_id: str                       # encid of the review
    review_rating: Optional[int] = None
    review_date: Optional[str] = None
    reviewer_name: Optional[str] = None
    reviewer_id: Optional[str] = None
    
    # Metadata
    source: str = "yelp"


class ReviewPhotosOutput(BaseModel):
    """Review photos output."""
    items: List[ReviewPhotoItem] = Field(default_factory=list)
    total_count: int = 0
    reviews_with_photos: int = 0         # Number of reviews that had photos
    
    # Metadata
    yelp_business_id: Optional[str] = None
    business_name: Optional[str] = None
    data_source: str = "yelp"
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)