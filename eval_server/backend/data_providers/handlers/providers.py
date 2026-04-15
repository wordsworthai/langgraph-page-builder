import os
from typing import Any, Dict, Optional

from wwai_agent_orchestration.data.providers.business_profile_provider import BusinessProfileProvider
from wwai_agent_orchestration.data.providers.reviews_provider import ReviewsProvider
from wwai_agent_orchestration.data.providers.google_maps_provider import GoogleMapsProvider
from wwai_agent_orchestration.data.providers.yelp_provider import YelpProvider
from wwai_agent_orchestration.data.providers.media_assets_provider import MediaAssetsProvider
from wwai_agent_orchestration.data.providers.logo_provider import LogoProvider
from wwai_agent_orchestration.data.providers.business_photos_provider import BusinessPhotosProvider
from wwai_agent_orchestration.data.providers.review_photos_provider import ReviewPhotosProvider
from wwai_agent_orchestration.data.providers.models.media_assets import MediaAssetsInput
from wwai_agent_orchestration.data.providers.models.logo import LogoInput
from wwai_agent_orchestration.data.providers.models.scraped_photos import (
    BusinessPhotosInput,
    ReviewPhotosInput,
)

from data_providers.utils import require_arg, to_plain_object


def _get_yelp_provider() -> YelpProvider:
    return YelpProvider(rapidapi_key=os.getenv("RAPIDAPI_KEY", ""))


def run_business_profile(args: Dict[str, Any], allow_external: bool) -> Dict[str, Any]:
    del allow_external
    result = BusinessProfileProvider().get_by_business_id(require_arg(args, "business_id"))
    return to_plain_object(result)


def run_reviews(args: Dict[str, Any], allow_external: bool) -> Dict[str, Any]:
    del allow_external
    result = ReviewsProvider().get_by_business_id(
        business_id=require_arg(args, "business_id"),
        min_length=args.get("min_length"),
        min_rating=args.get("min_rating"),
        max_results=args.get("max_results"),
    )
    return to_plain_object(result)


def run_google_maps(args: Dict[str, Any], allow_external: bool) -> Optional[Dict[str, Any]]:
    del allow_external
    result = GoogleMapsProvider().get_by_business_id(require_arg(args, "business_id"))
    return to_plain_object(result) if result else None


def run_yelp(args: Dict[str, Any], allow_external: bool) -> Optional[Dict[str, Any]]:
    yelp_url = args.get("yelp_url")
    if yelp_url and not allow_external:
        raise PermissionError("Yelp URL scrape is blocked. Enable external calls to proceed.")
    result = _get_yelp_provider().get_by_business_id(
        business_id=require_arg(args, "business_id"),
        yelp_url=yelp_url,
    )
    return to_plain_object(result) if result else None


def run_media_assets(args: Dict[str, Any], allow_external: bool) -> Dict[str, Any]:
    del allow_external
    result = MediaAssetsProvider().get(
        MediaAssetsInput(
            business_id=require_arg(args, "business_id"),
            media_type=args.get("media_type", "all"),
            max_results=args.get("max_results"),
            retrieval_sources=args.get("retrieval_sources"),
        )
    )
    return to_plain_object(result)


def run_logos(args: Dict[str, Any], allow_external: bool) -> Dict[str, Any]:
    del allow_external
    result = LogoProvider().get(LogoInput(business_id=require_arg(args, "business_id")))
    return to_plain_object(result)


def run_business_photos(args: Dict[str, Any], allow_external: bool) -> Dict[str, Any]:
    del allow_external
    result = BusinessPhotosProvider().get(
        BusinessPhotosInput(
            business_id=require_arg(args, "business_id"),
            max_results=args.get("max_results"),
        )
    )
    return to_plain_object(result)


def run_review_photos(args: Dict[str, Any], allow_external: bool) -> Dict[str, Any]:
    del allow_external
    result = ReviewPhotosProvider().get(
        ReviewPhotosInput(
            business_id=require_arg(args, "business_id"),
            max_results=args.get("max_results"),
            min_rating=args.get("min_rating"),
        )
    )
    return to_plain_object(result)

