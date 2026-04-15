"""Gemini AI service for batch and real-time image generation"""

import os
import json
import time
import asyncio
import functools
import base64
import random
import uuid
from uuid import uuid4
from typing import List, Dict, Optional, Any
from datetime import datetime
from io import BytesIO

from PIL import Image
from google import genai
from google.genai import types

from app.core.db_mongo import get_mongo_collection
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.products.page_builder.services.media.media_service import MediaService


class GeminiService:
    """Handles Gemini Batch API and Real-time API for image generation"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found")
        
        self.client = genai.Client(api_key=self.api_key)
    
    # =========================================================================
    # BATCH API - SUBMIT ONLY (Returns immediately)
    # =========================================================================
    
    def create_batch_jsonl(
        self, 
        prompts: List[str], 
        model: str,
        aspect_ratio: Optional[str] = None,
        image_size: Optional[str] = None
    ) -> str:
        """
        Create JSONL file for batch processing
        
        Note: imageConfig (aspect_ratio, image_size) is only supported by 
        gemini-3-pro-image-preview. For other models, these are ignored.
        """
        temp_file = f"/tmp/batch_requests_{uuid4()}.jsonl"
        
        # Check if model supports imageConfig
        supports_image_config = "gemini-3-pro" in model
        has_image_config_params = aspect_ratio and image_size
        
        with open(temp_file, "w") as f:
            for i, prompt in enumerate(prompts):
                generation_config = {
                    "responseModalities": ["TEXT", "IMAGE"]
                }
                
                # Add imageConfig only for supported models
                if supports_image_config and has_image_config_params:
                    generation_config["imageConfig"] = {
                        "aspectRatio": aspect_ratio,
                        "imageSize": image_size
                    }
                
                request = {
                    "key": f"request-{i+1}",
                    "request": {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generation_config": generation_config
                    }
                }
                f.write(json.dumps(request) + "\n")
        
        return temp_file
    
    async def submit_batch_job_async(
        self, 
        prompts: List[str],
        model: str,
        aspect_ratio: Optional[str] = None,
        image_size: Optional[str] = None
    ) -> Dict:
        """
        Submit batch job and return immediately (non-blocking)
        
        Returns:
            Dict with batch_job_name and metadata
        """
        
        # Create JSONL file (with imageConfig if supported)
        jsonl_file = self.create_batch_jsonl(
            prompts=prompts,
            model=model,
            aspect_ratio=aspect_ratio,
            image_size=image_size
        )
        
        # Upload file to Gemini
        uploaded_file = self.client.files.upload(
            file=jsonl_file,
            config=types.UploadFileConfig(
                display_name=f'ai-generation-{datetime.now().strftime("%Y%m%d-%H%M%S")}',
                mime_type='jsonl'
            )
        )
        
        # Clean up temp file
        os.remove(jsonl_file)
        
        # Submit batch job
        batch_job = self.client.batches.create(
            model=model,
            src=uploaded_file.name,
            config={
                'display_name': f"ai-gen-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            }
        )
        
        return {
            "batch_job_name": batch_job.name,
            "state": batch_job.state.name,
            "submitted_at": datetime.utcnow().isoformat()
        }
    
    # =========================================================================
    # BATCH API - POLL STATUS (Non-blocking check)
    # =========================================================================
    
    def get_batch_status(self, batch_name: str) -> Dict:
        """
        Get current status of a batch job (non-blocking)
        
        Returns:
            Dict with batch status info
        """
        try:
            batch_job = self.client.batches.get(name=batch_name)
            
            return {
                "batch_job_name": batch_job.name,
                "state": batch_job.state.name,
                "display_name": batch_job.display_name,
                "created_time": batch_job.create_time.isoformat() if batch_job.create_time else None,
                "success": True
            }
        except Exception as e:
            return {
                "batch_job_name": batch_name,
                "state": "ERROR",
                "error": str(e),
                "success": False
            }
    
    def is_batch_complete(self, batch_name: str) -> Dict:
        """
        Check if batch is complete and return status
        
        Returns:
            Dict with is_complete, is_success, state
        """
        status = self.get_batch_status(batch_name)
        state = status.get("state", "UNKNOWN")
        
        return {
            "batch_job_name": batch_name,
            "state": state,
            "is_complete": state in ["JOB_STATE_SUCCEEDED", "JOB_STATE_FAILED", "JOB_STATE_CANCELLED"],
            "is_success": state == "JOB_STATE_SUCCEEDED",
            "is_failed": state in ["JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "ERROR"]
        }
    
    # =========================================================================
    # BATCH API - DOWNLOAD RESULTS
    # =========================================================================
    
    def download_batch_results(self, batch_name: str) -> List[Dict]:
        """
        Download and parse batch results
        
        Returns:
            List of result dicts with image data
        """
        batch_job = self.client.batches.get(name=batch_name)
        
        if batch_job.state.name != "JOB_STATE_SUCCEEDED":
            raise ValueError(f"Batch not complete. State: {batch_job.state.name}")
        
        if not batch_job.dest or not batch_job.dest.file_name:
            raise ValueError("No result file found")
        
        # Download results file
        file_content_bytes = self.client.files.download(file=batch_job.dest.file_name)
        file_content = file_content_bytes.decode('utf-8')
        
        # Parse JSONL results
        results = []
        for line in file_content.splitlines():
            if line:
                parsed = json.loads(line)
                results.append(parsed)
        
        return results
    
    # =========================================================================
    # BATCH API - BLOCKING METHODS (For backward compatibility)
    # =========================================================================
    
    async def submit_batch_job(
        self, 
        prompts: List[str],
        model: str,
        aspect_ratio: Optional[str] = None,
        image_size: Optional[str] = None
    ) -> str:
        """Submit batch job and return batch_name (backward compatible)"""
        result = await self.submit_batch_job_async(
            prompts=prompts,
            model=model,
            aspect_ratio=aspect_ratio,
            image_size=image_size
        )
        return result["batch_job_name"]
    
    async def poll_batch_job(
        self, 
        batch_name: str, 
        poll_interval: int = 10,
        timeout: int = 3600
    ) -> types.BatchJob:
        """Poll batch job until complete (blocking)"""
        
        start_time = time.time()
        
        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Batch job timed out after {timeout} seconds")
            
            batch_job = self.client.batches.get(name=batch_name)
            
            if batch_job.state.name == "JOB_STATE_SUCCEEDED":
                return batch_job
            elif batch_job.state.name == "JOB_STATE_FAILED":
                raise RuntimeError(f"Batch job failed")
            elif batch_job.state.name == "JOB_STATE_CANCELLED":
                raise RuntimeError("Batch job was cancelled")
            
            await asyncio.sleep(poll_interval)
    
    async def download_batch_results_async(self, batch_name: str) -> List[Dict]:
        """Async wrapper for download_batch_results"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.download_batch_results, batch_name)
    
    # =========================================================================
    # REAL-TIME API METHODS (supports aspect_ratio and image_size)
    # =========================================================================
    
    async def generate_images_realtime(
        self,
        prompts: List[str],
        model: str = "gemini-2.5-flash-image",
        aspect_ratio: Optional[str] = None,
        image_size: Optional[str] = None
    ) -> List[Dict]:
        """
        Generate images using Real-time API
        
        Args:
            prompts: List of text prompts for image generation
            model: Gemini model to use
            aspect_ratio: Image aspect ratio (only for gemini-3-pro-image-preview)
            image_size: Output resolution (only for gemini-3-pro-image-preview)
            
        Returns:
            List of dicts with prompt, image_data (bytes), and mime_type
        """
        results = []
        
        for i, prompt in enumerate(prompts):
            try:
                response = await self._generate_single_image(
                    prompt=prompt,
                    model=model,
                    aspect_ratio=aspect_ratio,
                    image_size=image_size
                )
                
                if response:
                    results.append({
                        "index": i,
                        "prompt": prompt,
                        "image_data": response["image_data"],
                        "mime_type": response["mime_type"],
                        "success": True
                    })
                else:
                    results.append({
                        "index": i,
                        "prompt": prompt,
                        "success": False,
                        "error": "No image generated"
                    })
                    
            except Exception as e:
                results.append({
                    "index": i,
                    "prompt": prompt,
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    async def _generate_single_image(
        self,
        prompt: str,
        model: str,
        aspect_ratio: Optional[str] = None,
        image_size: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Generate a single image using the real-time API
        
        Note: image_config (aspect_ratio, image_size) is only supported by 
        gemini-3-pro-image-preview. For gemini-2.5-flash-image, these params
        are ignored and images default to 1024x1024.
        """
        
        # Build config based on whether image_config params are provided
        # and if the model supports them (only gemini-3-pro does)
        supports_image_config = "gemini-3-pro" in model
        has_image_config_params = aspect_ratio and image_size
        
        if supports_image_config and has_image_config_params:
            config = types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE'],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=image_size
                )
            )
        else:
            # No image_config - works with all image generation models
            config = types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE']
            )
        
        # Run synchronous API call in thread pool
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.models.generate_content(
                model=model,
                contents=[prompt],
                config=config
            )
        )
        
        # Extract image data from response
        for part in response.parts:
            if part.inline_data is not None:
                return {
                    "image_data": part.inline_data.data,  # bytes
                    "mime_type": part.inline_data.mime_type
                }
        
        return None


# =============================================================================
# CONFIGURATION - Aspect Ratio Distribution
# =============================================================================

ASPECT_RATIO_CONFIG = [
    {"ratio": "1:1", "weight": 0.3617, "category": "Square"},
    {"ratio": "4:3", "weight": 0.2500, "category": "Landscape"},
    {"ratio": "16:9", "weight": 0.1755, "category": "Wide"},
    {"ratio": "21:9", "weight": 0.0691, "category": "Ultra-wide"},
]

# Normalize weights to sum to 1.0
_total_weight = sum(ar["weight"] for ar in ASPECT_RATIO_CONFIG)
for ar in ASPECT_RATIO_CONFIG:
    ar["normalized_weight"] = ar["weight"] / _total_weight


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def distribute_prompts_by_aspect_ratio(
    prompts: List[str],
    aspect_ratios: List[Dict] = ASPECT_RATIO_CONFIG,
    shuffle: bool = True
) -> Dict[str, List[str]]:
    """
    Distribute prompts across aspect ratios based on normalized weights.
    
    Args:
        prompts: List of prompt strings
        aspect_ratios: List of dicts with 'ratio' and 'normalized_weight' keys
        shuffle: Whether to shuffle prompts before distribution
        
    Returns:
        Dict mapping aspect ratio to list of prompts
        e.g., {"1:1": ["prompt1", "prompt2", ...], "4:3": [...], ...}
    """
    if shuffle:
        prompts = prompts.copy()
        random.shuffle(prompts)
    
    total_prompts = len(prompts)
    distribution = {}
    assigned = 0
    
    # Sort by weight descending to assign largest groups first
    sorted_ratios = sorted(aspect_ratios, key=lambda x: x["normalized_weight"], reverse=True)
    
    for i, ar in enumerate(sorted_ratios):
        ratio = ar["ratio"]
        weight = ar["normalized_weight"]
        
        # For last ratio, assign all remaining prompts
        if i == len(sorted_ratios) - 1:
            count = total_prompts - assigned
        else:
            count = round(total_prompts * weight)
        
        # Ensure we don't exceed available prompts
        count = min(count, total_prompts - assigned)
        
        # Assign prompts
        distribution[ratio] = prompts[assigned:assigned + count]
        assigned += count
    
    return distribution


# =============================================================================
# GEMINI MEDIA ORCHESTRATOR
# =============================================================================

class GeminiMediaOrchestrator:
    """Orchestrates Gemini image generation with S3 upload and MongoDB storage"""
    
    def __init__(self, media_service: "MediaService", gemini_service: GeminiService):
        """
        Initialize orchestrator with media and gemini services.
        
        Args:
            media_service: MediaService instance for S3/MongoDB operations
            gemini_service: GeminiService instance for image generation
        """
        self.media_service = media_service
        self.gemini_service = gemini_service
        
        # Access S3 client and bucket from media_service
        self.s3_client = media_service.s3_client
        self.bucket_name = media_service.bucket_name
    
    async def _run_in_thread(self, func, *args, **kwargs):
        """Run synchronous function in thread pool."""
        loop = asyncio.get_event_loop()
        partial_func = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, partial_func)
    
    async def _get_media_collection(self):
        """Get the media MongoDB collection from media_management database."""
        return await self.media_service._get_media_collection()
    
    async def _upload_generated_image_to_s3(
        self,
        image_data: bytes,
        org_id: str,
        filename: str
    ) -> dict:
        """Upload generated image to S3 and return metadata"""
        
        # Get image dimensions
        image = Image.open(BytesIO(image_data))
        width, height = image.size
        aspect_ratio = round(width / height, 4)
        
        # Generate S3 path
        image_id = str(uuid.uuid4())
        asset_path = f"{org_id}/images/{image_id}.png"
        
        # Upload to S3
        await self._run_in_thread(
            self.s3_client.put_object,
            Bucket=self.bucket_name,
            Key=asset_path,
            Body=image_data,
            ContentType='image/png'
        )
        
        # Generate public URL
        src = self.media_service._construct_s3_url(asset_path)
        
        return {
            'src': src,
            'asset_path': asset_path,
            'filename': filename,
            'width': width,
            'height': height,
            'aspect_ratio': aspect_ratio,
            'size': len(image_data),
            'id': image_id
        }
    
    def _create_generated_media_document(
        self,
        image_metadata: dict,
        trade_type: str,
        category: Optional[str],
        original_prompt: str,
        style_modifier: str,
        full_prompt: str,
        batch_job_name: Optional[str],
        model: str,
        api_mode: str = "batch",
        aspect_ratio: Optional[str] = None,
        image_size: Optional[str] = None,
    ) -> dict:
        """Create MongoDB document for generated image"""
        
        now = datetime.utcnow()
        
        generation_metadata = {
            "original_prompt": original_prompt,
            "style_modifier": style_modifier,
            "full_prompt": full_prompt,
            "model": model,
            "api_mode": api_mode,
            "generated_at": now.isoformat()
        }
        
        # Add batch-specific or realtime-specific metadata
        if api_mode == "batch" and batch_job_name:
            generation_metadata["batch_job"] = batch_job_name
        elif api_mode == "realtime":
            generation_metadata["aspect_ratio_requested"] = aspect_ratio
            generation_metadata["image_size_requested"] = image_size
        
        return {
            "source": "generated",
            "media_type": "image",
            "size": image_metadata['size'],
            "autopopulation_metadata": {
                "media_extension": "png",
                "width": image_metadata['width'],
                "height": image_metadata['height'],
            },
            "created_at": now,
            "updated_at": now,
            "image": {
                "src": image_metadata['src'],
                "asset_path": image_metadata['asset_path'],
                "filename": image_metadata['filename'],
                "width": image_metadata['width'],
                "height": image_metadata['height'],
                "aspect_ratio": image_metadata['aspect_ratio'],
                "alt": full_prompt,
                "id": image_metadata['id']
            },
            "trade_type": trade_type,
            "trade_type_search_query": trade_type,
            "category": category,
            "generation_metadata": generation_metadata
        }
    
    def _create_batch_generated_media_document(
        self,
        image_metadata: dict,
        trade_type: str,
        original_prompt: str,
        style_modifier: str,
        full_prompt: str,
        batch_job_name: str,
        model: str,
        aspect_ratio: str,
        image_size: str,
    ) -> dict:
        """Create MongoDB document for generated image from batch"""
        
        now = datetime.utcnow()
        
        return {
            "source": "generated",
            "media_type": "image",
            "size": image_metadata['size'],
            "autopopulation_metadata": {
                "media_extension": "png",
                "width": image_metadata['width'],
                "height": image_metadata['height'],
            },
            "created_at": now,
            "updated_at": now,
            "image": {
                "src": image_metadata['src'],
                "asset_path": image_metadata['asset_path'],
                "filename": image_metadata['filename'],
                "width": image_metadata['width'],
                "height": image_metadata['height'],
                "aspect_ratio": image_metadata['aspect_ratio'],
                "alt": full_prompt,
                "id": image_metadata['id']
            },
            "trade_type": trade_type,
            "trade_type_search_query": trade_type,
            "generation_metadata": {
                "original_prompt": original_prompt,
                "style_modifier": style_modifier,
                "full_prompt": full_prompt,
                "model": model,
                "api_mode": "batch",
                "batch_job": batch_job_name,
                "aspect_ratio_requested": aspect_ratio,
                "image_size_requested": image_size,
                "generated_at": now.isoformat()
            }
        }
    
    async def generate_and_ingest_images(
        self,
        prompts: List[str],
        trade_type: str,
        org_id: str,
        style_modifier: str,
        aspect_ratio: str,
        image_size: str,
        model: str,
        category: Optional[str],
        use_realtime: bool = False,
    ) -> dict:
        """
        Generate images using Gemini API and ingest to S3 + MongoDB
        
        Args:
            use_realtime: If True, uses Real-time API (supports aspect_ratio/image_size).
                         If False, uses Batch API (higher rate limits, but 1024x1024 only).
        
        Returns:
            dict with counts, errors, and API-specific metadata
        """
        
        # Combine prompts with style modifier
        full_prompts = [
            f"{style_modifier}. {prompt}"
            for prompt in prompts
        ]
        
        if use_realtime:
            return await self._generate_and_ingest_realtime(
                prompts=prompts,
                full_prompts=full_prompts,
                trade_type=trade_type,
                org_id=org_id,
                style_modifier=style_modifier,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                model=model,
                category=category,
            )
        else:
            return await self._generate_and_ingest_batch(
                prompts=prompts,
                full_prompts=full_prompts,
                trade_type=trade_type,
                org_id=org_id,
                style_modifier=style_modifier,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                model=model,
                category=category,
            )
    
    async def _generate_and_ingest_realtime(
        self,
        prompts: List[str],
        full_prompts: List[str],
        trade_type: str,
        org_id: str,
        style_modifier: str,
        aspect_ratio: str,
        image_size: str,
        model: str,
        category: Optional[str],
    ) -> dict:
        """
        Generate images using Real-time API and ingest to S3 + MongoDB
        
        Supports aspect_ratio and image_size parameters.
        Better for smaller batches where specific dimensions are required.
        """
        
        # Step 1: Generate images via real-time API
        results = await self.gemini_service.generate_images_realtime(
            prompts=full_prompts,
            model=model,
            aspect_ratio=aspect_ratio,
            image_size=image_size
        )
        
        # Step 2: Process each result
        uploaded_count = 0
        inserted_count = 0
        failed_count = 0
        errors = []
        
        for result in results:
            i = result["index"]
            original_prompt = prompts[i]
            full_prompt = full_prompts[i]
            
            try:
                if not result.get("success"):
                    failed_count += 1
                    errors.append({
                        'prompt_index': i,
                        'prompt': original_prompt,
                        'error': result.get("error", "Generation failed")
                    })
                    continue
                
                image_data = result["image_data"]
                
                # Upload to S3
                filename = f"generated_{uuid.uuid4()}.png"
                image_metadata = await self._upload_generated_image_to_s3(
                    image_data=image_data,
                    org_id=org_id,
                    filename=filename
                )
                uploaded_count += 1
                
                # Create MongoDB document
                document = self._create_generated_media_document(
                    image_metadata=image_metadata,
                    trade_type=trade_type,
                    category=category,
                    original_prompt=original_prompt,
                    style_modifier=style_modifier,
                    full_prompt=full_prompt,
                    batch_job_name=None,  # No batch job for realtime
                    model=model,
                    api_mode="realtime",
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                )
                
                # Insert to MongoDB
                collection = await self._get_media_collection()
                await collection.insert_one(document)
                inserted_count += 1
                
            except Exception as e:
                failed_count += 1
                errors.append({
                    'prompt_index': i,
                    'prompt': original_prompt,
                    'error': str(e)
                })
        
        return {
            "success": True,
            "batch_job_name": None,
            "total_prompts": len(prompts),
            "message": f"Successfully processed {uploaded_count}/{len(prompts)} images via Real-time API",
            "api_mode": "realtime",
            "job_state": None,
            "uploaded_count": uploaded_count,
            "inserted_count": inserted_count,
            "failed_count": failed_count,
            "errors": errors
        }
    
    async def _generate_and_ingest_batch(
        self,
        prompts: List[str],
        full_prompts: List[str],
        trade_type: str,
        org_id: str,
        style_modifier: str,
        aspect_ratio: str,
        image_size: str,
        model: str,
        category: Optional[str],
    ) -> dict:
        """
        Generate images using Batch API and ingest to S3 + MongoDB
        
        Note: Batch API does NOT support aspect_ratio/image_size.
        All images will be generated at 1024x1024 (1:1) by default.
        Use this for high-volume generation where dimensions don't matter.
        """
        
        # Step 1: Submit batch job
        batch_job_name = await self.gemini_service.submit_batch_job(
            prompts=full_prompts,
            model=model,
            aspect_ratio=aspect_ratio,
            image_size=image_size
        )
        
        # Step 2: Poll for completion
        batch_job = await self.gemini_service.poll_batch_job(batch_job_name)
        
        # Step 3: Download results
        results = await self.gemini_service.download_batch_results(batch_job_name)
        
        # Step 4 & 5: Process each result
        uploaded_count = 0
        inserted_count = 0
        failed_count = 0
        errors = []
        
        for i, result in enumerate(results):
            try:
                original_prompt = prompts[i]
                full_prompt = full_prompts[i]
                
                # Extract image data
                if 'response' not in result or not result['response']:
                    failed_count += 1
                    errors.append({
                        'prompt_index': i,
                        'error': 'No response in result'
                    })
                    continue
                
                # Find image in response
                image_data = None
                for part in result['response']['candidates'][0]['content']['parts']:
                    if 'inlineData' in part and part['inlineData']['mimeType'].startswith('image/'):
                        image_data = base64.b64decode(part['inlineData']['data'])
                        break
                
                if not image_data:
                    failed_count += 1
                    errors.append({
                        'prompt_index': i,
                        'error': 'No image data found'
                    })
                    continue
                
                # Upload to S3
                filename = f"generated_{uuid.uuid4()}.png"
                image_metadata = await self._upload_generated_image_to_s3(
                    image_data=image_data,
                    org_id=org_id,
                    filename=filename
                )
                uploaded_count += 1
                
                # Create MongoDB document
                document = self._create_generated_media_document(
                    image_metadata=image_metadata,
                    trade_type=trade_type,
                    category=category,
                    original_prompt=original_prompt,
                    style_modifier=style_modifier,
                    full_prompt=full_prompt,
                    batch_job_name=batch_job_name,
                    model=model,
                    api_mode="batch",
                )
                
                # Insert to MongoDB
                collection = await self._get_media_collection()
                await collection.insert_one(document)
                inserted_count += 1
                
            except Exception as e:
                failed_count += 1
                errors.append({
                    'prompt_index': i,
                    'prompt': original_prompt,
                    'error': str(e)
                })
        
        return {
            "success": True,
            "batch_job_name": batch_job_name,
            "total_prompts": len(prompts),
            "message": f"Successfully processed {uploaded_count}/{len(prompts)} images via Batch API",
            "api_mode": "batch",
            "job_state": batch_job.state.name,
            "uploaded_count": uploaded_count,
            "inserted_count": inserted_count,
            "failed_count": failed_count,
            "errors": errors
        }
    
    async def submit_batches_for_trade(
        self,
        trade_type: str,
        org_id: str,
        style_modifier: str,
        image_size: str,
        model: str,
    ) -> Dict:
        """
        Submit batch jobs for a trade (idempotent - won't resubmit if already done)
        
        Returns:
            Dict with submission results
        """
        
        # Get trade document
        collection = await get_mongo_collection("gemini_trade_queries", "trades")
        trade_doc = await collection.find_one({"trade_type": trade_type})
        
        if not trade_doc:
            return {
                "success": False,
                "trade_type": trade_type,
                "message": f"Trade '{trade_type}' not found",
                "batches_submitted": 0,
                "batch_jobs": {}
            }
        
        current_status = trade_doc.get("status", "ready")
        
        # Check if already submitted or completed
        if current_status in ["batches_submitted", "batches_complete", "generated"]:
            existing_jobs = trade_doc.get("batch_jobs", {})
            return {
                "success": True,
                "trade_type": trade_type,
                "message": f"Already in '{current_status}' state. Skipping submission.",
                "batches_submitted": len(existing_jobs),
                "batch_jobs": existing_jobs,
                "skipped": True
            }
        
        # Get prompts
        prompts = trade_doc.get("generated_queries", [])
        if not prompts:
            return {
                "success": False,
                "trade_type": trade_type,
                "message": "No prompts found",
                "batches_submitted": 0,
                "batch_jobs": {}
            }
        
        # Distribute prompts by aspect ratio
        distribution = distribute_prompts_by_aspect_ratio(prompts)
        
        # Submit batches for each aspect ratio
        batch_jobs = {}
        submitted_count = 0
        
        for aspect_ratio, ratio_prompts in distribution.items():
            if not ratio_prompts:
                continue
            
            # Add style modifier to each prompt
            full_prompts = [
                f"{style_modifier}. {prompt}"
                for prompt in ratio_prompts
            ]
            
            try:
                # Submit batch
                result = await self.gemini_service.submit_batch_job_async(
                    prompts=full_prompts,
                    model=model,
                    aspect_ratio=aspect_ratio,
                    image_size=image_size
                )
                
                batch_jobs[aspect_ratio] = {
                    "batch_job_name": result["batch_job_name"],
                    "prompts": ratio_prompts,  # Store original prompts (without style modifier)
                    "full_prompts": full_prompts,  # Store full prompts for reference
                    "prompt_count": len(ratio_prompts),
                    "status": "pending",
                    "submitted_at": result["submitted_at"],
                    "completed_at": None,
                    "processed_at": None,
                    "results": None
                }
                submitted_count += 1
                
            except Exception as e:
                batch_jobs[aspect_ratio] = {
                    "batch_job_name": None,
                    "prompts": ratio_prompts,
                    "prompt_count": len(ratio_prompts),
                    "status": "submit_failed",
                    "error": str(e),
                    "submitted_at": datetime.utcnow().isoformat()
                }
        
        # Update MongoDB with batch jobs
        await collection.update_one(
            {"trade_type": trade_type},
            {
                "$set": {
                    "status": "batches_submitted",
                    "batch_jobs": batch_jobs,
                    "generation_config": {
                        "org_id": org_id,
                        "style_modifier": style_modifier,
                        "image_size": image_size,
                        "model": model
                    },
                    "batches_submitted_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "success": True,
            "trade_type": trade_type,
            "message": f"Submitted {submitted_count} batch jobs",
            "batches_submitted": submitted_count,
            "batch_jobs": batch_jobs
        }
    
    async def poll_batches_for_trade(
        self,
        trade_type: str,
    ) -> Dict:
        """
        Poll status of all batches for a trade and update MongoDB
        
        Returns:
            Dict with current status of all batches
        """
        
        collection = await get_mongo_collection("gemini_trade_queries", "trades")
        trade_doc = await collection.find_one({"trade_type": trade_type})
        
        if not trade_doc:
            return {
                "success": False,
                "trade_type": trade_type,
                "status": "error",
                "message": f"Trade '{trade_type}' not found",
                "total_batches": 0,
                "pending": 0,
                "succeeded": 0,
                "failed": 0,
                "processed": 0,
                "is_complete": False,
                "batch_jobs": {}
            }
        
        current_status = trade_doc.get("status", "ready")
        
        # Skip if already complete or not yet submitted
        if current_status == "ready":
            return {
                "success": False,
                "trade_type": trade_type,
                "status": "ready",
                "message": "Batches not yet submitted",
                "total_batches": 0,
                "pending": 0,
                "succeeded": 0,
                "failed": 0,
                "processed": 0,
                "is_complete": False,
                "batch_jobs": {}
            }
        
        if current_status in ["batches_complete", "generated"]:
            batch_jobs = trade_doc.get("batch_jobs", {})
            # Count batches for the response
            total = len(batch_jobs)
            pending = sum(1 for j in batch_jobs.values() if j.get("status") == "pending")
            succeeded = sum(1 for j in batch_jobs.values() if j.get("status") == "succeeded")
            failed = sum(1 for j in batch_jobs.values() if j.get("status") == "failed")
            processed = sum(1 for j in batch_jobs.values() if j.get("status") == "processed")
            
            return {
                "success": True,
                "trade_type": trade_type,
                "status": current_status,
                "message": f"Already in '{current_status}' state",
                "total_batches": total,
                "pending": pending,
                "succeeded": succeeded,
                "failed": failed,
                "processed": processed,
                "is_complete": True,
                "batch_jobs": {ar: {"status": j.get("status", "unknown"), "batch_job_name": j.get("batch_job_name")} 
                              for ar, j in batch_jobs.items()}
            }
        
        batch_jobs = trade_doc.get("batch_jobs", {})
        
        # Poll each batch
        pending_count = 0
        succeeded_count = 0
        failed_count = 0
        processed_count = 0
        
        for aspect_ratio, job_info in batch_jobs.items():
            current_job_status = job_info.get("status", "unknown")
            
            # Skip if already processed or no batch name
            if current_job_status in ["processed", "submit_failed"]:
                if current_job_status == "processed":
                    processed_count += 1
                else:
                    failed_count += 1
                continue
            
            batch_job_name = job_info.get("batch_job_name")
            if not batch_job_name:
                failed_count += 1
                continue
            
            # Check status with Gemini
            status = self.gemini_service.is_batch_complete(batch_job_name)
            
            if status["is_complete"]:
                if status["is_success"]:
                    batch_jobs[aspect_ratio]["status"] = "succeeded"
                    batch_jobs[aspect_ratio]["completed_at"] = datetime.utcnow().isoformat()
                    succeeded_count += 1
                else:
                    batch_jobs[aspect_ratio]["status"] = "failed"
                    batch_jobs[aspect_ratio]["completed_at"] = datetime.utcnow().isoformat()
                    batch_jobs[aspect_ratio]["error"] = status.get("state", "Unknown error")
                    failed_count += 1
            else:
                batch_jobs[aspect_ratio]["status"] = "pending"
                batch_jobs[aspect_ratio]["gemini_state"] = status.get("state")
                pending_count += 1
        
        # Determine overall status
        total_batches = len(batch_jobs)
        all_complete = pending_count == 0
        
        if all_complete:
            new_status = "batches_complete"
        else:
            new_status = "batches_submitted"
        
        # Update MongoDB
        await collection.update_one(
            {"trade_type": trade_type},
            {
                "$set": {
                    "status": new_status,
                    "batch_jobs": batch_jobs,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "success": True,
            "trade_type": trade_type,
            "status": new_status,
            "total_batches": total_batches,
            "pending": pending_count,
            "succeeded": succeeded_count,
            "failed": failed_count,
            "processed": processed_count,
            "is_complete": all_complete,
            "batch_jobs": {ar: {"status": j["status"], "batch_job_name": j.get("batch_job_name")} 
                          for ar, j in batch_jobs.items()}
        }
    
    async def process_batches_for_trade(
        self,
        trade_type: str,
        org_id: str,
    ) -> Dict:
        """
        Download completed batches and ingest to S3/MongoDB
        
        NOW WITH IMAGE-LEVEL DEDUPLICATION:
        - Checks if each image already exists before uploading
        - Safe to run multiple times without duplicates
        
        Returns:
            Dict with processing results
        """
        
        collection = await get_mongo_collection("gemini_trade_queries", "trades")
        trade_doc = await collection.find_one({"trade_type": trade_type})
        
        if not trade_doc:
            return {
                "success": False,
                "trade_type": trade_type,
                "message": f"Trade '{trade_type}' not found",
                "total_images": 0,
                "uploaded_count": 0,
                "inserted_count": 0,
                "skipped_count": 0,
                "failed_count": 0,
                "errors": []
            }
        
        current_status = trade_doc.get("status", "ready")
        
        # Check if ready for processing
        if current_status == "generated":
            return {
                "success": True,
                "trade_type": trade_type,
                "message": "Already fully processed",
                "skipped": True,
                "total_images": 0,
                "uploaded_count": 0,
                "inserted_count": 0,
                "skipped_count": 0,
                "failed_count": 0,
                "errors": []
            }
        
        if current_status not in ["batches_complete", "batches_submitted"]:
            return {
                "success": False,
                "trade_type": trade_type,
                "message": f"Cannot process in '{current_status}' state",
                "total_images": 0,
                "uploaded_count": 0,
                "inserted_count": 0,
                "skipped_count": 0,
                "failed_count": 0,
                "errors": []
            }
        
        batch_jobs = trade_doc.get("batch_jobs", {})
        generation_config = trade_doc.get("generation_config", {})
        style_modifier = generation_config.get("style_modifier", "")
        model = generation_config.get("model", "gemini-3-pro-image-preview")
        image_size = generation_config.get("image_size", "2K")
        
        # Get media collection for deduplication checks
        media_collection = await self._get_media_collection()
        
        # Process each succeeded batch
        total_uploaded = 0
        total_inserted = 0
        total_skipped = 0  # NEW: Track skipped duplicates
        total_failed = 0
        all_errors = []
        
        for aspect_ratio, job_info in batch_jobs.items():
            job_status = job_info.get("status")
            
            # Skip if not succeeded or already processed
            if job_status != "succeeded":
                continue
            
            batch_job_name = job_info.get("batch_job_name")
            original_prompts = job_info.get("prompts", [])
            
            try:
                # Download results from Gemini
                results = self.gemini_service.download_batch_results(batch_job_name)
                
                # Process each result
                batch_uploaded = 0
                batch_inserted = 0
                batch_skipped = 0  # NEW
                batch_failed = 0
                batch_errors = []
                
                for i, result in enumerate(results):
                    try:
                        # Get original prompt
                        original_prompt = original_prompts[i] if i < len(original_prompts) else f"prompt_{i}"
                        full_prompt = f"{style_modifier}. {original_prompt}"
                        
                        # =====================================================
                        # NEW: CHECK FOR EXISTING IMAGE (DEDUPLICATION)
                        # Uses trade_type + original_prompt for robustness
                        # This allows re-running with new batches without duplicates
                        # =====================================================
                        existing = await media_collection.find_one({
                            "trade_type": trade_type,
                            "generation_metadata.original_prompt": original_prompt
                        })
                        
                        if existing:
                            # Already processed - skip upload and insert
                            batch_skipped += 1
                            continue
                        # =====================================================
                        
                        # Extract image data
                        if 'response' not in result or not result['response']:
                            batch_failed += 1
                            batch_errors.append({
                                "prompt_index": i,
                                "error": "No response in result"
                            })
                            continue
                        
                        # Find image in response
                        image_data = None
                        candidates = result['response'].get('candidates', [])
                        if candidates:
                            parts = candidates[0].get('content', {}).get('parts', [])
                            for part in parts:
                                if 'inlineData' in part and part['inlineData'].get('mimeType', '').startswith('image/'):
                                    image_data = base64.b64decode(part['inlineData']['data'])
                                    break
                        
                        if not image_data:
                            batch_failed += 1
                            batch_errors.append({
                                "prompt_index": i,
                                "error": "No image data found"
                            })
                            continue
                        
                        # Upload to S3
                        filename = f"generated_{uuid.uuid4()}.png"
                        image_metadata = await self._upload_generated_image_to_s3(
                            image_data=image_data,
                            org_id=org_id,
                            filename=filename
                        )
                        batch_uploaded += 1
                        
                        # Create MongoDB document
                        document = self._create_batch_generated_media_document(
                            image_metadata=image_metadata,
                            trade_type=trade_type,
                            original_prompt=original_prompt,
                            style_modifier=style_modifier,
                            full_prompt=full_prompt,
                            batch_job_name=batch_job_name,
                            model=model,
                            aspect_ratio=aspect_ratio,
                            image_size=image_size,
                        )
                        
                        # Insert to media collection
                        await media_collection.insert_one(document)
                        batch_inserted += 1
                        
                    except Exception as e:
                        batch_failed += 1
                        batch_errors.append({
                            "prompt_index": i,
                            "error": str(e)
                        })
                
                # Update batch job status
                batch_jobs[aspect_ratio]["status"] = "processed"
                batch_jobs[aspect_ratio]["processed_at"] = datetime.utcnow().isoformat()
                batch_jobs[aspect_ratio]["results"] = {
                    "uploaded_count": batch_uploaded,
                    "inserted_count": batch_inserted,
                    "skipped_count": batch_skipped,  # NEW
                    "failed_count": batch_failed,
                    "errors": batch_errors
                }
                
                total_uploaded += batch_uploaded
                total_inserted += batch_inserted
                total_skipped += batch_skipped  # NEW
                total_failed += batch_failed
                all_errors.extend(batch_errors)
                
            except Exception as e:
                batch_jobs[aspect_ratio]["status"] = "process_failed"
                batch_jobs[aspect_ratio]["error"] = str(e)
                all_errors.append({
                    "aspect_ratio": aspect_ratio,
                    "error": str(e)
                })
        
        # Check if all batches are processed
        all_processed = all(
            job.get("status") in ["processed", "failed", "submit_failed", "process_failed"]
            for job in batch_jobs.values()
        )
        
        if all_processed:
            new_status = "generated"
        else:
            new_status = "batches_complete"
        
        # Update trade document
        await collection.update_one(
            {"trade_type": trade_type},
            {
                "$set": {
                    "status": new_status,
                    "batch_jobs": batch_jobs,
                    "generation_progress": {
                        "total_prompts": sum(j.get("prompt_count", 0) for j in batch_jobs.values()),
                        "successful": total_inserted + total_skipped,  # Include skipped as "successful"
                        "failed": total_failed,
                        "skipped_duplicates": total_skipped  # NEW
                    },
                    "generation_completed_at": datetime.utcnow() if all_processed else None,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "success": True,
            "trade_type": trade_type,
            "status": new_status,
            "message": f"Processed {total_uploaded} new images, skipped {total_skipped} duplicates",
            "total_images": total_uploaded + total_skipped + total_failed,
            "uploaded_count": total_uploaded,
            "inserted_count": total_inserted,
            "skipped_count": total_skipped,  # NEW
            "failed_count": total_failed,
            "errors": all_errors
        }


# Dependency injection
def get_gemini_service() -> GeminiService:
    """Dependency for FastAPI"""
    return GeminiService()


def get_gemini_media_orchestrator(
    media_service: "MediaService",
    gemini_service: GeminiService,
) -> GeminiMediaOrchestrator:
    """
    Dependency injection for GeminiMediaOrchestrator.
    
    Args:
        media_service: MediaService instance (injected via Depends)
        gemini_service: GeminiService instance (injected via Depends)
    
    Returns:
        GeminiMediaOrchestrator instance
    """
    return GeminiMediaOrchestrator(media_service, gemini_service)