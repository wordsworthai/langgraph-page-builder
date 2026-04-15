"""Section repository and compile endpoints."""
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient

from wwai_agent_orchestration.data.repositories.section_repository import SectionRepositoryService
from wwai_agent_orchestration.utils.landing_page_builder.template_utils import (
    compile_section_with_ipsum_lorem,
    compile_section_to_html,
    compile_batch_section_ids_to_html,
)

from .common import (
    DEFAULT_MONGO_URI,
    DocumentNotFoundError,
    make_json_serializable,
)

router = APIRouter()


def _get_section_repo_service(mongo_uri: str) -> SectionRepositoryService:
    """Build SectionRepositoryService with db_manager backed by MongoClient(mongo_uri)."""
    client = MongoClient(mongo_uri or DEFAULT_MONGO_URI)
    return SectionRepositoryService(db_manager=client)


class SectionRepoCategoriesRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    query_filter: Optional[Dict[str, Any]] = None


class SectionRepoSectionsRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    l0_category: Optional[str] = None
    l1_category: Optional[str] = None
    query_filter: Optional[Dict[str, Any]] = None


class SectionRepoDistinctRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    field: str  # "tag", "status", or "semantic_tags"


class SectionRepoUpdateStatusRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    section_id: str
    status: str


class SectionRepoGetSectionRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    section_id: str


class SectionRepoUpdateSemanticTagsRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    section_id: str
    semantic_tags: List[str]


class SectionTemplateRequest(BaseModel):
    section_id: str


class CompileSectionRequest(BaseModel):
    section_id: str
    section_mapping: Optional[Dict[str, Any]] = None


class CompileBatchSectionRequest(BaseModel):
    section_ids: List[str] = []


STAGING_DB_NAME = "section_repo_dev"
STAGING_COLLECTION_NAME = "section_repo_staging"


class StagingSaveRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    section_id: str
    section_mapping: Dict[str, Any]


class StagingGetRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    section_id: str


class StagingListRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    section_ids: Optional[List[str]] = None


class StagingDeleteRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    section_id: str


def _get_staging_collection(mongo_uri: str):
    """Get the staging collection for section drafts."""
    client = MongoClient(mongo_uri or DEFAULT_MONGO_URI)
    db = client[STAGING_DB_NAME]
    return db[STAGING_COLLECTION_NAME]


@router.post("/api/sections/staging/save")
async def staging_save(request: StagingSaveRequest):
    """Upsert a section draft to the staging collection."""
    section_id = (request.section_id or "").strip()
    if not section_id:
        raise HTTPException(status_code=400, detail="section_id is required")
    if not request.section_mapping:
        raise HTTPException(status_code=400, detail="section_mapping is required")
    try:
        coll = _get_staging_collection(request.mongo_uri or DEFAULT_MONGO_URI)
        now = datetime.utcnow()
        doc = {
            "section_id": section_id,
            "section_mapping": request.section_mapping,
            "updated_at": now,
        }
        existing = coll.find_one({"section_id": section_id})
        if existing:
            coll.update_one(
                {"section_id": section_id},
                {"$set": doc},
            )
        else:
            doc["created_at"] = now
            coll.insert_one(doc)
        return make_json_serializable({"ok": True, "section_id": section_id})
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save staging: {str(e)}",
        )


