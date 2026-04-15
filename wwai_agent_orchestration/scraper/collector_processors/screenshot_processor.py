from typing import Dict, Any, List, Optional
import os
from template_json_builder.utils.s3_upload import get_s3_client, upload_file_to_s3

def process_results_for_screenshot(
    results_by_profile: Dict[str, Any],
    s3_file_dir: str,
    bucket_name: Optional[str] = None,
    bucket_location: Optional[str] = None,
    overwrite: bool = True,
) -> Dict[str, Any]:
    """
    Process and upload all section screenshots to S3.
    
    Returns:
        Dict with:
        - desktop_screenshots: List of dicts with section_id, index, s3_url, screenshot_path
        - mobile_screenshots: List of dicts with section_id, index, s3_url, screenshot_path
        - desktop_s3_url: First desktop screenshot URL (for backward compatibility)
        - mobile_s3_url: First mobile screenshot URL (for backward compatibility)
    """
    client, err = get_s3_client()
    if client is None:
        raise RuntimeError(f"Failed to create S3 client: {err}")

    # Validate required parameters
    if not s3_file_dir:
        raise ValueError("s3_file_dir cannot be empty or None")
    if not isinstance(s3_file_dir, str):
        raise ValueError(f"s3_file_dir must be a string, got {type(s3_file_dir)}")

    # Use defaults if not provided (matching upload_file_to_s3 defaults)
    final_bucket_name = bucket_name or os.environ.get("S3_BUCKET_NAME", "")
    final_bucket_location = bucket_location or os.environ.get("S3_BUCKET_REGION", "")

    def upload_all_screenshots(profile_key: str, prefix: str) -> List[Dict[str, Any]]:
        """
        Upload all screenshots for a given profile.
        Returns list of dicts with section_id, index, s3_url, screenshot_path.
        """
        profile = results_by_profile.get(profile_key, {})
        screenshots = profile.get("section_screenshots", [])

        if not screenshots:
            return []

        uploaded_screenshots = []
        
        for idx, screenshot_data in enumerate(screenshots):
            path = screenshot_data.get("screenshot_path")
            section_id = screenshot_data.get("section_id", f"section_{idx}")
            screenshot_index = screenshot_data.get("index", idx)
            
            if not path or not isinstance(path, str) or not os.path.isfile(path):
                continue
            
            try:
                # Use section_id in filename prefix to make it unique
                filename_prefix = f"{prefix}_{section_id}"
                status_or = upload_file_to_s3(
                    client=client,
                    local_filename=path,
                    s3_file_dir=s3_file_dir,
                    filename_prefix=filename_prefix,
                    bucket_name=final_bucket_name,
                    bucket_location=final_bucket_location,
                    overwrite=overwrite,
                    content_type="image/png",
                )
                
                if not status_or.status:
                    # Continue with other screenshots instead of failing completely
                    continue
                
                s3_url = status_or.response.get("s3_url")
                
                uploaded_screenshots.append({
                    "section_id": section_id,
                    "index": screenshot_index,
                    "s3_url": s3_url,
                    "screenshot_path": path,
                })
                
            except Exception:
                # Continue with other screenshots instead of failing completely
                continue
        
        return uploaded_screenshots

    # Upload all desktop screenshots
    desktop_screenshots = upload_all_screenshots("desktop", "desktop")
    
    # Upload all mobile screenshots
    mobile_screenshots = upload_all_screenshots("mobile", "mobile")

    # Build output with all screenshots and backward compatibility
    output = {
        "desktop_screenshots": desktop_screenshots,
        "mobile_screenshots": mobile_screenshots,
        # Backward compatibility: first screenshot URLs
        "desktop_s3_url": desktop_screenshots[0]["s3_url"] if desktop_screenshots else None,
        "mobile_s3_url": mobile_screenshots[0]["s3_url"] if mobile_screenshots else None,
    }

    return output