# data_providers/providers/google_maps_provider.py
"""
Google Maps Provider.

Retrieves and transforms Google Maps data from MongoDB.
No API calls - data is saved by backend during business creation.
"""

from wwai_agent_orchestration.core.observability.logger import get_logger
from typing import Optional, Dict, Any

from wwai_agent_orchestration.data.connectors.base_mongo_provider import BaseProvider
from wwai_agent_orchestration.data.providers.models.google_maps import (
    GoogleMapsInput,
    GoogleMapsOutput,
)
from wwai_agent_orchestration.data.providers.utils.google_maps_parser import (
    parse_google_maps_data,
)

logger = get_logger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

DB_BUSINESSES = "businesses"
COLLECTION_SCRAPED = "business_scraped_data"


# =============================================================================
# EXCEPTIONS
# =============================================================================

class GoogleMapsValidationError(Exception):
    """Raised when Google Maps data fails validation."""
    pass


# =============================================================================
# PROVIDER
# =============================================================================

class GoogleMapsProvider(BaseProvider):
    """
    Provider for Google Maps business data.

    Reads from MongoDB where backend stores Google Places data.
    Transforms raw data into clean GoogleMapsOutput.

    Note: This provider does NOT call Google APIs.
    Data is saved by the backend during business creation flow.
    """

    def get(self, input_data: GoogleMapsInput) -> Optional[GoogleMapsOutput]:
        """
        Get Google Maps data for a business.

        Args:
            input_data: GoogleMapsInput with business_id

        Returns:
            GoogleMapsOutput with transformed data, or None if not found

        Raises:
            GoogleMapsValidationError: If data exists but is malformed
        """
        business_id = input_data.business_id
        logger.info(f"Fetching Google Maps data for business_id: {business_id}")

        # Query raw data from MongoDB
        raw_doc = self.find_one(
            DB_BUSINESSES,
            COLLECTION_SCRAPED,
            {"business_id": business_id}
        )

        if not raw_doc:
            logger.info(f"No scraped data document found for business_id: {business_id}")
            return None

        # Extract Google Maps data
        google_maps_data = raw_doc.get("google_maps_data")

        if not google_maps_data:
            logger.info(f"No google_maps_data in document for business_id: {business_id}")
            return None

        # Handle wrapped format: {"key": url, "value": data}
        if isinstance(google_maps_data, dict) and "value" in google_maps_data:
            raw_data = google_maps_data.get("value", {})
            source_url = google_maps_data.get("key")
            logger.debug(f"Extracted Google Maps data from wrapped format, source: {source_url}")
        else:
            # Direct format (legacy or different storage)
            raw_data = google_maps_data

        if not raw_data:
            logger.info(f"Empty google_maps_data value for business_id: {business_id}")
            return None

        # Transform to GoogleMapsOutput
        try:
            output = parse_google_maps_data(raw_data)

            logger.info(
                f"Successfully parsed Google Maps data for business_id: {business_id}",
                extra={
                    "display_name": output.display_name,
                    "derived_sector": output.derived_sector,
                    "has_rating": output.rating is not None,
                    "review_count": output.review_count,
                }
            )

            return output

        except Exception as e:
            logger.error(
                f"Failed to parse Google Maps data for business_id {business_id}: {e}",
                exc_info=True
            )
            raise GoogleMapsValidationError(f"Invalid Google Maps data structure: {e}")

    def get_by_business_id(self, business_id: str) -> Optional[GoogleMapsOutput]:
        """
        Convenience wrapper to fetch Google Maps data by business_id.
        """
        return self.get(GoogleMapsInput(business_id=business_id))

    def get_raw(self, business_id: str) -> Optional[Dict[str, Any]]:
        """
        Get raw Google Maps data without transformation.

        Useful for debugging or when raw access is needed.

        Args:
            business_id: Business ID

        Returns:
            Raw data dict or None
        """
        raw_doc = self.find_one(
            DB_BUSINESSES,
            COLLECTION_SCRAPED,
            {"business_id": business_id}
        )

        if not raw_doc:
            return None

        google_maps_data = raw_doc.get("google_maps_data")

        if isinstance(google_maps_data, dict) and "value" in google_maps_data:
            return google_maps_data.get("value")

        return google_maps_data
