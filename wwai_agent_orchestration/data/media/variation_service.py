"""
Variation Service for post-processing generated images.
Creates downscaled variations for optimized delivery.
"""
import asyncio
import functools
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from io import BytesIO

from PIL import Image
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection

from app.products.page_builder.config.aws import aws_config
from app.core.db_mongo import get_mongo_collection
from app.products.page_builder.utils.media.upload_utils.upload_to_s3 import get_s3_client, generate_s3_url


# =============================================================================
# CONFIGURATION - Scale Factors (maintains aspect ratio)
# =============================================================================

VARIATION_CONFIG = [
    {"index": "0", "scale_factor": 0.2},   # 20% of original
    {"index": "1", "scale_factor": 0.4},   # 40% of original
    {"index": "2", "scale_factor": 0.6},   # 60% of original
    {"index": "3", "scale_factor": 0.8},   # 80% of original
]
# Original (1.0) is already stored, so we create 4 downscaled + 1 original = 5 total

JPEG_QUALITY = 85


class VariationService:
    """Service for creating image variations."""
    
    def __init__(self):
        self.s3_client, error = get_s3_client()
        if error:
            raise HTTPException(status_code=500, detail=f"Failed to initialize S3 client: {error}")
        
        self.bucket_name = aws_config.S3_MEDIA_BUCKET_NAME
    
    async def _run_in_thread(self, func, *args, **kwargs):
        """Run synchronous function in thread pool."""
        loop = asyncio.get_event_loop()
        partial_func = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, partial_func)
    
    def _construct_s3_url(self, s3_key: str) -> str:
        """Construct direct S3 URL."""
        return generate_s3_url(s3_key, bucket_name=self.bucket_name)
    
    async def _get_media_collection(self) -> AsyncIOMotorCollection:
        """Get the media MongoDB collection."""
        return await get_mongo_collection("media", "media_management")
    
    async def _get_trades_collection(self) -> AsyncIOMotorCollection:
        """Get the trades collection for tracking."""
        return await get_mongo_collection("gemini_trade_queries", "trades")
    
    # =========================================================================
    # S3 OPERATIONS
    # =========================================================================
    
    async def download_from_s3(self, asset_path: str) -> bytes:
        """Download file from S3."""
        try:
            response = await self._run_in_thread(
                self.s3_client.get_object,
                Bucket=self.bucket_name,
                Key=asset_path
            )
            body = response['Body']
            data = await self._run_in_thread(body.read)
            return data
        except ClientError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to download from S3: {str(e)}"
            )
    
    async def upload_to_s3(
        self, 
        file_bytes: bytes, 
        s3_key: str, 
        content_type: str = "image/jpeg"
    ) -> str:
        """Upload file bytes to S3. Returns S3 URL."""
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
    
    # =========================================================================
    # IMAGE PROCESSING
    # =========================================================================
    
    def resize_image_by_scale(
        self,
        image_bytes: bytes,
        scale_factor: float
    ) -> Tuple[bytes, int, int]:
        """
        Resize image by scale factor, maintaining aspect ratio.
        
        Args:
            image_bytes: Original image data
            scale_factor: Scale factor (e.g., 0.5 = half size)
            
        Returns:
            Tuple of (resized_bytes_jpeg, new_width, new_height)
        """
        image = Image.open(BytesIO(image_bytes))
        
        # Convert to RGB if necessary (PNG with alpha, palette mode, etc.)
        if image.mode in ('RGBA', 'P', 'LA'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        original_width, original_height = image.size
        
        # Calculate new dimensions based on scale factor
        new_width = int(original_width * scale_factor)
        new_height = int(original_height * scale_factor)
        
        # Ensure minimum dimension of 1px
        new_width = max(1, new_width)
        new_height = max(1, new_height)
        
        # Resize using high-quality resampling
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save to bytes as JPEG
        output = BytesIO()
        resized.save(output, format='JPEG', quality=JPEG_QUALITY, optimize=True)
        
        return output.getvalue(), new_width, new_height
    
    def create_all_variations(
        self,
        image_bytes: bytes,
        base_asset_path: str
    ) -> Dict[str, Dict]:
        """
        Create all variation sizes for an image using scale factors.
        
        Args:
            image_bytes: Original image data
            base_asset_path: Original asset path (e.g., "org_id/images/uuid.png")
            
        Returns:
            Dict mapping variation index to variation data (including bytes)
        """
        # Parse the base path to create variation paths
        # e.g., "org_id/images/uuid.png" -> "org_id/images/uuid_0.jpg"
        path_without_ext = base_asset_path.rsplit('.', 1)[0]
        
        variations = {}
        
        for config in VARIATION_CONFIG:
            index = config["index"]
            scale = config["scale_factor"]
            
            # Resize by scale factor
            resized_bytes, width, height = self.resize_image_by_scale(image_bytes, scale)
            
            # Build variation path (JPEG extension)
            variation_path = f"{path_without_ext}_{index}.jpg"
            
            variations[index] = {
                "bytes": resized_bytes,
                "width": width,
                "height": height,
                "asset_path": variation_path,
                "size": len(resized_bytes),
                "scale_factor": scale
            }
        
        return variations
    
    # =========================================================================
    # SINGLE IMAGE PROCESSING
    # =========================================================================
    
    async def process_single_image(self, image_doc: Dict) -> Dict:
        """
        Process a single image - create and upload variations.
        
        Args:
            image_doc: MongoDB document for the image
            
        Returns:
            Dict with processing result
        """
        doc_id = image_doc["_id"]
        image_data = image_doc.get("image", {})
        asset_path = image_data.get("asset_path")
        
        if not asset_path:
            return {
                "success": False,
                "doc_id": str(doc_id),
                "error": "No asset_path found"
            }
        
        try:
            # Step 1: Download original from S3
            original_bytes = await self.download_from_s3(asset_path)
            
            # Step 2: Create all variations (CPU-bound, runs in thread pool)
            variations_data = await self._run_in_thread(
                self.create_all_variations,
                original_bytes,
                asset_path
            )
            
            # Step 3: Upload each variation to S3
            variations_for_db = {}
            
            for index, var_data in variations_data.items():
                src = await self.upload_to_s3(
                    var_data["bytes"],
                    var_data["asset_path"],
                    "image/jpeg"
                )
                
                variations_for_db[index] = {
                    "src": src,
                    "width": var_data["width"],
                    "height": var_data["height"],
                    "asset_path": var_data["asset_path"],
                    "size": var_data["size"],
                    "scale_factor": var_data["scale_factor"]
                }
            
            # Step 4: Update MongoDB document
            collection = await self._get_media_collection()
            await collection.update_one(
                {"_id": doc_id},
                {
                    "$set": {
                        "image.variations": variations_for_db,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return {
                "success": True,
                "doc_id": str(doc_id),
                "variations_created": len(variations_for_db)
            }
            
        except Exception as e:
            return {
                "success": False,
                "doc_id": str(doc_id),
                "error": str(e)
            }
    
    # =========================================================================
    # BATCH PROCESSING BY TRADE
    # =========================================================================
    
    async def process_trade_variations(
        self,
        trade_type: str,
        batch_size: int = 50
    ) -> Dict:
        """
        Process all unprocessed images for a trade type.
        
        Idempotent: skips images that already have variations.
        
        Args:
            trade_type: Trade type to process
            batch_size: Number of images to process in this call
            
        Returns:
            Dict with processing results
        """
        media_collection = await self._get_media_collection()
        
        # Query unprocessed images (no variations field)
        query = {
            "source": "generated",
            "trade_type": trade_type,
            "image.variations": {"$exists": False}
        }
        
        # First check if trade has any images at all
        total_for_trade = await media_collection.count_documents({
            "source": "generated",
            "trade_type": trade_type
        })
        
        if total_for_trade == 0:
            return {
                "success": False,
                "trade_type": trade_type,
                "status": "error",
                "message": f"No generated images found for trade '{trade_type}'",
                "processed": 0,
                "failed": 0,
                "remaining": 0
            }
        
        cursor = media_collection.find(query).limit(batch_size)
        images = await cursor.to_list(length=batch_size)
        
        if not images:
            # Check total remaining
            remaining = await media_collection.count_documents(query)
            
            return {
                "success": True,
                "trade_type": trade_type,
                "status": "complete" if remaining == 0 else "processing",
                "message": "All images processed" if remaining == 0 else "Batch complete",
                "processed": 0,
                "failed": 0,
                "remaining": remaining
            }
        
        # Process each image
        processed = 0
        failed = 0
        errors = []
        
        for image_doc in images:
            result = await self.process_single_image(image_doc)
            
            if result["success"]:
                processed += 1
            else:
                failed += 1
                errors.append({
                    "doc_id": result["doc_id"],
                    "error": result.get("error")
                })
        
        # Check remaining after this batch
        remaining = await media_collection.count_documents(query)
        
        status = "complete" if remaining == 0 else "processing"
        
        return {
            "success": True,
            "trade_type": trade_type,
            "status": status,
            "processed": processed,
            "failed": failed,
            "remaining": remaining,
            "errors": errors if errors else None,
            "message": f"Processed {processed} images, {remaining} remaining"
        }
    
    # =========================================================================
    # STATUS CHECKING
    # =========================================================================
    
    async def get_postprocess_status(
        self,
        trade_type: Optional[str] = None
    ) -> Dict:
        """
        Get post-processing status for one or all trades.
        
        Derives trade list directly from media collection (not trades collection).
        
        Args:
            trade_type: Optional specific trade to check
            
        Returns:
            Dict with status info
        """
        media_collection = await self._get_media_collection()
        
        if trade_type:
            # Single trade status
            # Count total and processed images
            total = await media_collection.count_documents({
                "source": "generated",
                "trade_type": trade_type
            })
            
            if total == 0:
                return {
                    "success": False,
                    "message": f"No generated images found for trade '{trade_type}'"
                }
            
            processed = await media_collection.count_documents({
                "source": "generated",
                "trade_type": trade_type,
                "image.variations": {"$exists": True}
            })
            
            remaining = total - processed
            
            # Derive status from counts
            if remaining == 0:
                status = "complete"
            elif processed > 0:
                status = "processing"
            else:
                status = "pending"
            
            return {
                "success": True,
                "trade_type": trade_type,
                "postprocess_status": status,
                "total_images": total,
                "processed_images": processed,
                "remaining": remaining,
                "progress_percent": round((processed / total * 100), 1) if total > 0 else 0
            }
        
        else:
            # Get all unique trade_types from generated images
            pipeline = [
                {"$match": {"source": "generated"}},
                {"$group": {"_id": "$trade_type"}},
                {"$sort": {"_id": 1}}
            ]
            
            trade_types_cursor = media_collection.aggregate(pipeline)
            trade_types = [doc["_id"] for doc in await trade_types_cursor.to_list(length=100)]
            
            results = []
            for tt in trade_types:
                if not tt:  # Skip empty trade_type
                    continue
                    
                total = await media_collection.count_documents({
                    "source": "generated",
                    "trade_type": tt
                })
                
                processed = await media_collection.count_documents({
                    "source": "generated",
                    "trade_type": tt,
                    "image.variations": {"$exists": True}
                })
                
                remaining = total - processed
                
                # Derive status from counts
                if remaining == 0:
                    status = "complete"
                elif processed > 0:
                    status = "processing"
                else:
                    status = "pending"
                
                results.append({
                    "trade_type": tt,
                    "postprocess_status": status,
                    "total": total,
                    "processed": processed,
                    "remaining": remaining,
                    "progress_percent": round((processed / total * 100), 1) if total > 0 else 0
                })
            
            # Summary stats
            total_images = sum(r["total"] for r in results)
            total_processed = sum(r["processed"] for r in results)
            
            return {
                "success": True,
                "trades": results,
                "total_trades": len(results),
                "summary": {
                    "total_images": total_images,
                    "processed_images": total_processed,
                    "remaining": total_images - total_processed,
                    "progress_percent": round((total_processed / total_images * 100), 1) if total_images > 0 else 0
                }
            }


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

def get_variation_service() -> VariationService:
    """Dependency for FastAPI"""
    return VariationService()