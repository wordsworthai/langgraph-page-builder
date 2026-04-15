"""Promote staging code to main section repo."""
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

from template_json_builder.code_generator.api_utils.code_utils import insert_code_version
from template_json_builder.db.queries import SECTION_REPO_PROD_DB

from ..common import DEFAULT_MONGO_URI, make_json_serializable

# Staging DB/collection (matches section_repo.py)
STAGING_DB_NAME = "section_repo_dev"
STAGING_COLLECTION_NAME = "section_repo_staging"

router = APIRouter()


class PromoteRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    section_id: str
    section_mapping: Dict[str, Any]


@router.post("/api/sections/code/promote")
async def promote_to_main(request: PromoteRequest):
    """
    Save staging code to main section repo (section_codeblocks), then delete staging draft.
    Uses template_json_builder insert_code_version.
    """
    section_id = (request.section_id or "").strip()
    if not section_id:
        raise HTTPException(status_code=400, detail="section_id is required")
    if not request.section_mapping:
        raise HTTPException(status_code=400, detail="section_mapping is required")
    try:
        client = AsyncIOMotorClient(request.mongo_uri or DEFAULT_MONGO_URI)
        db = client[SECTION_REPO_PROD_DB]
        result = await insert_code_version(
            section_id=section_id,
            section_mapping=request.section_mapping,
            db=db,
        )
        if result is None:
            client.close()
            raise HTTPException(
                status_code=404,
                detail="Section or codeblock document not found",
            )
        # Delete staging draft
        staging_db = client[STAGING_DB_NAME]
        staging_coll = staging_db[STAGING_COLLECTION_NAME]
        await staging_coll.delete_one({"section_id": section_id})
        client.close()
        return make_json_serializable({"ok": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to promote to main: {str(e)}",
        )
