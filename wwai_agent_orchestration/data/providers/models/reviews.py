# data_providers/models/reviews.py
"""
Reviews data models.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# =============================================================================
# SUPPORTING TYPES
# =============================================================================

class Review(BaseModel):
    """Normalized review from any source."""
    body: str
    rating: Optional[float] = None
    title: Optional[str] = None
    author: Optional[str] = None
    location: Optional[str] = None
    review_timestamp: Optional[datetime] = None
    review_provider: str              # "google", "yelp"


# =============================================================================
# INPUT / OUTPUT
# =============================================================================

class ReviewsInput(BaseModel):
    """Input for Reviews retrieval."""
    business_id: str
    
    # Filters
    min_length: Optional[int] = None
    min_rating: Optional[float] = None
    max_results: Optional[int] = None


class ReviewsOutput(BaseModel):
    """Reviews output."""
    reviews: List[Review] = Field(default_factory=list)
    average_rating: Optional[float] = None
    review_providers: List[str] = Field(default_factory=list)
    filtered_count: int = 0
    
    # Metadata
    last_updated: datetime = Field(default_factory=datetime.utcnow)