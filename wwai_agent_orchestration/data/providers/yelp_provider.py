# data_providers/providers/yelp_provider.py
"""
Yelp Provider.

Retrieves, scrapes, stores, and transforms Yelp business data AND reviews.
Handles the full lifecycle: DB lookup → API call (if needed) → store → transform.
"""

from wwai_agent_orchestration.core.observability.logger import get_logger
import requests
from typing import Optional, Dict, Any, List

from wwai_agent_orchestration.data.connectors.base_mongo_provider import BaseProvider
from wwai_agent_orchestration.data.providers.models.yelp import (
    YelpInput,
    YelpOutput,
)
from wwai_agent_orchestration.data.providers.utils.yelp_parser import (
    parse_yelp_data,
    parse_yelp_api_response,
)

logger = get_logger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

DB_BUSINESSES = "businesses"
COLLECTION_SCRAPED = "business_scraped_data"

# Reviews pagination
DEFAULT_REVIEWS_PER_PAGE = 20
MAX_REVIEW_PAGES = 2  # Limit to avoid excessive API calls


# =============================================================================
# EXCEPTIONS
# =============================================================================

class YelpValidationError(Exception):
    """Raised when Yelp data fails validation."""
    pass


# =============================================================================
# PROVIDER
# =============================================================================

class YelpProvider(BaseProvider):
    """
    Provider for Yelp business data and reviews.

    Handles:
    1. DB lookup first (return if exists)
    2. API scraping if URL provided and not in DB
    3. Reviews fetching from /reviews endpoint
    4. Storage of scraped data (non-blocking, preserves other data)
    5. Transformation to clean YelpOutput
    """

    def __init__(
        self,
        rapidapi_key: str,
        rapidapi_host: str = "yelp-business-api.p.rapidapi.com",
        timeout: int = 30
    ):
        super().__init__()
        self._rapidapi_key = rapidapi_key
        self._rapidapi_host = rapidapi_host
        self._timeout = timeout

    def get(self, input_data: YelpInput) -> Optional[YelpOutput]:
        """
        Get Yelp data for a business.

        Flow:
        1. Check DB for existing data
        2. If found → transform and return
        3. If not found + yelp_url provided → scrape API (details + reviews)
        4. If scrape successful → store in DB → transform and return
        5. If scrape fails → return None (graceful)
        """
        business_id = input_data.business_id
        yelp_url = input_data.yelp_url

        logger.info(
            f"Fetching Yelp data for business_id: {business_id}",
            extra={"has_yelp_url": bool(yelp_url)}
        )

        # STEP 1: Try DB lookup first
        db_data = self._get_from_db(business_id)

        if db_data:
            logger.info(f"Found Yelp data in DB for business_id: {business_id}")
            try:
                return parse_yelp_data(db_data, from_api=False)
            except Exception as e:
                logger.error(f"Failed to parse Yelp data from DB: {e}")
                raise YelpValidationError(f"Invalid Yelp data structure in DB: {e}")

        # STEP 2: No DB data - try API if URL provided
        if not yelp_url:
            logger.info(f"No Yelp data in DB and no URL provided for business_id: {business_id}")
            return None

        logger.info(f"Scraping Yelp data from API for business_id: {business_id}")

        # STEP 3: Call Yelp API for business details
        api_response = self._scrape_yelp_details(yelp_url)

        if not api_response:
            logger.warning(f"Yelp API scraping failed for business_id: {business_id}")
            return None

        # STEP 4: Parse API response
        try:
            parsed_data = parse_yelp_api_response(api_response)
        except Exception as e:
            logger.error(f"Failed to parse Yelp API response: {e}")
            raise YelpValidationError(f"Invalid Yelp API response structure: {e}")

        # STEP 5: Fetch reviews from /reviews endpoint
        yelp_business_id = api_response.get("encid") or api_response.get("business_id")
        reviews_data = self._scrape_yelp_reviews(yelp_url, yelp_business_id)

        if reviews_data:
            parsed_data["reviews"] = reviews_data.get("reviews", [])
            parsed_data["review_count"] = reviews_data.get("review_count")
            parsed_data["rating"] = reviews_data.get("rating")
            parsed_data["review_counts_by_rating"] = reviews_data.get("review_counts_by_rating")
            logger.info(f"Fetched {len(parsed_data.get('reviews', []))} reviews for business_id: {business_id}")
            # Also add reviews to raw for completeness
            api_response["reviews"] = reviews_data.get("reviews", [])
            api_response["review_count"] = reviews_data.get("review_count")
            api_response["review_counts_by_rating"] = reviews_data.get("review_counts_by_rating")

        # STEP 5.5: Preserve raw API response inside parsed data
        parsed_data["raw_data"] = api_response

        # STEP 6: Store in DB
        self._store_yelp_data(business_id, yelp_url, parsed_data)

        # STEP 7: Transform and return
        try:
            output = parse_yelp_data(parsed_data, from_api=True)

            logger.info(
                f"Successfully scraped and parsed Yelp data for business_id: {business_id}",
                extra={
                    "business_name": output.business_name,
                    "derived_sector": output.derived_sector,
                    "rating": output.rating,
                    "categories_count": len(output.categories),
                    "reviews_count": len(parsed_data.get("reviews", [])),
                }
            )

            return output

        except Exception as e:
            logger.error(f"Failed to transform Yelp data: {e}")
            raise YelpValidationError(f"Failed to transform Yelp data: {e}")

    def get_by_business_id(
        self,
        business_id: str,
        yelp_url: Optional[str] = None,
    ) -> Optional[YelpOutput]:
        """
        Convenience wrapper to fetch Yelp data without constructing input model.
        """
        return self.get(YelpInput(business_id=business_id, yelp_url=yelp_url))

    # =========================================================================
    # PRIVATE METHODS - API CALLS
    # =========================================================================

    def _scrape_yelp_details(self, yelp_url: str) -> Optional[Dict[str, Any]]:
        """Scrape Yelp business details via /each endpoint."""
        url = f"https://{self._rapidapi_host}/each"

        headers = {
            "x-rapidapi-key": self._rapidapi_key,
            "x-rapidapi-host": self._rapidapi_host
        }

        params = {"business_url": yelp_url}

        try:
            logger.debug(f"Calling Yelp /each API for URL: {yelp_url}")

            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=self._timeout
            )

            if response.status_code == 200:
                data = response.json()

                if data.get("message") == "200: success" and "business_details" in data:
                    logger.debug("Yelp /each API call successful")
                    return data["business_details"]
                else:
                    logger.warning(f"Yelp API returned unexpected format: {data.get('message')}")
                    return None
            else:
                logger.warning(f"Yelp API returned status {response.status_code}")
                return None

        except requests.Timeout:
            logger.warning(f"Yelp API timeout after {self._timeout}s")
            return None
        except requests.RequestException as e:
            logger.warning(f"Yelp API request failed: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error in Yelp API call: {e}")
            return None

    def _scrape_yelp_reviews(
        self,
        yelp_url: str,
        business_id: Optional[str] = None,
        max_pages: int = MAX_REVIEW_PAGES
    ) -> Optional[Dict[str, Any]]:
        """
        Scrape Yelp reviews via /reviews endpoint.

        Args:
            yelp_url: Yelp business URL
            business_id: Yelp's internal business ID (encid) - optional but faster
            max_pages: Maximum pages to fetch (default 2 = 40 reviews)

        Returns:
            Dict with reviews list and metadata, or None on failure
        """
        url = f"https://{self._rapidapi_host}/reviews"

        headers = {
            "x-rapidapi-key": self._rapidapi_key,
            "x-rapidapi-host": self._rapidapi_host
        }

        all_reviews = []
        review_metadata = {}
        end_cursor = None

        for page in range(max_pages):
            params = {
                "business_url": yelp_url,
                "reviews_per_page": str(DEFAULT_REVIEWS_PER_PAGE),
                "sort_by": "Yelp_sort",
                "rating_filter": "All_ratings"
            }

            if business_id:
                params["business_id"] = business_id

            # Use cursor for pagination after first page
            if end_cursor:
                params["end_cursor"] = end_cursor

            try:
                logger.debug(f"Calling Yelp /reviews API (page {page + 1})")

                response = requests.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=self._timeout
                )

                if response.status_code != 200:
                    logger.warning(f"Yelp reviews API returned status {response.status_code}")
                    break

                data = response.json()

                if "200" not in str(data.get("status", "")):
                    logger.warning(f"Yelp reviews API error: {data.get('status')}")
                    break

                # Store metadata from first page
                if page == 0:
                    review_metadata = {
                        "rating": data.get("rating"),
                        "review_count": data.get("review_count"),
                        "review_counts_by_rating": data.get("review_counts_by_rating"),
                        "review_counts_by_language": data.get("review_counts_by_language"),
                    }

                # Add reviews
                page_reviews = data.get("reviews", [])
                all_reviews.extend(page_reviews)

                logger.debug(f"Fetched {len(page_reviews)} reviews (total: {len(all_reviews)})")

                # Check for more pages
                if not data.get("has_next_page"):
                    break

                end_cursor = data.get("end_cursor")
                if not end_cursor:
                    break

            except requests.Timeout:
                logger.warning(f"Yelp reviews API timeout on page {page + 1}")
                break
            except requests.RequestException as e:
                logger.warning(f"Yelp reviews API request failed: {e}")
                break
            except Exception as e:
                logger.warning(f"Unexpected error fetching reviews: {e}")
                break

        if not all_reviews and not review_metadata:
            return None

        return {
            "reviews": all_reviews,
            **review_metadata
        }

    # =========================================================================
    # PRIVATE METHODS - DB OPERATIONS
    # =========================================================================

    def _get_from_db(self, business_id: str) -> Optional[Dict[str, Any]]:
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

        if isinstance(yelp_data, dict) and "value" in yelp_data:
            return yelp_data.get("value")

        return yelp_data

    def _store_yelp_data(
        self,
        business_id: str,
        yelp_url: str,
        data: Dict[str, Any]
    ) -> bool:
        """Store Yelp data in MongoDB (preserves google_maps_data)."""
        try:
            existing_doc = self.find_one(
                DB_BUSINESSES,
                COLLECTION_SCRAPED,
                {"business_id": business_id}
            )

            update_doc = {
                "business_id": business_id,
                "yelp_data": {
                    "key": yelp_url,
                    "value": data
                }
            }

            if existing_doc and "google_maps_data" in existing_doc:
                update_doc["google_maps_data"] = existing_doc["google_maps_data"]

            success = self.upsert_one(
                DB_BUSINESSES,
                COLLECTION_SCRAPED,
                {"business_id": business_id},
                update_doc
            )

            if success:
                logger.info(f"Stored Yelp data for business_id: {business_id}")

            return success

        except Exception as e:
            logger.error(f"Error storing Yelp data: {e}")
            return False

    def get_raw(self, business_id: str) -> Optional[Dict[str, Any]]:
        """Get raw Yelp data without transformation."""
        db_data = self._get_from_db(business_id)
        if db_data:
            return db_data.get("raw_data")
        return None

    def refresh_reviews(self, input_data: YelpInput) -> Optional[int]:
        """
        Force refresh reviews for an existing business.

        Returns:
            Number of reviews fetched, or None on failure
        """
        business_id = input_data.business_id
        yelp_url = input_data.yelp_url

        if not yelp_url:
            # Try to get URL from existing data
            existing = self._get_from_db(business_id)
            if not existing:
                return None
            yelp_url = existing.get("yelp_url")
            if not yelp_url:
                return None

        reviews_data = self._scrape_yelp_reviews(yelp_url)

        if not reviews_data:
            return None

        # Update existing document with new reviews
        existing = self._get_from_db(business_id) or {}
        existing["reviews"] = reviews_data.get("reviews", [])
        existing["review_count"] = reviews_data.get("review_count")
        existing["rating"] = reviews_data.get("rating")

        # Also update raw_data if it exists
        if "raw_data" in existing:
            existing["raw_data"]["reviews"] = reviews_data.get("reviews", [])
            existing["raw_data"]["review_count"] = reviews_data.get("review_count")

        self._store_yelp_data(business_id, yelp_url, existing)

        return len(reviews_data.get("reviews", []))