@router.post("/api/sections/staging/get")
async def staging_get(request: StagingGetRequest):
    """Fetch a section draft from staging. Returns 404 if not found."""
    section_id = (request.section_id or "").strip()
    if not section_id:
        raise HTTPException(status_code=400, detail="section_id is required")
    try:
        coll = _get_staging_collection(request.mongo_uri or DEFAULT_MONGO_URI)
        doc = coll.find_one({"section_id": section_id})
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"No draft found for section_id={section_id}",
            )
        return make_json_serializable(doc["section_mapping"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch staging: {str(e)}",
        )


@router.post("/api/sections/staging/list")
async def staging_list(request: StagingListRequest):
    """List staging documents, optionally filtered by section_ids."""
    try:
        coll = _get_staging_collection(request.mongo_uri or DEFAULT_MONGO_URI)
        query = {}
        if request.section_ids:
            query["section_id"] = {"$in": [s.strip() for s in request.section_ids if s and s.strip()]}
        docs = list(coll.find(query, {"section_id": 1, "created_at": 1, "updated_at": 1}))
        items = [
            {
                "section_id": d["section_id"],
                "created_at": d.get("created_at"),
                "updated_at": d.get("updated_at"),
            }
            for d in docs
        ]
        return make_json_serializable({"items": items})
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list staging: {str(e)}",
        )


@router.post("/api/sections/staging/delete")
async def staging_delete(request: StagingDeleteRequest):
    """Delete a section draft from the staging collection."""
    section_id = (request.section_id or "").strip()
    if not section_id:
        raise HTTPException(status_code=400, detail="section_id is required")
    try:
        coll = _get_staging_collection(request.mongo_uri or DEFAULT_MONGO_URI)
        result = coll.delete_one({"section_id": section_id})
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No draft found for section_id={section_id}",
            )
        return make_json_serializable({"ok": True, "section_id": section_id})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete staging: {str(e)}",
        )


@router.post("/api/data/section-repo/categories")
async def get_section_repo_categories(request: SectionRepoCategoriesRequest):
    """Get unique L0 categories from the section repository."""
    try:
        service = _get_section_repo_service(request.mongo_uri or DEFAULT_MONGO_URI)
        query_filter = request.query_filter or {"status": "ACTIVE", "tag": "smb"}
        categories = service.get_unique_l0_categories(
            query_filter=query_filter,
        )
        return make_json_serializable({"categories": categories})
    except DocumentNotFoundError:
        return make_json_serializable({"categories": []})
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch section repo categories: {str(e)}"
        )


@router.post("/api/data/section-repo/sections")
async def get_section_repo_sections(request: SectionRepoSectionsRequest):
    """Get sections from the section repository, optionally filtered by L0 category."""
    try:
        service = _get_section_repo_service(request.mongo_uri or DEFAULT_MONGO_URI)
        query_filter = request.query_filter or {"status": "ACTIVE", "tag": "smb"}

        if request.l0_category:
            sections = service.get_sections_by_l0(
                l0_category=request.l0_category,
                query_filter=query_filter,
            )
        else:
            sections = service.fetch_sections_with_metadata(
                query_filter=query_filter,
            )

        for s in sections:
            if "_id" in s:
                s["section_id"] = str(s.get("_id", s.get("section_id", "")))
            elif "section_id" not in s:
                s["section_id"] = str(s.get("_id", ""))

        if request.l1_category:
            sections = [s for s in sections if s.get("section_l1") == request.l1_category]

        return make_json_serializable({"sections": sections})
    except DocumentNotFoundError:
        return make_json_serializable({"sections": []})
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch section repo sections: {str(e)}"
        )


@router.post("/api/data/section-repo/distinct")
async def get_section_repo_distinct(request: SectionRepoDistinctRequest):
    """Get distinct values for a field (tag, status, or semantic_tags) from the sections collection."""
    if request.field not in ("tag", "status", "semantic_tags"):
        raise HTTPException(status_code=400, detail="field must be 'tag', 'status', or 'semantic_tags'")
    try:
        service = _get_section_repo_service(request.mongo_uri or DEFAULT_MONGO_URI)
        if request.field == "tag":
            values = service.get_distinct_tags()
        elif request.field == "status":
            values = service.get_distinct_statuses()
        else:
            values = service.get_distinct_semantic_tags()
        return make_json_serializable({"values": values})
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch distinct {request.field}: {str(e)}"
        )


