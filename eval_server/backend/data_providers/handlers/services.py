from typing import Any, Dict

from wwai_agent_orchestration.data.services.media.media_service import MediaService

from data_providers.utils import require_arg

_MEDIA_SERVICE = MediaService()


def run_media_match_images(args: Dict[str, Any], allow_external: bool) -> Dict[str, Any]:
    del allow_external
    return _MEDIA_SERVICE.match_images_for_slots(
        business_id=require_arg(args, "business_id"),
        slots=args.get("slots", []),
        retrieval_sources=args.get("retrieval_sources"),
        max_recommendations_per_slot=args.get("max_recommendations_per_slot", 1),
    )


def run_media_match_videos(args: Dict[str, Any], allow_external: bool) -> Dict[str, Any]:
    del allow_external
    return _MEDIA_SERVICE.match_videos_for_slots(
        business_id=require_arg(args, "business_id"),
        slots=args.get("slots", []),
        retrieval_sources=args.get("retrieval_sources"),
        max_recommendations_per_slot=args.get("max_recommendations_per_slot", 1),
    )

