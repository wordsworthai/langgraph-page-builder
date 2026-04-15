"""Business profile endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from wwai_agent_orchestration.data.providers.business_profile_provider import BusinessProfileProvider

from .common import make_json_serializable

router = APIRouter()


class BusinessProfileRequest(BaseModel):
    business_id: str


@router.post("/api/business-profile")
async def get_business_profile(request: BusinessProfileRequest):
    """
    Get business profile information for a given business_id.
    """
    try:
        provider = BusinessProfileProvider()
        result = provider.get_by_business_id(request.business_id)

        profile_dict = result.model_dump() if hasattr(result, 'model_dump') else result.dict()
        return make_json_serializable({"business_profile": profile_dict})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch business profile: {str(e)}")
