# data_providers/providers/media_assets_provider.py
"""
Media Assets Provider.

Retrieves media (images/videos) from media_management database based on business trades.
"""

from wwai_agent_orchestration.core.observability.logger import get_logger
from typing import Optional, Dict, Any, List
from datetime import datetime

from wwai_agent_orchestration.data.connectors.base_mongo_provider import BaseProvider
from wwai_agent_orchestration.data.providers.models.media_assets import (
    MediaAssetsInput,
    MediaAssetsOutput,
    MediaItem,
    ImageLookup,
    VideoLookup,
    PreviewImage,
    VideoSource,
)
from wwai_agent_orchestration.data.services.media.defaults import (
    DEFAULT_IMAGE_RETRIEVAL_SOURCES,
)

logger = get_logger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

DB_MEDIA = "media_management"
COLLECTION_MEDIA = "media"


# =============================================================================
# PROVIDER
# =============================================================================

class MediaAssetsProvider(BaseProvider):
    """
    Provider for media assets.

    Retrieves images and videos from media_management.media collection
    based on business's assigned trades.
    """

    def get(self, input_data: MediaAssetsInput) -> MediaAssetsOutput:
        """
        Get media assets for a business based on assigned trades.

        Flow:
        1. Lookup business trades from business_types collection
        2. Query media by trade_type (stock media by default)
        3. Apply media_type and max_results filters
        4. Transform to MediaItems and return

        Args:
            input_data: MediaAssetsInput with business_id and optional filters

        Returns:
            MediaAssetsOutput with media items
        """
        business_id = input_data.business_id
        media_type = input_data.media_type
        max_results = input_data.max_results

        # Get source from input, default to "stock"
        retrieval_sources = getattr(
            input_data, 'retrieval_sources', DEFAULT_IMAGE_RETRIEVAL_SOURCES
        )

        logger.info(
            f"Getting trade-based media for business_id: {business_id}, "
            f"media_type: {media_type}, retrieval_sources: {retrieval_sources}, max_results: {max_results}"
        )

        # =====================================================================
        # STEP 1: Get business trades
        # =====================================================================
        trades = self.get_business_trades(business_id)

        if not trades:
            logger.warning(f"No trades found for business_id: {business_id}")
            return MediaAssetsOutput(
                items=[],
                total_count=0,
                images_count=0,
                videos_count=0,
            )

        logger.info(f"Business has {len(trades)} trades: {trades}")

        # =====================================================================
        # STEP 2: Build query
        # =====================================================================
        # Filter out "google_maps" from retrieval_sources since it uses different retrieval logic
        # (handled by BusinessPhotosProvider, not from media_management database)
        db_sources = [s for s in retrieval_sources if s != "google_maps"]

        query = {
            "trade_type": {"$in": trades},
            "source": {"$in": db_sources}
        }

        # Apply media_type filter if not "all"
        if media_type != "all":
            query["media_type"] = media_type

        logger.info(f"Querying media with: {query}")

        # =====================================================================
        # STEP 3: Query media collection
        # =====================================================================
        raw_media = self.find_many(
            DB_MEDIA,
            COLLECTION_MEDIA,
            query,
            limit=max_results,
            sort=[("created_at", -1)]  # Newest first
        )

        if not raw_media:
            logger.info(f"No media found for trades: {trades}")
            return MediaAssetsOutput(
                items=[],
                total_count=0,
                images_count=0,
                videos_count=0,
            )

        logger.info(f"Found {len(raw_media)} raw media documents")

        # =====================================================================
        # STEP 4: Transform to MediaItems
        # =====================================================================
        items = []
        images_count = 0
        videos_count = 0

        for raw in raw_media:
            item = self._transform_media_item(raw)
            if item:
                items.append(item)
                if item.media_type == "image":
                    images_count += 1
                else:
                    videos_count += 1

        logger.info(
            f"Returning {len(items)} media items "
            f"({images_count} images, {videos_count} videos)"
        )

        return MediaAssetsOutput(
            items=items,
            total_count=len(items),
            images_count=images_count,
            videos_count=videos_count,
            last_updated=datetime.utcnow(),
        )

    def _transform_media_item(self, raw: Dict[str, Any]) -> Optional[MediaItem]:
        """Transform raw media document to MediaItem."""
        try:
            media_type = raw.get("media_type")
            source = raw.get("source", "upload")

            # Generate media_id from image/video id or fallback
            media_id = None
            lookup_object = None

            if media_type == "image" and raw.get("image"):
                img = raw["image"]
                media_id = img.get("id") or raw.get("_id")

                lookup_object = ImageLookup(
                    id=img.get("id", f"gid://shopify/MediaImage/{media_id}"),
                    src=img.get("src", ""),
                    alt=img.get("alt"),
                    width=img.get("width"),
                    height=img.get("height"),
                    aspect_ratio=img.get("aspect_ratio"),
                    variations=img.get("variations"),
                )

            elif media_type == "video" and raw.get("video"):
                vid = raw["video"]
                media_id = vid.get("id") or raw.get("_id")

                # Build preview image
                preview_image = None
                if vid.get("preview_image"):
                    pi = vid["preview_image"]
                    preview_image = PreviewImage(
                        url=pi.get("url", ""),
                        width=pi.get("width", 0),
                        height=pi.get("height", 0),
                        alt=pi.get("alt"),
                    )

                # Build sources
                sources = []
                if vid.get("sources"):
                    for src in vid["sources"]:
                        sources.append(VideoSource(
                            format=src.get("format", ""),
                            mime_type=src.get("mime_type", ""),
                            url=src.get("url", ""),
                            width=src.get("width", 0),
                            height=src.get("height", 0),
                        ))

                lookup_object = VideoLookup(
                    id=vid.get("id", f"gid://shopify/Video/{media_id}"),
                    filename=vid.get("filename", ""),
                    alt=vid.get("alt"),
                    aspect_ratio=vid.get("aspect_ratio"),
                    preview_image=preview_image,
                    sources=sources,
                )

            if not lookup_object:
                return None

            return MediaItem(
                media_id=str(media_id),
                media_type=media_type,
                source=source,
                lookup_object=lookup_object,
            )

        except Exception as e:
            logger.error(f"Failed to transform media item: {e}")
            return None
