"""
Client for fetching media from multiple providers.

Supports:
- Stock/Generated media (MediaAssetsProvider)
- Google Maps business photos (BusinessPhotosProvider)
"""
from wwai_agent_orchestration.core.observability.logger import get_logger
from typing import List, Literal

from wwai_agent_orchestration.data.providers.media_assets_provider import (
    MediaAssetsProvider,
)
from wwai_agent_orchestration.data.providers.business_photos_provider import (
    BusinessPhotosProvider,
)
from wwai_agent_orchestration.data.providers.models.media_assets import (
    MediaAssetsInput,
    MediaAssetsOutput,
    MediaItem,
    ImageLookup,
)
from wwai_agent_orchestration.data.providers.models.scraped_photos import (
    BusinessPhotosInput,
    BusinessPhotoItem,
)
from wwai_agent_orchestration.data.services.media.defaults import (
    DEFAULT_IMAGE_RETRIEVAL_SOURCES,
    DEFAULT_VIDEO_RETRIEVAL_SOURCES,
)

logger = get_logger(__name__)


class MediaProviderClient:
    """
    Unified client for fetching media from multiple sources.
    
    Sources:
    - Stock media (by business trades)
    - Google Maps business photos (scraped data)
    """
    
    def __init__(self):
        self.media_provider = MediaAssetsProvider()
        self.business_photos_provider = BusinessPhotosProvider()
    
    def get_all_images(
        self, 
        business_id: str,
        retrieval_sources: List[Literal["stock", "generated", "google_maps"]] = None,
    ) -> List[MediaItem]:
        """
        Fetch images from all relevant sources.
        
        Args:
            business_id: Business identifier
            use_source: If True, include Google Maps photos (default True)
            
        Returns:
            Combined list of MediaItems with source tagging
        """
        if retrieval_sources is None:
            retrieval_sources = DEFAULT_IMAGE_RETRIEVAL_SOURCES
        all_items: List[MediaItem] = []
        stock_count = 0
        gmaps_count = 0
        
        # Always fetch stock/generated media.
        # In the media db lookup, we remove google maps as a reteieval source,
        # since it is handled by the business photos provider.
        media_items_from_db = self._fetch_media_assets_from_media_management_db(
            business_id, 
            retrieval_sources
        )
        stock_count = len(media_items_from_db)
        all_items.extend(media_items_from_db)
        
        # Conditionally fetch business photos (Google Maps)
        if "google_maps" in retrieval_sources:
            media_items_from_google_maps = self._fetch_google_maps_business_photos(business_id)
            gmaps_count = len(media_items_from_google_maps)
            all_items.extend(media_items_from_google_maps)
        
        return all_items
    
    def get_all_videos(
        self, 
        business_id: str,
        retrieval_sources: List[Literal["stock", "generated", "google_maps"]] = None,
    ) -> List[MediaItem]:
        """
        Fetch videos from all relevant sources.
        
        Args:
            business_id: Business identifier
            retrieval_sources: List of sources to fetch from: generated, google_maps, stock
            
        Returns:
            List of MediaItem objects
        """
        if retrieval_sources is None:
            retrieval_sources = DEFAULT_VIDEO_RETRIEVAL_SOURCES
        try:
            logger.info(f"Fetching videos for business_id: {business_id}")
            
            input_data = MediaAssetsInput(
                business_id=business_id,
                media_type="video",
                retrieval_sources=retrieval_sources,
                max_results=None,
            )
            
            output: MediaAssetsOutput = self.media_provider.get(input_data)
            
            logger.info(
                f"Retrieved {output.videos_count} videos for {business_id}"
            )
            
            return output.items
            
        except Exception as e:
            logger.error(f"Failed to fetch videos for {business_id}: {e}")
            raise
    
    def _fetch_media_assets_from_media_management_db(
        self, 
        business_id: str,
        retrieval_sources: List[Literal["stock", "generated", "google_maps"]] = None,
    ) -> List[MediaItem]:
        """
        Fetch stock/generated media from MediaAssetsProvider.
        
        Args:
            business_id: Business identifier
            
        Returns:
            List of MediaItem with source='stock'
        """
        if retrieval_sources is None:
            retrieval_sources = DEFAULT_IMAGE_RETRIEVAL_SOURCES
        try:
            logger.debug(f"Fetching stock media for {business_id}")
            
            input_data = MediaAssetsInput(
                business_id=business_id,
                media_type="image",
                retrieval_sources=retrieval_sources,
                max_results=None,
            )
            
            output: MediaAssetsOutput = self.media_provider.get(input_data)
            
            logger.debug(f"Found {output.images_count} stock images")
            
            return output.items
            
        except Exception as e:
            logger.error(f"Failed to fetch stock media for {business_id}: {e}")
            return []
    
    def _fetch_google_maps_business_photos(self, business_id: str) -> List[MediaItem]:
        """
        Fetch Google Maps business photos and convert to MediaItem format.
        
        Args:
            business_id: Business identifier
            
        Returns:
            List of MediaItem with source='google_maps'
        """
        try:
            logger.debug(f"Fetching business photos for {business_id}")
            
            input_data = BusinessPhotosInput(
                business_id=business_id,
                max_results=None,
            )
            
            output = self.business_photos_provider.get(input_data)
            
            if not output.items:
                logger.debug(f"No business photos found for {business_id}")
                return []
            
            # Convert BusinessPhotoItem → MediaItem
            media_items = []
            for photo in output.items:
                media_item = self._business_photo_to_media_item(photo)
                if media_item:
                    media_items.append(media_item)
            
            logger.debug(
                f"Converted {len(media_items)} business photos to MediaItems"
            )
            
            return media_items
            
        except Exception as e:
            logger.error(f"Failed to fetch business photos for {business_id}: {e}")
            return []
    
    def _business_photo_to_media_item(
        self, 
        photo: BusinessPhotoItem
    ) -> MediaItem:
        """
        Convert BusinessPhotoItem to MediaItem for unified processing.
        
        Args:
            photo: BusinessPhotoItem from BusinessPhotosProvider
            
        Returns:
            MediaItem with source='google_maps'
        """
        try:
            # Build ImageLookup from business photo
            lookup = ImageLookup(
                id=f"gmaps://{photo.photo_id}",
                src=photo.url,
                alt=None,  # Google Maps photos don't have alt text
                width=photo.width,
                height=photo.height,
                aspect_ratio=photo.aspect_ratio,
            )
            
            return MediaItem(
                media_id=photo.photo_id,
                media_type="image",
                source="google_maps",  # Key: source tagging for weighted scoring
                lookup_object=lookup,
            )
            
        except Exception as e:
            logger.warning(
                f"Failed to convert business photo {photo.photo_id}: {e}"
            )
            return None