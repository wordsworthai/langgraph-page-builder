"""
Media Service for handling file uploads to S3 and MongoDB.
"""
import asyncio
import functools
import logging
import os
import tempfile
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List
import uuid

import httpx
from bson import ObjectId
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import Depends, HTTPException, Request, UploadFile
from motor.motor_asyncio import AsyncIOMotorCollection

from app.products.page_builder.config.aws import aws_config
from app.core.db_mongo import get_mongo_collection
from app.shared.schemas.auth.auth import CurrentUserResponse
from app.shared.services.auth.users_service import get_current_user_optional
from app.products.page_builder.utils.media.media_utils import (
    validate_file_type,
    validate_file_size,
    extract_image_metadata,
    extract_video_metadata,
    generate_video_thumbnail,
    generate_unique_id,
    sanitize_text,
    parse_tags,
    MediaValidationError,
    MediaProcessingError,
)
from app.products.page_builder.utils.media.upload_utils.upload_to_s3 import (
    get_s3_client,
    generate_s3_url,
)

logger = logging.getLogger(__name__)


class MediaService:
    """Service for media upload operations."""
    
    def __init__(
        self,
        current_user: Optional[CurrentUserResponse],
        request: Request,
    ):
        self.current_user = current_user
        self.request = request
        
        # Use existing S3 client utility
        self.s3_client, error = get_s3_client()
        if error:
            raise HTTPException(status_code=500, detail=f"Failed to initialize S3 client: {error}")
        
        self.bucket_name = aws_config.S3_MEDIA_BUCKET_NAME
    
    async def _run_in_thread(self, func, *args, **kwargs):
        """Run synchronous function in thread pool."""
        loop = asyncio.get_event_loop()
        partial_func = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, partial_func)

    def _select_best_preview_asset(self, assets: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Select the best available preview asset in priority order:
        preview_1500 > preview_1000 > preview_600 || highest preview_{number}.
        Returns the asset dict including its key under 'key' if found.
        """
        if not assets:
            return None

        candidates = []
        for key, asset in assets.items():
            if key.startswith("preview_"):
                suffix = key.replace("preview_", "")
                if suffix.isdigit() and asset.get("url"):
                    candidates.append((int(suffix), key, asset))
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            _, key, asset = candidates[0]
            return {**asset, "key": key}
        return None
    
    async def _get_media_collection(self) -> AsyncIOMotorCollection:
        """Get the media MongoDB collection from media_management database."""
        return await get_mongo_collection("media", "media_management")

    async def _get_business_type_collection(self) -> AsyncIOMotorCollection:
        """Get the business_type collection from businesses database."""
        return await get_mongo_collection("business_types", "businesses")

    
    def _construct_s3_url(self, s3_key: str) -> str:
        """Construct direct S3 URL using existing utility."""
        return generate_s3_url(s3_key, bucket_name=self.bucket_name)
    
    def _build_autopopulation_metadata(
        self,
        width: int,
        height: int,
        extension: str,
        tags: list,
    ) -> dict:
        """Create the autopopulation metadata block used across media types."""
        return {
            "media_extension": extension,
            "width": width,
            "height": height,
            "media_tags": tags,
        }

    def _build_media_document(
        self,
        *,
        source: str,
        media_type: str,
        size: int,
        media_payload: dict,
        autopopulation_metadata: dict,
        business_id: Optional[str] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """Assemble a media document with shared fields and timestamps."""
        now = datetime.now()
        document = {
            "source": source,
            "media_type": media_type,
            "size": size,
            "autopopulation_metadata": autopopulation_metadata,
            "created_at": now,
            "updated_at": now,
            **media_payload,
        }
        if business_id:
            document["business_id"] = business_id
        if extra_fields:
            document.update(extra_fields)
        return document

    async def _insert_media_and_format_response(
        self,
        document: dict,
        success_message: str,
    ) -> dict:
        """Persist a media document and format the API response."""
        collection = await self._get_media_collection()
        result = await collection.insert_one(document)
        response_document = self._format_media_document(
            {**document, "_id": result.inserted_id}
        )
        return {
            "success": True,
            "message": success_message,
            "media": response_document,
        }

    def _build_image_asset_path(
        self,
        unique_id: str,
        extension: str,
        business_id: Optional[str],
        stock_provider: str = "shutterstock",
    ) -> str:
        """Derive the S3 path for an image (upload or stock)."""
        if business_id:
            return f"{business_id}/images/{unique_id}.{extension}"
        return f"stock/{stock_provider}/{unique_id}.{extension}"

    def _build_video_asset_paths(
        self,
        business_id: Optional[str],
        unique_id: str,
        extension: str,
        stock_provider: str = "shutterstock",
    ) -> Tuple[str, str]:
        """Derive S3 paths for a video file and its thumbnail."""
        if business_id:
            video_asset_path = f"{business_id}/videos/{unique_id}.{extension}"
            thumbnail_asset_path = f"{business_id}/videos/thumbnails/{unique_id}_thumb.jpg"
        else:
            video_asset_path = f"stock/{stock_provider}/{unique_id}.{extension}"
            thumbnail_asset_path = f"stock/{stock_provider}/{unique_id}_thumb.jpg"
        return video_asset_path, thumbnail_asset_path
    
    async def upload_to_s3(
        self, 
        file_bytes: bytes, 
        s3_key: str, 
        content_type: str
    ) -> str:
        """
        Upload file bytes to S3.
        Returns:
            S3 URL of uploaded file
        """
        try:
            await self._run_in_thread(
                self.s3_client.put_object,
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_bytes,
                ContentType=content_type,
            )
            return self._construct_s3_url(s3_key)
        except (ClientError, NoCredentialsError) as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload to S3: {str(e)}"
            )
    
    async def delete_from_s3(self, s3_key: str) -> None:
        """
        Delete file from S3.
        
        Args:
            s3_key: The S3 key (path) of the file to delete
        """
        try:
            await self._run_in_thread(
                self.s3_client.delete_object,
                Bucket=self.bucket_name,
                Key=s3_key,
            )
        except (ClientError, NoCredentialsError) as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete from S3: {str(e)}"
            )
    
    async def upload_media(
        self,
        file: UploadFile,
        business_id: str,
        alt: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> dict:
        """
        Process and upload media file.
        
        Args:
            file: Uploaded file
            business_id: Business ID (required)
            alt: Alt text for accessibility
            tags: Comma-separated tags
            
        Returns:
            dict with success status, message, and media document
        """
        # Read file bytes
        file_bytes = await file.read()
        
        if not file_bytes:
            raise HTTPException(status_code=400, detail="No file content provided")
        
        try:
            # Step 1: Validate file type (magic bytes)
            mime_type, extension, media_type = validate_file_type(
                file_bytes, 
                filename=file.filename
            )
            
            # Step 2: Validate file size
            validate_file_size(file_bytes, media_type)
            
            # Step 3: Generate unique ID and paths
            unique_id = generate_unique_id()
            
            # Sanitize inputs
            sanitized_alt = sanitize_text(alt)
            parsed_tags = parse_tags(tags)
            
            # Step 4: Process based on media type
            if media_type == "image":
                return await self._process_image_upload(
                    file_bytes=file_bytes,
                    business_id=business_id,
                    unique_id=unique_id,
                    mime_type=mime_type,
                    extension=extension,
                    original_filename=file.filename,
                    alt=sanitized_alt,
                    tags=parsed_tags,
                )
            else:
                return await self._process_video_upload(
                    file_bytes=file_bytes,
                    business_id=business_id,
                    unique_id=unique_id,
                    mime_type=mime_type,
                    extension=extension,
                    original_filename=file.filename,
                    alt=sanitized_alt,
                    tags=parsed_tags,
                )
                
        except MediaValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except MediaProcessingError as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _process_image_upload(
        self,
        file_bytes: bytes,
        business_id: str,
        unique_id: str,
        mime_type: str,
        extension: str,
        original_filename: Optional[str],
        alt: Optional[str],
        tags: list,
    ) -> dict:
        """Process and upload an image file."""
        
        # Extract metadata
        metadata = await self._run_in_thread(extract_image_metadata, file_bytes)
        
        # Construct S3 path
        asset_path = self._build_image_asset_path(unique_id, extension, business_id)
        
        # Upload to S3
        cdn_url = await self.upload_to_s3(file_bytes, asset_path, mime_type)
        
        autopop_metadata = self._build_autopopulation_metadata(
            width=metadata["width"],
            height=metadata["height"],
            extension=extension,
            tags=tags,
        )
        
        document = self._build_media_document(
            source="upload",
            media_type="image",
            size=len(file_bytes),
            media_payload={
                "image": {
                    "src": cdn_url,
                    "asset_path": asset_path,
                    "filename": original_filename,
                    "width": metadata["width"],
                    "height": metadata["height"],
                    "aspect_ratio": metadata["aspect_ratio"],
                    "alt": alt,
                    "id": unique_id,
                }
            },
            autopopulation_metadata=autopop_metadata,
            business_id=business_id,
        )
        
        return await self._insert_media_and_format_response(
            document, "Image uploaded successfully"
        )

    async def _process_stock_image_upload(
        self,
        file_bytes: bytes,
        business_id: Optional[str],
        unique_id: str,
        mime_type: str,
        extension: str,
        original_filename: Optional[str],
        alt: Optional[str],
        tags: list,
        width: int,
        height: int,
        aspect_ratio: float,
        size: int,
        stock_media_id: str,
        search_query: str,
        stock_provider: str = "shutterstock",
        trade_type: Optional[str] = None,
    ) -> dict:
        """Process and upload a stock image file with pre-known metadata."""

        # Construct S3 path (include business_id if provided)
        asset_path = self._build_image_asset_path(
            unique_id, extension, business_id, stock_provider=stock_provider
        )

        # Upload to S3
        cdn_url = await self.upload_to_s3(file_bytes, asset_path, mime_type)

        autopop_metadata = self._build_autopopulation_metadata(
            width=width,
            height=height,
            extension=extension,
            tags=tags,
        )

        document = self._build_media_document(
            source="stock",
            media_type="image",
            size=size,
            media_payload={
                "image": {
                    "src": cdn_url,
                    "asset_path": asset_path,
                    "filename": original_filename,
                    "width": width,
                    "height": height,
                    "aspect_ratio": aspect_ratio,
                    "alt": alt,
                    "id": unique_id,
                }
            },
            autopopulation_metadata=autopop_metadata,
            business_id=business_id,
            extra_fields={
                "trade_type": trade_type or "",
                "trade_type_search_query": search_query,
                "stock_media_id": stock_media_id,
            },
        )

        return await self._insert_media_and_format_response(
            document, "Stock image ingested successfully"
        )
    
    async def _process_stock_video_upload(
        self,
        video_bytes: bytes,
        thumbnail_bytes: bytes,
        business_id: Optional[str],
        unique_id: str,
        mime_type: str,
        extension: str,
        original_filename: Optional[str],
        alt: Optional[str],
        tags: list,
        width: Optional[int],
        height: Optional[int],
        aspect_ratio: float,
        size: int,
        stock_media_id: str,
        search_query: str,
        stock_provider: str = "shutterstock",
        thumbnail_mime_type: str = "image/jpeg",
        thumbnail_width: Optional[int] = None,
        thumbnail_height: Optional[int] = None,
        trade_type: Optional[str] = None,
    ) -> dict:
        """Process and upload a stock video preview plus thumbnail."""

        video_asset_path, thumbnail_asset_path = self._build_video_asset_paths(
            business_id, unique_id, extension, stock_provider=stock_provider
        )

        # Upload preview video
        video_cdn_url = await self.upload_to_s3(video_bytes, video_asset_path, mime_type)

        # Upload thumbnail
        thumbnail_cdn_url = await self.upload_to_s3(
            thumbnail_bytes, thumbnail_asset_path, thumbnail_mime_type
        )

        autopop_metadata = self._build_autopopulation_metadata(
            width=width or 0,
            height=height or 0,
            extension=extension,
            tags=tags,
        )

        document = self._build_media_document(
            source="stock",
            media_type="video",
            size=size,
            media_payload={
                "video": {
                    "asset_path": video_asset_path,
                    "filename": original_filename,
                    "aspect_ratio": aspect_ratio,
                    "alt": alt,
                    "id": unique_id,
                    "preview_image": {
                        "url": thumbnail_cdn_url,
                        "width": thumbnail_width,
                        "height": thumbnail_height,
                    },
                    "sources": [
                        {
                            "format": extension,
                            "mime_type": mime_type,
                            "url": video_cdn_url,
                            "width": width,
                            "height": height,
                        }
                    ],
                }
            },
            autopopulation_metadata=autopop_metadata,
            business_id=business_id,
            extra_fields={
                 "trade_type": trade_type or "",
                "trade_type_search_query": search_query,
                "stock_media_id": stock_media_id,
            },
        )

        return await self._insert_media_and_format_response(
            document, "Stock video ingested successfully"
        )
    
    async def _process_video_upload(
        self,
        file_bytes: bytes,
        business_id: str,
        unique_id: str,
        mime_type: str,
        extension: str,
        original_filename: Optional[str],
        alt: Optional[str],
        tags: list,
    ) -> dict:
        """Process and upload a video file with thumbnail generation."""
        
        # Create temporary files for video processing
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, f"{unique_id}.{extension}")
            thumbnail_path = os.path.join(temp_dir, f"{unique_id}_thumb.jpg")
            
            # Write video to temp file
            with open(video_path, 'wb') as f:
                f.write(file_bytes)
            
            # Extract video metadata
            metadata = await self._run_in_thread(extract_video_metadata, video_path)
            
            # Generate thumbnail
            thumbnail_metadata = await self._run_in_thread(
                generate_video_thumbnail, 
                video_path, 
                thumbnail_path
            )
            
            # Construct S3 paths
            video_asset_path, thumbnail_asset_path = self._build_video_asset_paths(
                business_id, unique_id, extension
            )
            
            # Upload video to S3
            video_cdn_url = await self.upload_to_s3(file_bytes, video_asset_path, mime_type)
            
            # Upload thumbnail to S3
            with open(thumbnail_path, 'rb') as f:
                thumbnail_bytes = f.read()
            thumbnail_cdn_url = await self.upload_to_s3(
                thumbnail_bytes, 
                thumbnail_asset_path, 
                "image/jpeg"
            )
        
        autopop_metadata = self._build_autopopulation_metadata(
            width=metadata["width"],
            height=metadata["height"],
            extension=extension,
            tags=tags,
        )

        document = self._build_media_document(
            source="upload",
            media_type="video",
            size=len(file_bytes),
            media_payload={
                "video": {
                    "asset_path": video_asset_path,
                    "filename": original_filename,
                    "aspect_ratio": metadata["aspect_ratio"],
                    "alt": alt,
                    "id": unique_id,
                    "preview_image": {
                        "url": thumbnail_cdn_url,
                        "width": thumbnail_metadata["width"],
                        "height": thumbnail_metadata["height"],
                    },
                    "sources": [
                        {
                            "format": extension,
                            "mime_type": mime_type,
                            "url": video_cdn_url,
                            "width": metadata["width"],
                            "height": metadata["height"],
                        }
                    ],
                }
            },
            autopopulation_metadata=autopop_metadata,
            business_id=business_id,
        )

        return await self._insert_media_and_format_response(
            document, "Video uploaded successfully"
        )
    
    def _format_media_document(self, doc: dict) -> dict:
        """Format a media document for API response (convert ObjectId and datetime)."""
        formatted = {**doc}
        # Convert ObjectId to string
        if "_id" in formatted:
            formatted["_id"] = str(formatted["_id"])
        # Convert datetime fields to ISO format
        if "created_at" in formatted and hasattr(formatted["created_at"], "isoformat"):
            formatted["created_at"] = formatted["created_at"].isoformat()
        if "updated_at" in formatted and hasattr(formatted["updated_at"], "isoformat"):
            formatted["updated_at"] = formatted["updated_at"].isoformat()
        return formatted
    
    async def get_media_overview(self, business_id: str) -> dict:
        """
        Fetch 6 most recent media items for a business.
        
        Args:
            business_id: Business ID to fetch media for
            
        Returns:
            dict with success status, media list, and total count
        """
        collection = await self._get_media_collection()
        
        # Fetch 6 most recent media items
        cursor = collection.find({"business_id": business_id}).sort("created_at", -1).limit(6)
        media_list = await cursor.to_list(length=6)
        
        # Get total count for the business
        total_count = await collection.count_documents({"business_id": business_id})
        
        # Format documents for response
        formatted_media = [self._format_media_document(doc) for doc in media_list]
        
        return {
            "success": True,
            "media": formatted_media,
            "total_count": total_count
        }
    
    async def get_media_details(self, business_id: str) -> dict:
        """
        Fetch all media items for a business.
        
        Args:
            business_id: Business ID to fetch media for
            
        Returns:
            dict with success status, media list, and total count
        """
        collection = await self._get_media_collection()
        
        # Fetch all media items for the business
        cursor = collection.find({"business_id": business_id}).sort("created_at", -1)
        media_list = await cursor.to_list(length=None)
        
        # Format documents for response
        formatted_media = [self._format_media_document(doc) for doc in media_list]
        
        return {
            "success": True,
            "media": formatted_media,
            "total_count": len(formatted_media)
        }

    async def get_recommended_media(
        self,
        business_id: str,
        media_type: Optional[str] = None,
        max_results: int = 50
    ) -> dict:
        """
        Fetch recommended media based on business's assigned trades.
        
        Flow:
        1. Get business trades from business_type collection
        2. Query media with trade_type + source="generated"
        
        Args:
            business_id: Business ID to fetch trades for
            media_type: Optional filter - "image", "video", or None for all
            max_results: Maximum number of results
            
        Returns:
            dict with success status, media list, and counts
        """
        # Step 1: Get business trades
        business_type_collection = await self._get_business_type_collection()
        business_doc = await business_type_collection.find_one({"business_id": business_id})
        
        if not business_doc:
            return {
                "success": True,
                "media": [],
                "total_count": 0,
                "message": "No trade information found for this business"
            }
        
        # Extract trade names from assigned_trades array
        assigned_trades = business_doc.get("assigned_trades", [])
        trades = [t.get("trade") for t in assigned_trades if t.get("trade")]
        
        if not trades:
            return {
                "success": True,
                "media": [],
                "total_count": 0,
                "message": "No trades assigned to this business"
            }
        
        # Step 2: Build query
        # Apply source filtering based on media_type:
        # - Videos: include both "generated" and "stock"
        # - Images: only "generated"
        # - None (all): include both "generated" and "stock" to get all media types
        if media_type == "video":
            source_filter = {"$in": ["generated", "stock"]}
        elif media_type == "image":
            # For images, only use "generated" (images don't come from stock in recommended)
            source_filter = "generated"
        else:
            # For None (all media types), include both "generated" and "stock" to get images + videos
            source_filter = {"$in": ["generated", "stock"]}
        
        # Build query with trade_type filter
        # For stock videos, also include those without trade_type (generic stock)
        # For generated media, require matching trade_type
        if isinstance(source_filter, dict) and "stock" in source_filter.get("$in", []):
            # When including stock, use OR to get:
            # 1. Generated media with matching trade_type (images + videos)
            # 2. Stock videos with matching trade_type (only videos, not images)
            # 3. Stock videos without trade_type (generic stock videos)
            or_conditions = [
                # Generated media with matching trade_type (both images and videos)
                {
                    "trade_type": {"$in": trades},
                    "source": "generated"
                },
                # Stock videos with matching trade_type (only videos, stock images are not in recommended)
                {
                    "trade_type": {"$in": trades},
                    "source": "stock",
                    "media_type": "video"
                },
            ]
            
            # Add stock videos without trade_type (generic stock - available to all)
            # Flatten the nested $or into separate conditions to avoid MongoDB query issues
            or_conditions.extend([
                {
                    "source": "stock",
                    "media_type": "video",
                    "trade_type": {"$exists": False}
                },
                {
                    "source": "stock",
                    "media_type": "video",
                    "trade_type": ""
                },
                {
                    "source": "stock",
                    "media_type": "video",
                    "trade_type": None
                }
            ])
            
            query = {"$or": or_conditions}
        else:
            # For images or when only "generated" source, require matching trade_type
            query = {
                "trade_type": {"$in": trades},
                "source": source_filter
            }
        
        if media_type and media_type != "all":
            # Add media_type filter
            if "$or" in query:
                # Add media_type to all OR conditions (skip if already present to avoid overwriting)
                for condition in query["$or"]:
                    if "media_type" not in condition:
                        condition["media_type"] = media_type
            else:
                query["media_type"] = media_type
        
        # Step 3: Query media collection
        media_collection = await self._get_media_collection()
        
        if "$or" in query:
            # For $or queries, use expanded limit to ensure we get all results including videos
            # Then sort and return - frontend can filter by type if needed
            expanded_limit = max(max_results * 3, 200)  # Get at least 3x the requested amount or 200, whichever is larger
            cursor = media_collection.find(query).sort("created_at", -1).limit(expanded_limit)
            all_docs = await cursor.to_list(length=expanded_limit)
            
            # Remove duplicates (in case a document matches multiple conditions)
            seen_ids = set()
            unique_docs = []
            for doc in all_docs:
                doc_id = str(doc.get("_id"))
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    unique_docs.append(doc)
            
            # Sort by created_at descending (handle None/missing dates)
            def get_sort_key(doc):
                created_at = doc.get("created_at")
                if created_at is None:
                    return datetime.min
                return created_at
            unique_docs.sort(key=get_sort_key, reverse=True)
            
            # Return all unique results (not limited) so videos are included
            # Frontend can filter by type and paginate if needed
            media_list = unique_docs
            logger.info(f"[get_recommended_media] Found {len(unique_docs)} unique results, returning all")
        else:
            # For simple queries (images only), use the original approach
            cursor = media_collection.find(query).sort("created_at", -1).limit(max_results)
            media_list = await cursor.to_list(length=max_results)
        
        # Format documents for response
        formatted_media = [self._format_media_document(doc) for doc in media_list]
        
        # Log summary
        media_type_counts = {}
        for item in formatted_media:
            item_type = item.get("media_type", "unknown")
            media_type_counts[item_type] = media_type_counts.get(item_type, 0) + 1
        logger.info(f"[get_recommended_media] Returning {len(formatted_media)} media items: {media_type_counts}")
        
        return {
            "success": True,
            "media": formatted_media,
            "total_count": len(formatted_media),
            "trades": trades
        }

    async def get_business_images(self, business_id: str) -> dict:
        """
        Fetch business images from three sources:
        - Logo images (LogoProvider)
        - Review photos (ReviewPhotosProvider)
        - Google Photos (BusinessPhotosProvider)
        
        Args:
            business_id: Business ID to fetch images for
            
        Returns:
            dict with logo, reviews, and google_photos arrays
        """
        from wwai_agent_orchestration.data.providers.logo_provider import LogoProvider
        from wwai_agent_orchestration.data.providers.review_photos_provider import ReviewPhotosProvider
        from wwai_agent_orchestration.data.providers.business_photos_provider import BusinessPhotosProvider
        from wwai_agent_orchestration.data.providers.models.logo import LogoInput
        from wwai_agent_orchestration.data.providers.models.scraped_photos import (
            ReviewPhotosInput,
            BusinessPhotosInput
        )
        from datetime import datetime
        
        logo_provider = LogoProvider()
        review_photos_provider = ReviewPhotosProvider()
        business_photos_provider = BusinessPhotosProvider()
        
        # Fetch logo images
        logo_items = []
        try:
            logo_input = LogoInput(business_id=business_id)
            logo_output = logo_provider.get(logo_input)
            
            if logo_output.has_logo and logo_output.all_logos:
                for logo in logo_output.all_logos:
                    logo_items.append({
                        "_id": f"logo_{logo.logo_id}",
                        "business_id": business_id,
                        "source": "logo",
                        "media_type": "image",
                        "size": 0,
                        "image": {
                            "src": logo.url,
                            "asset_path": logo.url,
                            "filename": f"logo_{logo.trade_type}.png",
                            "id": logo.logo_id,
                            "width": logo.width,
                            "height": logo.height,
                            "aspect_ratio": logo.aspect_ratio,
                            "alt": f"Logo for {logo.trade_type}",
                        },
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat(),
                    })
        except Exception as e:
            # Log error but continue with other sources
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to fetch logo images for {business_id}: {e}")
        
        # Fetch review photos
        review_items = []
        try:
            review_input = ReviewPhotosInput(business_id=business_id, max_results=None)
            review_output = review_photos_provider.get(review_input)
            
            if review_output.items:
                for review_photo in review_output.items:
                    # Review photos may not have dimensions, use defaults
                    review_items.append({
                        "_id": f"review_{review_photo.photo_id}",
                        "business_id": business_id,
                        "source": "review_photo",
                        "media_type": "image",
                        "size": 0,
                        "image": {
                            "src": review_photo.url,
                            "asset_path": review_photo.url,
                            "filename": f"review_photo_{review_photo.photo_id}.jpg",
                            "id": review_photo.photo_id,
                            "width": None,  # Review photos may not have dimensions
                            "height": None,
                            "aspect_ratio": None,
                            "alt": f"Review photo from {review_photo.reviewer_name or 'customer'}",
                        },
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat(),
                    })
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to fetch review photos for {business_id}: {e}")
        
        # Fetch Google Photos
        google_photo_items = []
        try:
            business_photos_input = BusinessPhotosInput(business_id=business_id, max_results=None)
            business_photos_output = business_photos_provider.get(business_photos_input)
            
            if business_photos_output.items:
                for photo in business_photos_output.items:
                    google_photo_items.append({
                        "_id": f"google_photo_{photo.photo_id}",
                        "business_id": business_id,
                        "source": "google_photo",
                        "media_type": "image",
                        "size": 0,
                        "image": {
                            "src": photo.url,
                            "asset_path": photo.url,
                            "filename": f"google_photo_{photo.photo_id}.jpg",
                            "id": photo.photo_id,
                            "width": photo.width,
                            "height": photo.height,
                            "aspect_ratio": photo.aspect_ratio,
                            "alt": "Google Maps business photo",
                        },
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat(),
                    })
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to fetch Google photos for {business_id}: {e}")
        
        return {
            "success": True,
            "logo": logo_items,
            "reviews": review_items,
            "google_photos": google_photo_items,
        }

    async def ingest_stock_image(
        self,
        image_id: str,
        search_query: str,
        business_id: Optional[str],
        shutterstock_service,
        trade_type: Optional[str] = None,
    ) -> dict:
        """
        Ingest a Shutterstock stock image:
        - fetch image details
        - pick best preview asset (1500 > 1000 > 600 || highest preview_{n})
        - download and upload to S3
        - create stock_media and media documents
        """
        if not search_query or not search_query.strip():
            raise HTTPException(status_code=400, detail="search_query is required")

        # Fetch details from Shutterstock
        details = await shutterstock_service.get_image_details(
            image_id=image_id
        )

        assets = details.get("assets", {}) or {}
        best_asset = self._select_best_preview_asset(assets)
        if not best_asset or not best_asset.get("url"):
            raise HTTPException(
                status_code=502,
                detail="No downloadable preview asset available for this stock image",
            )

        asset_url = best_asset["url"]
        width = best_asset.get("width")
        height = best_asset.get("height")

        aspect_ratio = details.get("aspect")
        if aspect_ratio is None:
            if height and height != 0 and width:
                aspect_ratio = round(width / height, 4)
            else:
                aspect_ratio = 1.0

        # Download the chosen preview asset
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(asset_url, timeout=30.0, follow_redirects=True)
                response.raise_for_status()
                file_bytes = response.content
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to download preview asset: {e.response.status_code}",
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to download preview asset: {str(e)}",
            )

        # Detect mime/extension from bytes; fallback to Shutterstock format
        mime_type = "image/jpeg"
        extension = "jpg"
        try:
            detected_mime, detected_ext, detected_media_type = validate_file_type(
                file_bytes, filename=asset_url
            )
            if detected_media_type != "image":
                raise MediaValidationError("Preview asset is not an image")
            mime_type = detected_mime
            extension = detected_ext
        except MediaValidationError:
            huge_fmt = assets.get("huge_jpg", {}).get("format")
            if huge_fmt:
                extension = huge_fmt
                mime_type = f"image/{huge_fmt}"

        # Compute size
        size = assets.get("huge_jpg", {}).get("file_size") or len(file_bytes) or 0

        description = details.get("description")
        keywords = details.get("keywords") or []
        if not isinstance(keywords, list):
            keywords = []

        # Insert stock_media document
        query_hash = hashlib.sha256(search_query.encode("utf-8")).hexdigest()
        now = datetime.now()
        stock_doc = {
            "id": image_id,
            "stock_provider": "shutterstock",
            "search_query": search_query,
            "query_hash": query_hash,
            "api_response": details,
            "created_at": now,
            "updated_at": now,
        }
        stock_collection = await get_mongo_collection("stock_media", "media_management")
        stock_result = await stock_collection.insert_one(stock_doc)
        stock_media_id = str(stock_result.inserted_id)

        # Generate media-specific identifiers and values
        unique_id = generate_unique_id()
        sanitized_business_id = business_id.strip() if business_id else None


        # Process as stock upload (S3 upload + media doc)
        media_result = await self._process_stock_image_upload(
            file_bytes=file_bytes,
            business_id=sanitized_business_id,
            unique_id=unique_id,
            mime_type=mime_type,
            extension=extension,
            original_filename=details.get("original_filename"),
            alt=description,
            tags=keywords,
            width=width,
            height=height,
            aspect_ratio=aspect_ratio,
            size=size,
            stock_media_id=stock_media_id,
            search_query=search_query,
            stock_provider="shutterstock",
            trade_type=trade_type,  
        )

        # Attach stock_media_id for response context
        media_result["stock_media_id"] = stock_media_id
        return media_result
    
    async def ingest_stock_video(
        self,
        video_id: str,
        search_query: str,
        business_id: Optional[str],
        shutterstock_service,
        trade_type: Optional[str] = None,
    ) -> dict:
        """
        Ingest a Shutterstock stock video:
        - fetch video details
        - download preview_mp4 and thumb_jpg
        - upload preview + thumbnail to S3
        - create stock_media and media documents
        """
        if not search_query or not search_query.strip():
            raise HTTPException(status_code=400, detail="search_query is required")

        details = await shutterstock_service.get_video_details(video_id=video_id)
        assets = details.get("assets", {}) or {}

        preview_asset = assets.get("preview_mp4") or {}
        if not preview_asset.get("url"):
            raise HTTPException(
                status_code=502,
                detail="No downloadable preview asset available for this stock video",
            )

        preview_url = preview_asset["url"]
        width = preview_asset.get("width")
        height = preview_asset.get("height")

        # Fallback to known resolution assets if preview lacks dimensions
        for candidate_key in ["sd", "web", "hd"]:
            candidate = assets.get(candidate_key) or {}
            width = width or candidate.get("width")
            height = height or candidate.get("height")
            if width and height:
                break

        aspect_ratio = details.get("aspect")
        if aspect_ratio is None:
            if height and height != 0 and width:
                aspect_ratio = round(width / height, 4)
            else:
                aspect_ratio = 1.0

        # Download preview video
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(preview_url, timeout=30.0, follow_redirects=True)
                response.raise_for_status()
                video_bytes = response.content
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to download preview asset: {e.response.status_code}",
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to download preview asset: {str(e)}",
            )

        # Detect mime/extension; fallback to mp4
        mime_type = "video/mp4"
        extension = "mp4"
        try:
            detected_mime, detected_ext, detected_media_type = validate_file_type(
                video_bytes, filename=preview_url
            )
            if detected_media_type != "video":
                raise MediaValidationError("Preview asset is not a video")
            mime_type = detected_mime
            extension = detected_ext
        except MediaValidationError:
            pass

        size = preview_asset.get("file_size") or len(video_bytes) or 0

        description = details.get("description")
        keywords = details.get("keywords") or []
        if not isinstance(keywords, list):
            keywords = []

        # Thumbnail selection: thumb_jpg preferred, then preview_jpg, then first thumb_jpgs entry
        thumb_asset = assets.get("thumb_jpg") or {}
        thumb_url = thumb_asset.get("url")
        if not thumb_url:
            fallback_thumb = assets.get("preview_jpg") or {}
            thumb_url = fallback_thumb.get("url")
        if not thumb_url:
            thumb_jpgs = assets.get("thumb_jpgs", {}) or {}
            thumb_urls = thumb_jpgs.get("urls") or []
            if thumb_urls:
                thumb_url = thumb_urls[0]

        if not thumb_url:
            raise HTTPException(
                status_code=502, detail="No thumbnail available for this stock video"
            )

        try:
            async with httpx.AsyncClient() as client:
                thumb_response = await client.get(thumb_url, timeout=30.0, follow_redirects=True)
                thumb_response.raise_for_status()
                thumbnail_bytes = thumb_response.content
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to download thumbnail: {e.response.status_code}",
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to download thumbnail: {str(e)}",
            )

        thumbnail_mime_type = "image/jpeg"
        thumbnail_width = None
        thumbnail_height = None
        try:
            thumb_mime, thumb_ext, thumb_media_type = validate_file_type(
                thumbnail_bytes, filename=thumb_url
            )
            if thumb_media_type == "image":
                thumbnail_mime_type = thumb_mime
            thumb_metadata = await self._run_in_thread(
                extract_image_metadata, thumbnail_bytes
            )
            thumbnail_width = thumb_metadata.get("width")
            thumbnail_height = thumb_metadata.get("height")
        except MediaValidationError:
            pass
        except MediaProcessingError:
            # If metadata extraction fails, continue with available data
            pass

        # Insert stock_media document
        query_hash = hashlib.sha256(search_query.encode("utf-8")).hexdigest()
        now = datetime.now()
        stock_doc = {
            "id": video_id,
            "stock_provider": "shutterstock",
            "search_query": search_query,
            "query_hash": query_hash,
            "api_response": details,
            "created_at": now,
            "updated_at": now,
        }
        stock_collection = await get_mongo_collection("stock_media", "media_management")
        stock_result = await stock_collection.insert_one(stock_doc)
        stock_media_id = str(stock_result.inserted_id)

        # Generate media-specific identifiers and values
        unique_id = generate_unique_id()
        sanitized_business_id = business_id.strip() if business_id else None

        # Backfill missing dimensions from aspect ratio if possible
        if aspect_ratio and (not width or not height):
            if width and not height and aspect_ratio != 0:
                height = int(round(width / aspect_ratio))
            elif height and not width:
                width = int(round(aspect_ratio * height))

        width_for_doc = width or 0
        height_for_doc = height or 0


        media_result = await self._process_stock_video_upload(
            video_bytes=video_bytes,
            thumbnail_bytes=thumbnail_bytes,
            business_id=sanitized_business_id,
            unique_id=unique_id,
            mime_type=mime_type,
            extension=extension,
            original_filename=details.get("original_filename"),
            alt=description,
            tags=keywords,
            width=width_for_doc,
            height=height_for_doc,
            aspect_ratio=aspect_ratio,
            size=size,
            stock_media_id=stock_media_id,
            search_query=search_query,
            stock_provider="shutterstock",
            thumbnail_mime_type=thumbnail_mime_type,
            thumbnail_width=thumbnail_width,
            thumbnail_height=thumbnail_height,
            trade_type=trade_type,
        )

        media_result["stock_media_id"] = stock_media_id
        return media_result
    


    async def bulk_ingest_stock_by_query(
        self,
        query: str,
        trade_type: str,
        media_type: str,
        limit: int,
        shutterstock_service,
    ) -> dict:
        """
        Bulk ingest stock media for a single query.
        
        Args:
            query: Search query
            trade_type: Trade type (e.g., 'plumbing', 'hvac')
            media_type: 'image' or 'video'
            limit: Number of results to ingest
            shutterstock_service: Shutterstock service instance
            
        Returns:
            Summary of ingestion results
        """
        ingested = []
        failed = []
        
        try:
            if media_type == "image":
                # Search images
                search_results = await shutterstock_service.search_images(
                    query=query,
                    per_page=limit,
                    safe=True,
                    sort="popular",
                )
                
                items = search_results.get("data", [])[:limit]
                
                # Ingest each image
                for item in items:
                    image_id = item.get("id")
                    if not image_id:
                        continue
                    
                    try:
                        result = await self.ingest_stock_image(
                            image_id=str(image_id),
                            search_query=query,
                            business_id=None,  # Generic stock
                            shutterstock_service=shutterstock_service,
                            trade_type=trade_type,  # Pass trade_type here
                        )
                        ingested.append({
                            "id": image_id,
                            "type": "image",
                            "media_id": result.get("media", {}).get("id"),
                        })
                    except Exception as e:
                        failed.append({
                            "id": image_id,
                            "type": "image",
                            "error": str(e),
                        })
            
            elif media_type == "video":
                # Search videos
                search_results = await shutterstock_service.search_videos(
                    query=query,
                    per_page=limit,
                    safe=True,
                    sort="popular",
                )
                
                items = search_results.get("data", [])[:limit]
                
                # Ingest each video
                for item in items:
                    video_id = item.get("id")
                    if not video_id:
                        continue
                    
                    try:
                        result = await self.ingest_stock_video(
                            video_id=str(video_id),
                            search_query=query,
                            business_id=None,  # Generic stock
                            shutterstock_service=shutterstock_service,
                            trade_type=trade_type,  # Pass trade_type here
                        )
                        ingested.append({
                            "id": video_id,
                            "type": "video",
                            "media_id": result.get("media", {}).get("id"),
                        })
                    except Exception as e:
                        failed.append({
                            "id": video_id,
                            "type": "video",
                            "error": str(e),
                        })
            
            else:
                raise ValueError(f"Invalid media_type: {media_type}")
            
            return {
                "success": True,
                "query": query,
                "trade_type": trade_type,
                "media_type": media_type,
                "requested": limit,
                "ingested": len(ingested),
                "failed": len(failed),
                "results": {
                    "ingested": ingested,
                    "failed": failed,
                }
            }
        
        except Exception as e:
            return {
                "success": False,
                "query": query,
                "trade_type": trade_type,
                "media_type": media_type,
                "error": str(e),
            }

    
    def _extract_s3_key_from_url(self, url: str) -> Optional[str]:
        """
        Extract S3 key from a full S3 URL.
        
        URL format: https://{bucket}.s3.{region}.amazonaws.com/{s3_key}
        """
        if not url:
            return None
        try:
            # Split on .amazonaws.com/ and take the path part
            if ".amazonaws.com/" in url:
                return url.split(".amazonaws.com/")[1]
            return None
        except (IndexError, AttributeError):
            return None
    
    def _collect_s3_keys_for_document(self, document: dict) -> list[str]:
        """Collect S3 keys (asset paths + thumbnails) for a media document."""
        media_type = document.get("media_type")
        s3_keys_to_delete: list[str] = []

        if media_type == "image":
            image_data = document.get("image", {}) or {}
            asset_path = image_data.get("asset_path")
            if asset_path:
                s3_keys_to_delete.append(asset_path)
        elif media_type == "video":
            video_data = document.get("video", {}) or {}
            asset_path = video_data.get("asset_path")
            if asset_path:
                s3_keys_to_delete.append(asset_path)
            preview_image = video_data.get("preview_image", {}) or {}
            thumbnail_url = preview_image.get("url")
            if thumbnail_url:
                thumbnail_key = self._extract_s3_key_from_url(thumbnail_url)
                if thumbnail_key:
                    s3_keys_to_delete.append(thumbnail_key)

        return s3_keys_to_delete

    async def _delete_stock_media_document(self, stock_media_id: Optional[str]) -> None:
        """
        Delete the linked stock_media document when a stock asset is removed.
        """
        if not stock_media_id:
            return

        try:
            stock_object_id = ObjectId(stock_media_id)
        except Exception:
            raise HTTPException(status_code=500, detail="Invalid stock media reference")

        stock_collection = await get_mongo_collection("stock_media", "media_management")
        delete_result = await stock_collection.delete_one({"_id": stock_object_id})
        if delete_result.deleted_count == 0:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete stock media record",
            )

    async def delete_media_by_id(self, media_id: str, business_id: str) -> dict:
        """
        Delete media from S3 and MongoDB (including stock_media if applicable).
        
        Args:
            media_id: The MongoDB document ID
            business_id: Business ID (for authorization)
            
        Returns:
            dict with success status and message
        """
        collection = await self._get_media_collection()
        
        # Find the document
        try:
            object_id = ObjectId(media_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid media ID format")
        
        document = await collection.find_one({
            "_id": object_id,
            "business_id": business_id
        })
        
        if not document:
            raise HTTPException(status_code=404, detail="Media not found")
        
        source = document.get("source", "upload")
        media_type = document.get("media_type")
        s3_keys_to_delete = self._collect_s3_keys_for_document(document)

        # Delete from S3 first
        for s3_key in s3_keys_to_delete:
            try:
                await self.delete_from_s3(s3_key)
            except HTTPException:
                # Log but continue - we still want to delete from MongoDB
                # In production, you might want to handle this differently
                pass
        
        # Delete from MongoDB
        result = await collection.delete_one({
            "_id": object_id,
            "business_id": business_id
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=500, detail="Failed to delete media from database")

        if source == "stock":
            await self._delete_stock_media_document(document.get("stock_media_id"))

        source_label = "Stock media" if source == "stock" else (media_type.capitalize() if media_type else "Media")
        
        return {
            "success": True,
            "message": f"{source_label} deleted successfully"
        }

    async def delete_media(self, media_id: str, business_id: str) -> dict:
        """
        Backwards-compatible wrapper for deleting media by id.
        """
        return await self.delete_media_by_id(media_id, business_id)


def get_media_service(
    current_user: Optional[CurrentUserResponse] = Depends(get_current_user_optional),
    request: Request = None,
) -> MediaService:
    """Get MediaService instance for dependency injection."""
    return MediaService(current_user, request)