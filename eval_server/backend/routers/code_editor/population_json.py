"""Population JSON endpoints for code editor."""
from typing import Any, Dict, Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

from template_json_builder.code_generator.api_utils.population_json_utils import (
    get_reference_template_json_from_boilerplate,
)
from template_json_builder.db.queries import (
    SECTION_REPO_PROD_DB,
    SECTION_REPO_SECTION_METADATA_COLLECTION,
    fetch_prod_section_documents,
)

from ..common import DEFAULT_MONGO_URI, make_json_serializable

router = APIRouter()


class PopulationJsonRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    section_id: str


class PopulationJsonSaveRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    section_id: str
    populated_template_json: Dict[str, Any]


@router.post("/api/sections/population-json")
async def get_population_json(request: PopulationJsonRequest):
    """
    Fetch populated_template_json from section metadata.
    Uses template_json_builder get_populated_template_json.
    Returns {} when field is missing so modal can show empty editable object.
    """
    section_id = (request.section_id or "").strip()
    if not section_id:
        raise HTTPException(status_code=400, detail="section_id is required")
    try:
        client = AsyncIOMotorClient(request.mongo_uri or DEFAULT_MONGO_URI)
        db = client[SECTION_REPO_PROD_DB]
        raw_docs = await fetch_prod_section_documents(section_id=section_id, db=db)
        client.close()
        if not raw_docs:
            raise HTTPException(status_code=404, detail=f"Section not found: {section_id}")
        section_metadata = raw_docs.get("section_metadata") or {}
        ipsum = section_metadata.get("ipsum_lorem_metadata") or {}
        data = ipsum.get("populated_template_json")
        payload = {"populated_template_json": data if data is not None else {}}
        return make_json_serializable(payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch population JSON: {str(e)}",
        )


@router.post("/api/sections/population-json/save")
async def save_population_json(request: PopulationJsonSaveRequest):
    """
    Save populated_template_json to section metadata.
    Uses same logic as template_json_builder update_populated_template_json.
    Returns success when matched (matched_count > 0), even if no change (modified_count == 0).
    """
    section_id = (request.section_id or "").strip()
    if not section_id:
        raise HTTPException(status_code=400, detail="section_id is required")
    if request.populated_template_json is None:
        raise HTTPException(status_code=400, detail="populated_template_json is required")
    try:
        client = AsyncIOMotorClient(request.mongo_uri or DEFAULT_MONGO_URI)
        db = client[SECTION_REPO_PROD_DB]
        collection = db[SECTION_REPO_SECTION_METADATA_COLLECTION]
        result = await collection.update_one(
            {"_id": ObjectId(section_id)},
            {"$set": {"ipsum_lorem_metadata.populated_template_json": request.populated_template_json}},
        )
        client.close()
        if result.matched_count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Section not found: {section_id}",
            )
        return make_json_serializable({"ok": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save population JSON: {str(e)}",
        )


@router.post("/api/sections/reference-template-json")
async def get_reference_template_json(request: PopulationJsonRequest):
    """
    Fetch reference_template_json from boilerplate for a section.
    Uses template_json_builder get_reference_template_json_from_boilerplate.
    Returns {} when not available so modal can show empty state.
    """
    section_id = (request.section_id or "").strip()
    if not section_id:
        raise HTTPException(status_code=400, detail="section_id is required")
    try:
        client = AsyncIOMotorClient(request.mongo_uri or DEFAULT_MONGO_URI)
        db = client[SECTION_REPO_PROD_DB]
        data = await get_reference_template_json_from_boilerplate(section_id=section_id, db=db)
        client.close()
        payload = {"reference_template_json": data if data is not None else {}}
        return make_json_serializable(payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch reference template JSON: {str(e)}",
        )
