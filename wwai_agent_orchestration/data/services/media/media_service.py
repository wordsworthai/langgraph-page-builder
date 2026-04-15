"""
Main orchestration service for media matching.

Supports multi-source matching with source-weighted scoring:
- Google Maps business photos
- Stock/Generated media 
"""
from wwai_agent_orchestration.core.observability.logger import get_logger
from typing import List, Dict, Any, Optional

from wwai_agent_orchestration.data.services.models.media import (
    MediaMatchRequest,
    MediaSlot,
    MediaSlotIdentity,
    MediaMatchResponse,
    ImageMatchResult,
    VideoMatchResult,
    VideoMatchResponse,
    MatchMetadata,
    ShopifyImageObject,
    ShopifyVideoObject,
    ShopifyVideoSource
)
from wwai_agent_orchestration.data.services.media.defaults import (
    DEFAULT_IMAGE_RETRIEVAL_SOURCES,
    DEFAULT_VIDEO_RETRIEVAL_SOURCES,
)
from wwai_agent_orchestration.data.services.media.provider_client import MediaProviderClient
from wwai_agent_orchestration.data.services.media.transformer import (
    batch_transform, 
    asset_to_shopify_image,
    asset_to_shopify_video
)
from wwai_agent_orchestration.data.services.media.matcher import MediaAssetMatcher

logger = get_logger(__name__)


