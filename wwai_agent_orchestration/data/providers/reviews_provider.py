# data_providers/providers/reviews_provider.py
"""
Reviews Provider.

Aggregates and normalizes reviews from Google Maps and Yelp.
"""

from wwai_agent_orchestration.core.observability.logger import get_logger
from typing import Optional, Dict, Any, List
from datetime import datetime

from wwai_agent_orchestration.data.connectors.base_mongo_provider import BaseProvider
from wwai_agent_orchestration.data.providers.models.reviews import (
    ReviewsInput,
    ReviewsOutput,
    Review,
)

logger = get_logger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

DB_BUSINESSES = "businesses"
COLLECTION_SCRAPED = "business_scraped_data"


# =============================================================================
# PROVIDER
# =============================================================================

class ReviewsProvider(BaseProvider):
    """
    Provider for reviews data.

    Aggregates Google Maps + Yelp reviews into unified format.
    """

    def get(self, input_data: ReviewsInput) -> ReviewsOutput:
        """
        Get reviews for a business.

        Args:
            input_data: ReviewsInput with business_id and optional filters

        Returns:
            ReviewsOutput with normalized reviews
        """
        business_id = input_data.business_id
        logger.info(f"Getting reviews for: {business_id}")

        # Query raw data
        raw_data = self.find_one(
            DB_BUSINESSES,
            COLLECTION_SCRAPED,
            {"business_id": business_id}
        )

        if not raw_data:
            logger.warning(f"No data found for business_id: {business_id}")
            return ReviewsOutput(
                reviews=[],
                review_providers=[],
                filtered_count=0,
            )

        # Extract and normalize reviews from all sources
        all_reviews = []
        providers = set()

        # Google Maps reviews
        google_data = raw_data.get("google_maps_data", {})
        google_data = google_data.get("value", {})
        if google_data.get("reviews"):
            google_reviews = self._normalize_google_reviews(google_data["reviews"])
            all_reviews.extend(google_reviews)
            if google_reviews:
                providers.add("google")

        # Yelp reviews
        yelp_data = raw_data.get("yelp_data", {})
        yelp_data = yelp_data.get("value", {})
        if yelp_data.get("reviews"):
            yelp_reviews = self._normalize_yelp_reviews(yelp_data["reviews"])
            all_reviews.extend(yelp_reviews)
            if yelp_reviews:
                providers.add("yelp")

        # Apply filters
        filtered_reviews = self._apply_filters(
            all_reviews,
            min_length=input_data.min_length,
            min_rating=input_data.min_rating,
            max_results=input_data.max_results,
        )

        # Calculate average rating
        average_rating = self._calculate_average_rating(filtered_reviews)

        return ReviewsOutput(
            reviews=filtered_reviews,
            average_rating=average_rating,
            review_providers=list(providers),
            filtered_count=len(filtered_reviews),
            last_updated=datetime.utcnow(),
        )

    def get_by_business_id(
        self,
        business_id: str,
        min_length: Optional[int] = None,
        min_rating: Optional[float] = None,
        max_results: Optional[int] = None,
    ) -> ReviewsOutput:
        """
        Convenience wrapper to fetch reviews without constructing input model.
        """
        return self.get(
            ReviewsInput(
                business_id=business_id,
                min_length=min_length,
                min_rating=min_rating,
                max_results=max_results,
            )
        )

    def _normalize_google_reviews(
        self,
        reviews: List[Dict[str, Any]]
    ) -> List[Review]:
        """Normalize Google Maps reviews."""
        normalized = []

        for r in reviews:
            # Skip if no text
            text = r.get("text")
            if not text:
                continue

            # Parse timestamp
            review_timestamp = None
            if r.get("time"):
                try:
                    review_timestamp = datetime.fromtimestamp(r["time"])
                except:
                    pass

            normalized.append(Review(
                body=text,
                rating=r.get("rating"),
                title=None,  # Google reviews don't have titles
                author=r.get("author_name"),
                location=None,  # Google reviews don't have location
                review_timestamp=review_timestamp,
                review_provider="google",
            ))

        return normalized

    def _normalize_yelp_reviews(
        self,
        reviews: List[Dict[str, Any]]
    ) -> List[Review]:
        """Normalize Yelp reviews."""
        normalized = []

        for r in reviews:
            # Handle nested text structure
            text = r.get("text")
            if isinstance(text, dict):
                text = text.get("full")

            if not text:
                continue

            # Parse author
            author = r.get("author")
            if isinstance(author, dict):
                author = author.get("displayName")

            # Parse location
            location = None
            if isinstance(r.get("author"), dict):
                location = r["author"].get("displayLocation")

            # Parse timestamp
            review_timestamp = None
            if r.get("reviewCreatedAt"):
                try:
                    # Yelp format: "2025-08-31T12:46:48-04:00"
                    ts = r["reviewCreatedAt"]
                    if "T" in ts:
                        review_timestamp = datetime.fromisoformat(
                            ts.replace("Z", "+00:00")
                        )
                except:
                    pass

            normalized.append(Review(
                body=text,
                rating=r.get("rating"),
                title=None,  # Yelp reviews might have title but usually not
                author=author,
                location=location,
                review_timestamp=review_timestamp,
                review_provider="yelp",
            ))

        return normalized

    def _apply_filters(
        self,
        reviews: List[Review],
        min_length: Optional[int] = None,
        min_rating: Optional[float] = None,
        max_results: Optional[int] = None,
    ) -> List[Review]:
        """Apply filters to reviews."""
        filtered = reviews

        # Filter by length
        if min_length:
            filtered = [r for r in filtered if len(r.body) >= min_length]

        # Filter by rating
        if min_rating:
            filtered = [
                r for r in filtered
                if r.rating is not None and r.rating >= min_rating
            ]

        # Sort by rating (descending)
        filtered.sort(key=lambda r: r.rating or 0, reverse=True)

        # Limit results
        if max_results:
            filtered = filtered[:max_results]

        return filtered

    def _calculate_average_rating(self, reviews: List[Review]) -> Optional[float]:
        """Calculate average rating from reviews."""
        ratings = [r.rating for r in reviews if r.rating is not None]

        if not ratings:
            return None

        return round(sum(ratings) / len(ratings), 2)
