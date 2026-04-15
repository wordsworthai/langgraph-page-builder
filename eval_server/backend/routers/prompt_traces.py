"""Prompt traces API - fetch prompt call records by generation_version_id."""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from wwai_agent_orchestration.utils.landing_page_builder.db_utils import (
    fetch_by_generation_version_id,
    PROMPT_TRACES_COLLECTION,
    PROMPT_TRACES_DB_NAME,
)
from wwai_agent_orchestration.utils.checkpoint.checkpoint_utils import make_json_serializable

from .common import DEFAULT_MONGO_URI

router = APIRouter()


class PromptTracesRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    db_name: Optional[str] = PROMPT_TRACES_DB_NAME
    generation_version_id: str


@router.post("/api/prompt-traces")
async def get_prompt_traces(request: PromptTracesRequest):
    """
    Fetch all prompt traces for a generation_version_id.

    Returns the document with traces array, or empty traces if not found.
    """
    try:
        doc = fetch_by_generation_version_id(
            collection_name=PROMPT_TRACES_COLLECTION,
            generation_version_id=request.generation_version_id,
            db_name=request.db_name or PROMPT_TRACES_DB_NAME,
        )
        if doc is None:
            return {
                "generation_version_id": request.generation_version_id,
                "traces": [],
            }
        traces = doc.get("traces", [])
        return make_json_serializable({
            "generation_version_id": doc.get("generation_version_id", request.generation_version_id),
            "traces": traces,
            "updated_at": doc.get("updated_at"),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
