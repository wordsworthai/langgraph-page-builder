"""Task configuration endpoints. Config derived from taxonomy (source of truth)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from wwai_agent_orchestration.evals.human_feedback.taxonomy import (
    get_all_task_types,
    get_taxonomy,
)

from .common import make_json_serializable

router = APIRouter()


class TaskConfigRequest(BaseModel):
    task_type: str


def _taxonomy_to_task_config(taxonomy):
    """Build task config dict from taxonomy for frontend."""
    return {
        "display_name": taxonomy.display_name or taxonomy.task_type,
        "description": taxonomy.description or "",
        "mode": taxonomy.mode,
        "categories": [c.model_dump(mode="json") for c in taxonomy.categories],
    }


@router.get("/api/task-configs")
async def get_task_configs():
    """
    Get all task type configurations (derived from taxonomy).
    """
    try:
        task_types = get_all_task_types()
        task_configs = {}
        for task_type in task_types:
            taxonomy = get_taxonomy(task_type=task_type, version="v1")
            task_configs[task_type] = _taxonomy_to_task_config(taxonomy)

        return make_json_serializable({
            "task_configs": task_configs,
            "task_types": task_types,
        })
    except Exception as e:
        return make_json_serializable({"task_configs": {}, "task_types": [], "error": str(e)})


@router.post("/api/task-config")
async def get_single_task_config(request: TaskConfigRequest):
    """Get configuration for a specific task type (derived from taxonomy)."""
    try:
        taxonomy = get_taxonomy(task_type=request.task_type, version="v1")
        config = _taxonomy_to_task_config(taxonomy)
        return {"task_type": request.task_type, "config": config}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
