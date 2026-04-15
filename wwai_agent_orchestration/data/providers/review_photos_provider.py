# data_providers/providers/review_photos_provider.py
"""
Review Photos Provider.

Retrieves photos from Yelp reviews stored in MongoDB.
Photos are attached to individual reviews and extracted here.
"""

from wwai_agent_orchestration.core.observability.logger import get_logger
import hashlib
from typing import Optional, Dict, Any, List

from wwai_agent_orchestration.data.connectors.base_mongo_provider import BaseProvider
from wwai_agent_orchestration.data.providers.models.scraped_photos import (
    ReviewPhotosInput,
    ReviewPhotosOutput,
    ReviewPhotoItem,
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

class ReviewPhotosProvider(BaseProvider):
    """
    Provider for review photos from Yelp.

    Reads from MongoDB where Yelp data is stored.
    Extracts photos from the 'reviews[].review_photos' arrays.

    Each photo maintains context about the review it came from
    (rating, reviewer, date) for RAG purposes.
    """

    def get(self, input_data: ReviewPhotosInput) -> ReviewPhotosOutput:
        """
        Get review photos for a business from Yelp data.

        Args:
            input_data: ReviewPhotosInput with business_id and optional filters

        Returns:
            ReviewPhotosOutput with photo items
        """
        business_id = input_data.business_id
        max_results = input_data.max_results
        min_rating = input_data.min_rating

        logger.info(
            f"Fetching review photos for business_id: {business_id}, "
            f"max_results: {max_results}, min_rating: {min_rating}"
        )

        # Get raw Yelp data from DB
        raw_data = self._get_yelp_data(business_id)

        if not raw_data:
            logger.info(f"No Yelp data found for business_id: {business_id}")
            return ReviewPhotosOutput(
                items=[],
                total_count=0,
                reviews_with_photos=0,
            )

        # Extract reviews array
        reviews = raw_data.get("reviews", [])

        if not reviews:
            logger.info(f"No reviews in Yelp data for business_id: {business_id}")
            return ReviewPhotosOutput(
                items=[],
                total_count=0,
                reviews_with_photos=0,
                yelp_business_id=raw_data.get("yelp_business_id"),
                business_name=raw_data.get("business_name"),
            )

        logger.info(f"Processing {len(reviews)} reviews for photos")

        # Extract photos from reviews
        items = []
        reviews_with_photos = 0

        for review in reviews:
            # Apply min_rating filter
            review_rating = review.get("rating")
            if min_rating and review_rating and review_rating < min_rating:
                continue

            # Get photos from this review
            review_photos = review.get("review_photos", [])

            if not review_photos:
                continue

            reviews_with_photos += 1

            # Extract review context
            review_context = self._extract_review_context(review)

            # Transform each photo
            for photo_url in review_photos:
                item = self._transform_photo(photo_url, review_context)
                if item:
                    items.append(item)

                    # Check max_results limit
                    if max_results and len(items) >= max_results:
                        break

            # Check if we've hit max_results
            if max_results and len(items) >= max_results:
                break

        logger.info(
            f"Returning {len(items)} review photos from {reviews_with_photos} reviews "
            f"for business_id: {business_id}"
        )

        return ReviewPhotosOutput(
            items=items,
            total_count=len(items),
            reviews_with_photos=reviews_with_photos,
            yelp_business_id=raw_data.get("yelp_business_id"),
            business_name=raw_data.get("business_name"),
        )

    def _get_yelp_data(self, business_id: str) -> Optional[Dict[str, Any]]:
        """Get Yelp data from MongoDB."""
        raw_doc = self.find_one(
            DB_BUSINESSES,
            COLLECTION_SCRAPED,
            {"business_id": business_id}
        )

        if not raw_doc:
            return None

        yelp_data = raw_doc.get("yelp_data")

        if not yelp_data:
            return None

        # Handle wrapped format: {"key": url, "value": data}
        if isinstance(yelp_data, dict) and "value" in yelp_data:
            return yelp_data.get("value")

        # Direct format (legacy)
        return yelp_data

    def _extract_review_context(self, review: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant context from a review."""
        author = review.get("author", {})

        # Handle text which might be an object with markdown/raw
        text_obj = review.get("text", {})
        if isinstance(text_obj, dict):
            # Text object might have 'raw' or 'markdown' field
            text_obj.get("raw") or text_obj.get("markdown", "")

        return {
            "review_id": review.get("encid", ""),
            "review_rating": review.get("rating"),
            "review_date": review.get("reviewCreatedAt"),
            "reviewer_name": author.get("displayName") or author.get("markupDisplayName"),
            "reviewer_id": author.get("encid"),
        }

    def _transform_photo(
        self,
        photo_url: str,
        review_context: Dict[str, Any]
    ) -> Optional[ReviewPhotoItem]:
        """Transform photo URL + review context to ReviewPhotoItem."""
        try:
            if not photo_url or not isinstance(photo_url, str):
                return None

            # Generate photo_id from URL hash
            photo_id = f"yelp_{hashlib.md5(photo_url.encode()).hexdigest()[:12]}"

            return ReviewPhotoItem(
                photo_id=photo_id,
                url=photo_url,
                review_id=review_context.get("review_id", ""),
                review_rating=review_context.get("review_rating"),
                review_date=review_context.get("review_date"),
                reviewer_name=review_context.get("reviewer_name"),
                reviewer_id=review_context.get("reviewer_id"),
                source="yelp",
            )

        except Exception as e:
            logger.error(f"Failed to transform review photo: {e}")
            return None

    def get_raw(self, business_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get raw reviews with photos without transformation.

        Returns only reviews that have photos attached.

        Args:
            business_id: Business ID

        Returns:
            List of reviews with review_photos, or None
        """
        raw_data = self._get_yelp_data(business_id)

        if not raw_data:
            return None

        reviews = raw_data.get("reviews", [])

        # Filter to only reviews with photos
        reviews_with_photos = [
            r for r in reviews
            if r.get("review_photos") and len(r["review_photos"]) > 0
        ]

        return reviews_with_photos if reviews_with_photos else None

    def get_photo_count(self, business_id: str) -> int:
        """
        Quick count of total review photos without full transformation.

        Args:
            business_id: Business ID

        Returns:
            Total count of review photos
        """
        raw_data = self._get_yelp_data(business_id)

        if not raw_data:
            return 0

        reviews = raw_data.get("reviews", [])

        total = 0
        for review in reviews:
            photos = review.get("review_photos", [])
            total += len(photos)

        return total
