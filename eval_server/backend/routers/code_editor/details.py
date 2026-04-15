"""Section details endpoint for code editor preview."""
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient

from template_json_builder.db.queries import (
    SECTION_REPO_PROD_DB,
    SECTION_REPO_SECTIONS_COLLECTION,
)

from ..common import DEFAULT_MONGO_URI, make_json_serializable

router = APIRouter()


class SectionDetailsRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    section_id: str


@router.post("/api/sections/details")
async def get_section_details(request: SectionDetailsRequest):
    """
    Fetch section details (desktop_image_url, mobile_image_url, etc.) for preview.
    Uses section_repo_prod.sections from template_json_builder.
    """
    section_id = (request.section_id or "").strip()
    if not section_id:
        raise HTTPException(status_code=400, detail="section_id is required")
    try:
        oid = ObjectId(section_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid section_id format")
    try:
        client = MongoClient(request.mongo_uri or DEFAULT_MONGO_URI)
        db = client[SECTION_REPO_PROD_DB]
        section_doc = db[SECTION_REPO_SECTIONS_COLLECTION].find_one({"_id": oid})
        if not section_doc:
            raise HTTPException(status_code=404, detail=f"Section not found: {section_id}")
        details = {
            "section_l0": section_doc.get("section_l0"),
            "section_l1": section_doc.get("section_l1"),
            "section_label": section_doc.get("section_label"),
            "desktop_image_url": section_doc.get("desktop_image_url"),
            "mobile_image_url": section_doc.get("mobile_image_url"),
        }
        return make_json_serializable(details)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch section details: {str(e)}",
        )
