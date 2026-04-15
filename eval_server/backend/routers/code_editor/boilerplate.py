"""Boilerplate section endpoint for code editor."""
from typing import Optional

from fastapi import APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

from template_json_builder.code_generator.api_utils.boilerplate_code_generation import (
    boilerplate_code_generator,
)
from template_json_builder.db.queries import SECTION_REPO_PROD_DB

from ..common import DEFAULT_MONGO_URI, make_json_serializable

router = APIRouter()


class BoilerplateRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    section_id: str


@router.post("/api/sections/boilerplate/get")
async def boilerplate_get(request: BoilerplateRequest):
    """
    Fetch boilerplate section_mapping for a section.
    Uses boilerplate_code_generator from template_json_builder.
    Returns SectionData-compatible dict.
    """
    section_id = (request.section_id or "").strip()
    if not section_id:
        raise HTTPException(status_code=400, detail="section_id is required")
    try:
        client = AsyncIOMotorClient(request.mongo_uri or DEFAULT_MONGO_URI)
        db = client[SECTION_REPO_PROD_DB]
        section = await boilerplate_code_generator(section_id=section_id, db=db)
        client.close()
        return make_json_serializable(section.model_dump())
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch boilerplate: {str(e)}",
        )
