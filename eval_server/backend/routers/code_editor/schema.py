"""Section schema endpoint for code editor."""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

from template_json_builder.code_generator.api_utils.wwai_schema import (
    get_schema_for_section,
    insert_schema_version,
)
from template_json_builder.db.queries import SECTION_REPO_PROD_DB

from ..common import DEFAULT_MONGO_URI, make_json_serializable

router = APIRouter()


class SchemaRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    section_id: str


class SchemaSaveRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    section_id: str
    schema: List[Dict[str, Any]]


@router.post("/api/sections/schema")
async def get_section_schema(request: SchemaRequest):
    """
    Fetch the WWAI schema for a section (latest version's schema_data).
    Uses template_json_builder get_schema_for_section.
    """
    section_id = (request.section_id or "").strip()
    if not section_id:
        raise HTTPException(status_code=400, detail="section_id is required")
    try:
        client = AsyncIOMotorClient(request.mongo_uri or DEFAULT_MONGO_URI)
        db = client[SECTION_REPO_PROD_DB]
        schema_data = await get_schema_for_section(section_id=section_id, db=db)
        client.close()
        if schema_data is None:
            raise HTTPException(status_code=404, detail=f"Schema not found for section: {section_id}")
        return make_json_serializable(schema_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch schema: {str(e)}",
        )


@router.post("/api/sections/schema/save")
async def save_section_schema(request: SchemaSaveRequest):
    """
    Save a new schema version for a section.
    Uses template_json_builder insert_schema_version.
    """
    section_id = (request.section_id or "").strip()
    if not section_id:
        raise HTTPException(status_code=400, detail="section_id is required")
    if not request.schema or not isinstance(request.schema, list):
        raise HTTPException(status_code=400, detail="schema array is required")
    try:
        client = AsyncIOMotorClient(request.mongo_uri or DEFAULT_MONGO_URI)
        db = client[SECTION_REPO_PROD_DB]
        schema_data = {"schema": request.schema}
        result = await insert_schema_version(
            section_id=section_id,
            schema_data=schema_data,
            db=db,
            label="user",
        )
        client.close()
        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Section or schema document not found",
            )
        return make_json_serializable({"ok": True, "version": result.get("version")})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save schema: {str(e)}",
        )
