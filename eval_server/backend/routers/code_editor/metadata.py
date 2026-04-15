"""Section metadata endpoints for code editor."""
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

from template_json_builder.db.queries import (
    SECTION_REPO_PROD_DB,
    SECTION_REPO_SECTION_METADATA_COLLECTION,
    fetch_prod_section_documents,
)
from template_json_builder.code_generator.api_utils.section_metadata_utils import (
    regenerate_section_code_generation_config,
)

from ..common import DEFAULT_MONGO_URI, make_json_serializable

router = APIRouter()


class MetadataRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    section_id: str


class ParentRowsSaveRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    section_id: str
    parent_rows: List[Dict[str, Any]]


class SectionAiSignalsSaveRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    section_id: str
    section_ai_signals: Dict[str, Any]


def _get_section_metadata_field(
    raw_docs: Optional[Dict[str, Any]], field: str, default: Any
) -> Any:
    """Extract a top-level field from section_metadata."""
    if not raw_docs:
        return default
    section_metadata = raw_docs.get("section_metadata") or {}
    val = section_metadata.get(field)
    return val if val is not None else default


@router.post("/api/sections/metadata/device-specific-media")
async def get_device_specific_media_metadata(request: MetadataRequest):
    """
    Fetch device_specific_media_metadata for a section.
    Structure: { desktop: {...}, mobile: {...} }.
    Returns {} when field is missing.
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
        data = _get_section_metadata_field(
            raw_docs, "device_specific_media_metadata", {}
        )
        payload = {"device_specific_media_metadata": data if data is not None else {}}
        return make_json_serializable(payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch device-specific media metadata: {str(e)}",
        )


@router.post("/api/sections/metadata/parent-rows")
async def get_parent_rows(request: MetadataRequest):
    """
    Fetch parent_rows for a section.
    Structure: list of { element_type, element_id, block_type, parent_element_id, parent_block_type }.
    Returns [] when field is missing.
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
        data = _get_section_metadata_field(raw_docs, "parent_rows", [])
        payload = {"parent_rows": data if isinstance(data, list) else []}
        return make_json_serializable(payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch parent rows: {str(e)}",
        )


@router.post("/api/sections/metadata/section-ai-signals")
async def get_section_ai_signals(request: MetadataRequest):
    """
    Fetch section_ai_signals for a section.
    Structure: { content_description, styling_description, section_layout_description }.
    Returns {} when field is missing.
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
        data = _get_section_metadata_field(raw_docs, "section_ai_signals", {})
        payload = {"section_ai_signals": data if isinstance(data, dict) else {}}
        return make_json_serializable(payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch section AI signals: {str(e)}",
        )


@router.post("/api/sections/metadata/parent-rows/save")
async def save_parent_rows(request: ParentRowsSaveRequest):
    """
    Save parent_rows to section metadata.
    Returns { ok: true } on success; 404 if section not found.
    """
    section_id = (request.section_id or "").strip()
    if not section_id:
        raise HTTPException(status_code=400, detail="section_id is required")
    if request.parent_rows is None:
        raise HTTPException(status_code=400, detail="parent_rows is required")
    try:
        client = AsyncIOMotorClient(request.mongo_uri or DEFAULT_MONGO_URI)
        db = client[SECTION_REPO_PROD_DB]
        collection = db[SECTION_REPO_SECTION_METADATA_COLLECTION]
        result = await collection.update_one(
            {"_id": ObjectId(section_id)},
            {"$set": {"parent_rows": request.parent_rows}},
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
            detail=f"Failed to save parent rows: {str(e)}",
        )


@router.post("/api/sections/metadata/section-ai-signals/save")
async def save_section_ai_signals(request: SectionAiSignalsSaveRequest):
    """
    Save section_ai_signals to section metadata.
    Returns { ok: true } on success; 404 if section not found.
    """
    section_id = (request.section_id or "").strip()
    if not section_id:
        raise HTTPException(status_code=400, detail="section_id is required")
    if request.section_ai_signals is None:
        raise HTTPException(status_code=400, detail="section_ai_signals is required")
    try:
        client = AsyncIOMotorClient(request.mongo_uri or DEFAULT_MONGO_URI)
        db = client[SECTION_REPO_PROD_DB]
        collection = db[SECTION_REPO_SECTION_METADATA_COLLECTION]
        result = await collection.update_one(
            {"_id": ObjectId(section_id)},
            {"$set": {"section_ai_signals": request.section_ai_signals}},
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
            detail=f"Failed to save section AI signals: {str(e)}",
        )


@router.post("/api/sections/metadata/regenerate-section-code-generation-config")
async def regenerate_section_code_config(request: MetadataRequest):
    """
    Regenerate section_code_generation_config from schema and element level properties.
    Returns { ok: true } on success; 404 if section not found or schema missing.
    """
    section_id = (request.section_id or "").strip()
    if not section_id:
        raise HTTPException(status_code=400, detail="section_id is required")
    try:
        client = AsyncIOMotorClient(request.mongo_uri or DEFAULT_MONGO_URI)
        db = client[SECTION_REPO_PROD_DB]
        ok = await regenerate_section_code_generation_config(section_id=section_id, db=db)
        client.close()
        if not ok:
            raise HTTPException(
                status_code=404,
                detail="Section not found or schema missing",
            )
        return make_json_serializable({"ok": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to regenerate section code generation config: {str(e)}",
        )
