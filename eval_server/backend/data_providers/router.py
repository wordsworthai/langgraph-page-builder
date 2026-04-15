import time
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from wwai_agent_orchestration.utils.checkpoint.checkpoint_utils import make_json_serializable
from data_providers.registry import DATA_DEBUG_TARGETS
from data_providers.utils import to_plain_object


router = APIRouter()

_REQUIRED_TARGET_FIELDS = ("label", "category", "description", "external_call", "sample_args")


def _serialize_catalog_target(target: str, config: Dict[str, Any]) -> Dict[str, Any]:
    missing = [field for field in _REQUIRED_TARGET_FIELDS if field not in config]
    if missing:
        raise ValueError(f"Invalid target config for '{target}', missing fields: {', '.join(missing)}")
    return {
        "target": target,
        "label": config["label"],
        "category": config["category"],
        "description": config["description"],
        "external_call": config["external_call"],
        "sample_args": config["sample_args"],
        "result_renderer": config.get("result_renderer"),
        "random_args_generator": config.get("random_args_generator"),
    }


class DataDebugRunRequest(BaseModel):
    target: str
    args: Optional[Dict[str, Any]] = None
    allow_external: bool = False


@router.get("/api/data/debug/catalog")
async def get_data_debug_catalog():
    targets = []
    for target, config in DATA_DEBUG_TARGETS.items():
        targets.append(_serialize_catalog_target(target, config))
    targets.sort(key=lambda item: (item["category"], item["label"]))
    return make_json_serializable({"targets": targets})


@router.post("/api/data/debug/run")
async def run_data_debug_target(request: DataDebugRunRequest):
    target_config = DATA_DEBUG_TARGETS.get(request.target)
    if not target_config:
        raise HTTPException(status_code=404, detail=f"Unknown debug target: {request.target}")

    started = time.perf_counter()
    args = request.args or {}

    try:
        result = target_config["handler"](args, request.allow_external)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return make_json_serializable(
            {
                "success": True,
                "target": request.target,
                "result": to_plain_object(result),
                "error": None,
                "meta": {
                    "external_call": bool(target_config["external_call"]),
                    "elapsed_ms": elapsed_ms,
                },
            }
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return make_json_serializable(
            {
                "success": False,
                "target": request.target,
                "result": None,
                "error": str(exc),
                "meta": {
                    "external_call": bool(target_config["external_call"]),
                    "elapsed_ms": elapsed_ms,
                },
            }
        )

