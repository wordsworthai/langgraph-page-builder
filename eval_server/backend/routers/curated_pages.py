"""Curated pages API for Curated Page Builder."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from wwai_agent_orchestration.utils.landing_page_builder.template_utils import (
    get_curated_pages,
)
from wwai_agent_orchestration.utils.landing_page_builder.template import curated_options

router = APIRouter()


class SaveCuratedPageRequest(BaseModel):
    page_path: str = Field(..., description="Unique path for the page (e.g. /about)")
    page_title: str = Field(..., description="Display title")
    page_description: Optional[str] = Field(default=None, description="Optional description")
    section_ids: List[str] = Field(default_factory=list, description="Ordered list of section IDs")


@router.get("/api/curated-pages")
async def get_curated_pages_endpoint():
    """
    Fetch all curated pages from section_repo_prod.curated_pages.
    Returns pages with page_path, page_title, page_description, section_ids, section_desktop_urls.
    """
    response = get_curated_pages()
    return {"pages": [p.model_dump() for p in response.pages]}


@router.post("/api/curated-pages/save")
async def save_curated_page_endpoint(request: SaveCuratedPageRequest):
    """
    Upsert a curated page. Creates or updates by page_path.
    """
    try:
        curated_options.save_curated_page(
            page_path=request.page_path,
            page_title=request.page_title,
            page_description=request.page_description,
            section_ids=request.section_ids or [],
        )
        return {"success": True, "page_path": request.page_path}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
