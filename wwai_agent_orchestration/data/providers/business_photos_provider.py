# data_providers/providers/business_photos_provider.py
"""
Business Photos Provider.

Retrieves business photos from Google Maps data stored in MongoDB.
Photos are stored during business creation via Google Places API.
"""

from wwai_agent_orchestration.core.observability.logger import get_logger
import hashlib
from typing import Optional, Dict, Any, List

from wwai_agent_orchestration.data.connectors.base_mongo_provider import BaseProvider
from wwai_agent_orchestration.data.providers.models.scraped_photos import (
    BusinessPhotosInput,
    BusinessPhotosOutput,
    BusinessPhotoItem,
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

class BusinessPhotosProvider(BaseProvider):
    """
    Provider for business photos from Google Maps.
    
    Reads from MongoDB where Google Places data is stored.
    Extracts and transforms the 'photos' array into BusinessPhotoItems.
    
    Note: This provider does NOT call Google APIs.
    Data is saved by the backend during business creation flow.
    """
    
    def get(self, input_data: BusinessPhotosInput) -> BusinessPhotosOutput:
        """
        Get business photos for a business from Google Maps data.
        
        Args:
            input_data: BusinessPhotosInput with business_id and optional filters
            
        Returns:
            BusinessPhotosOutput with photo items
        """
        business_id = input_data.business_id
        max_results = input_data.max_results
        
        logger.info(
            f"Fetching business photos for business_id: {business_id}, "
            f"max_results: {max_results}"
        )
        
        # Get raw Google Maps data from DB
        raw_data = self._get_google_maps_data(business_id)
        
        if not raw_data:
            logger.info(f"No Google Maps data found for business_id: {business_id}")
            return BusinessPhotosOutput(
                items=[],
                total_count=0,
            )
        
        # Extract photos array
        photos = raw_data.get("photos", [])
        
        if not photos:
            logger.info(f"No photos in Google Maps data for business_id: {business_id}")
            return BusinessPhotosOutput(
                items=[],
                total_count=0,
                place_id=raw_data.get("id"),
                business_name=raw_data.get("displayName"),
            )
        
        logger.info(f"Found {len(photos)} photos in Google Maps data")
        
        # Transform to BusinessPhotoItems
        items = []
        for photo in photos:
            item = self._transform_photo(photo)
            if item:
                items.append(item)
                
                # Check max_results limit
                if max_results and len(items) >= max_results:
                    break
        
        logger.info(
            f"Returning {len(items)} business photos for business_id: {business_id}"
        )
        
        return BusinessPhotosOutput(
            items=items,
            total_count=len(items),
            place_id=raw_data.get("id"),
            business_name=raw_data.get("displayName"),
        )
    
    def _get_google_maps_data(self, business_id: str) -> Optional[Dict[str, Any]]:
        """Get Google Maps data from MongoDB."""
        raw_doc = self.find_one(
            DB_BUSINESSES,
            COLLECTION_SCRAPED,
            {"business_id": business_id}
        )
        
        if not raw_doc:
            return None
        
        google_maps_data = raw_doc.get("google_maps_data")
        
        if not google_maps_data:
            return None
        
        # Handle wrapped format: {"key": url, "value": data}
        if isinstance(google_maps_data, dict) and "value" in google_maps_data:
            return google_maps_data.get("value")
        
        # Direct format (legacy)
        return google_maps_data
    
    def _transform_photo(self, raw: Dict[str, Any]) -> Optional[BusinessPhotoItem]:
        """Transform raw Google Maps photo to BusinessPhotoItem."""
        try:
            url = raw.get("url")
            
            if not url:
                return None
            
            width = raw.get("widthPx", 0)
            height = raw.get("heightPx", 0)
            index = raw.get("index")
            
            # Generate photo_id from URL hash or index
            if index is not None:
                photo_id = f"gmaps_photo_{index}"
            else:
                photo_id = f"gmaps_{hashlib.md5(url.encode()).hexdigest()[:12]}"
            
            # Calculate aspect ratio
            aspect_ratio = None
            if width and height:
                aspect_ratio = round(width / height, 2)
            
            return BusinessPhotoItem(
                photo_id=photo_id,
                url=url,
                width=width,
                height=height,
                aspect_ratio=aspect_ratio,
                index=index,
                source="google_maps",
            )
        
        except Exception as e:
            logger.error(f"Failed to transform business photo: {e}")
            return None
    
    def get_raw(self, business_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get raw photos array without transformation.
        
        Useful for debugging or when raw access is needed.
        
        Args:
            business_id: Business ID
            
        Returns:
            Raw photos list or None
        """
        raw_data = self._get_google_maps_data(business_id)
        
        if not raw_data:
            return None
        
        return raw_data.get("photos")