@router.post("/api/data/section-repo/sections/update-status")
async def update_section_status(request: SectionRepoUpdateStatusRequest):
    """Update a section's status (e.g. set to INACTIVE)."""
    try:
        service = _get_section_repo_service(request.mongo_uri or DEFAULT_MONGO_URI)
        modified_count = service.update_section_status(
            section_id=request.section_id,
            status=request.status,
        )
        return make_json_serializable({"modified_count": modified_count})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update section status: {str(e)}"
        )


@router.post("/api/data/section-repo/sections/get-by-id")
async def get_section_by_id(request: SectionRepoGetSectionRequest):
    """Fetch a section by _id and return DeveloperSection fields."""
    section_id = (request.section_id or "").strip()
    if not section_id:
        raise HTTPException(status_code=400, detail="section_id is required")
    try:
        service = _get_section_repo_service(request.mongo_uri or DEFAULT_MONGO_URI)
        section = service.get_developer_section_by_id(section_id=section_id)
        if not section:
            raise HTTPException(
                status_code=404,
                detail=f"Section not found: {section_id}",
            )
        return make_json_serializable({"section": section})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch section: {str(e)}"
        )


@router.post("/api/data/section-repo/sections/update-semantic-tags")
async def update_section_semantic_tags(request: SectionRepoUpdateSemanticTagsRequest):
    """Update a section's semantic_tags. Replaces the entire list."""
    section_id = (request.section_id or "").strip()
    if not section_id:
        raise HTTPException(status_code=400, detail="section_id is required")
    try:
        service = _get_section_repo_service(request.mongo_uri or DEFAULT_MONGO_URI)
        modified_count = service.update_section_semantic_tags(
            section_id=section_id,
            semantic_tags=request.semantic_tags or [],
        )
        return make_json_serializable({"modified_count": modified_count})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update semantic tags: {str(e)}"
        )


@router.post("/api/sections/compile-batch")
async def compile_batch_section_endpoint(request: CompileBatchSectionRequest):
    """
    Compile multiple section IDs to HTML. Uses ipsum_lorem only.
    Returns compiled HTML for preview (e.g. Curated Page Builder).
    """
    section_ids = [str(sid).strip() for sid in (request.section_ids or []) if str(sid).strip()]
    try:
        compiled_html = await compile_batch_section_ids_to_html(section_ids)
        return {"compiled_html": compiled_html}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch compilation failed: {str(e)}",
        )


@router.post("/api/sections/compile")
async def compile_section_endpoint(request: CompileSectionRequest):
    """
    Compile a section to HTML. If section_mapping is provided (edited content from the
    code editor), it overlays the original. Returns compiled HTML for the preview panel.
    """
    section_id = (request.section_id or "").strip()
    if not section_id:
        raise HTTPException(status_code=400, detail="section_id is required")
    try:
        compiled_html = await compile_section_to_html(
            section_id=section_id,
            edited_section_mapping=request.section_mapping,
        )
        return {"compiled_html": compiled_html}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Compilation failed: {str(e)}",
        )


@router.post("/api/sections/template")
async def get_section_template(request: SectionTemplateRequest):
    """
    Compile a single section and return its section_mapping (SectionData-compatible).
    Uses ipsum_lorem template JSON (no autopopulation).
    """
    section_id = (request.section_id or "").strip()
    if not section_id:
        raise HTTPException(status_code=400, detail="section_id is required")
    try:
        tbo = await compile_section_with_ipsum_lorem(section_id)
        if not tbo.sections or not tbo.enabled_section_ids:
            raise HTTPException(
                status_code=404,
                detail=f"No section data returned for section_id={section_id}",
            )
        unique_id = tbo.enabled_section_ids[0]
        section_build_data = tbo.sections.get(unique_id)
        if not section_build_data:
            raise HTTPException(
                status_code=404,
                detail=f"Section build data not found for section_id={section_id}",
            )
        section_mapping = section_build_data.section_mapping
        return make_json_serializable(section_mapping)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compile section: {str(e)}",
        )