class MediaService:
    """
    Service for matching media slots to available assets.
    
    Orchestrates:
    1. Fetch media from providers (stock + optionally Google Maps)
    2. Transform to matcher format
    3. Match slots to assets using source-weighted scoring
    4. Convert back to Shopify format (with optimized variation selection)
    """
    
    def __init__(self):
        self.provider_client = MediaProviderClient()
        self.matcher = MediaAssetMatcher()
    
    def match_images(self, request: MediaMatchRequest) -> MediaMatchResponse:
        """
        Match image slots to available images.
        
        Args:
            request: MediaMatchRequest with business_id, slots
            
        Returns:
            MediaMatchResponse with matched images
        """
        try:            
            logger.info(
                f"Matching {len(request.slots)} image slots for {request.business_id}, "
                f"retrieval_sources={request.retrieval_sources}"
            )
            
            # Step 1: Fetch all images
            media_items = self.provider_client.get_all_images(
                request.business_id,
                retrieval_sources=request.retrieval_sources
            )
            
            if not media_items:
                logger.warning(f"No images found for {request.business_id}")
                return self._empty_image_response(request)
            
            # Step 2: Transform to MediaAssets
            available_assets = batch_transform(media_items)
            
            if not available_assets:
                logger.warning(
                    f"No valid assets after transform for {request.business_id}"
                )
                return self._empty_image_response(request)
            
            # Step 3: Configure matcher and match
            # If more than one retrieval source, we use source weighting
            self.matcher.use_source_weighting = len(request.retrieval_sources) > 1
            self.matcher.reset_used_assets()
            
            required_dimensions = [
                (slot.width, slot.height) for slot in request.slots
            ]
            
            max_per_slot = request.max_recommendations_per_slot
            
            # Use top N matching if max_recommendations_per_slot > 1
            if max_per_slot > 1:
                matched_assets_list = self.matcher.find_top_image_matches(
                    available_assets,
                    required_dimensions,
                    max_per_slot=max_per_slot
                )
                
                # Step 4: Build response with multiple results per slot
                results = []
                matched_count = 0
                
                for slot, matched_assets in zip(request.slots, matched_assets_list):
                    if matched_assets:
                        matched_count += 1
                        # Add all matches for this slot
                        for matched_asset in matched_assets:
                            # Convert to Shopify format with variation selection
                            shopify_image = self._to_shopify_image(
                                matched_asset,
                                slot_width=slot.width,
                                slot_height=slot.height
                            )
                            
                            # Extract match metadata
                            match_metadata = self._extract_metadata(matched_asset)
                            
                            results.append(ImageMatchResult(
                                slot_identity=slot.slot_identity,
                                shopify_image=shopify_image,
                                match_metadata=match_metadata
                            ))
                    else:
                        # No match found for this slot
                        results.append(ImageMatchResult(
                            slot_identity=slot.slot_identity,
                            shopify_image=None,
                            match_metadata=None
                        ))
            else:
                # Original behavior: single match per slot
                matched_assets = self.matcher.find_best_image_matches(
                    available_assets,
                    required_dimensions
                )
                
                # Step 4: Build response
                results = []
                matched_count = 0
                
                for slot, matched_asset in zip(request.slots, matched_assets):
                    if matched_asset:
                        # Convert to Shopify format with variation selection
                        shopify_image = self._to_shopify_image(
                            matched_asset,
                            slot_width=slot.width,
                            slot_height=slot.height
                        )
                        
                        # Extract match metadata
                        match_metadata = self._extract_metadata(matched_asset)
                        
                        results.append(ImageMatchResult(
                            slot_identity=slot.slot_identity,
                            shopify_image=shopify_image,
                            match_metadata=match_metadata
                        ))
                        matched_count += 1
                    else:
                        # No match found
                        results.append(ImageMatchResult(
                            slot_identity=slot.slot_identity,
                            shopify_image=None,
                            match_metadata=None
                        ))
            
            logger.info(
                f"Matched {matched_count}/{len(request.slots)} image slots "
                f"for {request.business_id} (retrieval_sources={request.retrieval_sources})"
            )
            
            return MediaMatchResponse(
                results=results,
                total_slots=len(request.slots),
                matched_count=matched_count,
                unmatched_count=len(request.slots) - matched_count
            )
            
        except Exception as e:
            logger.error(f"Failed to match images for {request.business_id}: {e}")
            raise
    
    def match_videos(self, request: MediaMatchRequest) -> VideoMatchResponse:
        """
        Match video slots to available videos.
        
        Note: Currently only stock videos supported (Google Maps has no video).
        
        Args:
            request: MediaMatchRequest with business_id and slots
            
        Returns:
            VideoMatchResponse with matched videos
        """
        try:            
            logger.info(
                f"Matching {len(request.slots)} video slots for {request.business_id}, "
                f"retrieval_sources={request.retrieval_sources}"
            )
            
            # Step 1: Fetch all videos
            media_items = self.provider_client.get_all_videos(
                request.business_id,
                retrieval_sources=request.retrieval_sources
            )
            
            if not media_items:
                logger.warning(f"No videos found for {request.business_id}")
                return self._empty_video_response(request)
            
            # Step 2: Transform to MediaAssets
            available_assets = batch_transform(media_items)
            
            # Step 3: Configure matcher and match
            # Note: use_source_weighting=False for videos since only stock exists
            self.matcher.use_source_weighting = False
            self.matcher.reset_used_assets()
            
            required_dimensions = [
                (slot.width, slot.height) for slot in request.slots
            ]
            
            max_per_slot = request.max_recommendations_per_slot
            
            # Use top N matching if max_recommendations_per_slot > 1
            if max_per_slot > 1:
                matched_assets_list = self.matcher.find_top_video_matches(
                    available_assets,
                    required_dimensions,
                    max_per_slot=max_per_slot
                )
                
                # Step 4: Build response with multiple results per slot
                results = []
                matched_count = 0
                
                for slot, matched_assets in zip(request.slots, matched_assets_list):
                    if matched_assets:
                        matched_count += 1
                        # Add all matches for this slot
                        for matched_asset in matched_assets:
                            # Convert to Shopify video format
                            shopify_video = self._to_shopify_video(matched_asset)
                            match_metadata = self._extract_metadata(matched_asset)
                            
                            results.append(VideoMatchResult(
                                slot_identity=slot.slot_identity,
                                shopify_video=shopify_video,
                                match_metadata=match_metadata
                            ))
                    else:
                        # No match found for this slot
                        results.append(VideoMatchResult(
                            slot_identity=slot.slot_identity,
                            shopify_video=None,
                            match_metadata=None
                        ))
            else:
                # Original behavior: single match per slot
                matched_assets = []
                for slot in request.slots:
                    matched_asset = self.matcher.find_best_video_match(
                        available_assets,
                        required_dimensions=(slot.width, slot.height)
                    )
                    matched_assets.append(matched_asset)
                
                # Step 4: Build response
                results = []
                matched_count = 0
                
                for slot, matched_asset in zip(request.slots, matched_assets):
                    if matched_asset:
                        # Convert to Shopify video format
                        shopify_video = self._to_shopify_video(matched_asset)
                        match_metadata = self._extract_metadata(matched_asset)
                        
                        results.append(VideoMatchResult(
                            slot_identity=slot.slot_identity,
                            shopify_video=shopify_video,
                            match_metadata=match_metadata
                        ))
                        matched_count += 1
                    else:
                        results.append(VideoMatchResult(
                            slot_identity=slot.slot_identity,
                            shopify_video=None,
                            match_metadata=None
                        ))
            
            logger.info(
                f"Matched {matched_count}/{len(request.slots)} video slots "
                f"for {request.business_id}"
            )
            
            return VideoMatchResponse(
                results=results,
                total_slots=len(request.slots),
                matched_count=matched_count,
                unmatched_count=len(request.slots) - matched_count
            )
            
        except Exception as e:
            logger.error(f"Failed to match videos for {request.business_id}: {e}")
            raise

    def match_images_for_slots(
        self,
        business_id: str,
        slots: List[Dict[str, Any]],
        retrieval_sources: Optional[List[str]] = None,
        max_recommendations_per_slot: int = 1,
    ) -> Dict[str, Any]:
        """
        Dict-facing facade to avoid external callers importing service models.
        """
        request = MediaMatchRequest(
            business_id=business_id,
            retrieval_sources=retrieval_sources or DEFAULT_IMAGE_RETRIEVAL_SOURCES,
            slots=self._build_slots_from_dicts(slots),
            max_recommendations_per_slot=max_recommendations_per_slot,
        )
        return self.match_images(request).model_dump()

    def match_videos_for_slots(
        self,
        business_id: str,
        slots: List[Dict[str, Any]],
        retrieval_sources: Optional[List[str]] = None,
        max_recommendations_per_slot: int = 1,
    ) -> Dict[str, Any]:
        """
        Dict-facing facade to avoid external callers importing service models.
        """
        request = MediaMatchRequest(
            business_id=business_id,
            retrieval_sources=retrieval_sources or DEFAULT_VIDEO_RETRIEVAL_SOURCES,
            slots=self._build_slots_from_dicts(slots),
            max_recommendations_per_slot=max_recommendations_per_slot,
        )
        return self.match_videos(request).model_dump()
    
    def _empty_image_response(self, request: MediaMatchRequest) -> MediaMatchResponse:
        """Build response when no images available."""
        results = [
            ImageMatchResult(
                slot_identity=slot.slot_identity, 
                shopify_image=None, 
                match_metadata=None
            )
            for slot in request.slots
        ]
        
        return MediaMatchResponse(
            results=results,
            total_slots=len(request.slots),
            matched_count=0,
            unmatched_count=len(request.slots)
        )
    
    def _empty_video_response(self, request: MediaMatchRequest) -> VideoMatchResponse:
        """Build response when no videos available."""
        results = [
            VideoMatchResult(
                slot_identity=slot.slot_identity,
                shopify_video=None,
                match_metadata=None
            )
            for slot in request.slots
        ]
        
        return VideoMatchResponse(
            results=results,
            total_slots=len(request.slots),
            matched_count=0,
            unmatched_count=len(request.slots)
        )

    def _build_slots_from_dicts(self, slots: List[Dict[str, Any]]) -> List[MediaSlot]:
        """Build MediaSlot models from dict payloads."""
        parsed_slots = []
        for slot in slots:
            identity_dict = slot.get("slot_identity") or {}
            slot_identity = MediaSlotIdentity(
                element_id=identity_dict.get("element_id"),
                block_type=identity_dict.get("block_type"),
                block_index=identity_dict.get("block_index"),
                section_id=identity_dict.get("section_id"),
            )
            parsed_slots.append(
                MediaSlot(
                    width=slot["width"],
                    height=slot["height"],
                    slot_identity=slot_identity,
                )
            )
        return parsed_slots
    
    # =========================================================================
    # VARIATION SELECTION
    # =========================================================================
    
    def _select_best_variation(
        self,
        variations: Dict[str, Any],
        slot_width: int,
        slot_height: int
    ) -> Optional[Dict[str, Any]]:
        """
        Select smallest variation that covers both slot dimensions.
        
        Args:
            variations: Dict of variation data (keyed by index "0", "1", etc.)
            slot_width: Required slot width
            slot_height: Required slot height
            
        Returns:
            Best variation dict, or None if no variation large enough (use original)
        """
        # Filter variations that cover both dimensions
        candidates = [
            v for v in variations.values()
            if isinstance(v, dict) 
            and v.get("width", 0) >= slot_width 
            and v.get("height", 0) >= slot_height
        ]
        
        if not candidates:
            return None
        
        # Return smallest that fits (minimize file size / bandwidth)
        return min(candidates, key=lambda v: v.get("width", 0) * v.get("height", 0))
    
    # =========================================================================
    # SHOPIFY CONVERSION
    # =========================================================================
    
    def _to_shopify_image(
        self, 
        asset,
        slot_width: Optional[int] = None,
        slot_height: Optional[int] = None
    ) -> ShopifyImageObject:
        """
        Convert MediaAsset to ShopifyImageObject.
        
        If slot dimensions provided and variations exist, selects the 
        smallest variation that covers the slot dimensions.
        """
        shopify_dict = asset_to_shopify_image(asset)
        
        # Default to original
        src = shopify_dict["src"]
        width = shopify_dict["width"]
        height = shopify_dict["height"]
        
        # Select best variation if available
        variations = shopify_dict.get("variations")
        if slot_width and slot_height and variations:
            best = self._select_best_variation(variations, slot_width, slot_height)
            if best:
                src = best["src"]
                width = best["width"]
                height = best["height"]
                logger.debug(
                    f"Selected variation {width}x{height} for slot {slot_width}x{slot_height}"
                )
        
        return ShopifyImageObject(
            id=shopify_dict["id"],
            src=src,
            alt=shopify_dict.get("alt"),
            width=width,
            height=height,
            aspect_ratio=shopify_dict.get(
                "aspect_ratio", 
                width / height if height else 1.0
            )
        )
    
    def _to_shopify_video(self, asset) -> ShopifyVideoObject:
        """Convert MediaAsset to ShopifyVideoObject."""
        video_dict = asset_to_shopify_video(asset)

        # Convert preview_image if present
        preview_image = None
        if video_dict.get("preview_image"):
            pi = video_dict["preview_image"]
            preview_image = ShopifyImageObject(
                id=video_dict["id"],
                src=pi["url"],
                alt=pi.get("alt"),
                width=pi["width"],
                height=pi["height"],
                aspect_ratio=pi.get("aspect_ratio", pi["width"] / pi["height"])
            )
        
        # Convert sources
        sources = [
            ShopifyVideoSource(
                format=src["format"],
                mime_type=src["mime_type"],
                url=src["url"],
                width=src["width"],
                height=src["height"]
            )
            for src in video_dict.get("sources", [])
        ]
        
        return ShopifyVideoObject(
            id=video_dict["id"],
            filename=video_dict["filename"],
            alt=video_dict.get("alt"),
            aspect_ratio=video_dict.get("aspect_ratio", 1.0),
            preview_image=preview_image,
            sources=sources
        )
    
    def _extract_metadata(self, asset) -> MatchMetadata:
        """Extract match metadata from asset."""
        return MatchMetadata(
            fit_score=asset.meta.get("fit_score", 0.0),
            source=asset.meta.get("source", "unknown"),
            source_bonus=asset.meta.get("source_bonus", 0.0),
            dimension_score=asset.meta.get("dimension_score", 0.0),
            quality_tier=asset.meta.get("quality_tier", "unknown"),
            match_type=asset.meta.get("match_type", "unknown"),
            match_reason=asset.meta.get("match_reason", ""),
            match_explanation=asset.meta.get("match_explanation", "")
        )


# Singleton instance for easy import
media_service = MediaService()