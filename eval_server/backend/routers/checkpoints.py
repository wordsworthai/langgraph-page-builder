"""Checkpoint and thread endpoints."""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from wwai_agent_orchestration.utils.checkpoint.checkpoint_utils import (
    fetch_full_checkpoint_history,
    get_all_thread_ids,
)

from .common import (
    DEFAULT_MONGO_URI,
    DEFAULT_DB_NAME,
    _get_checkpoint_db,
    make_json_serializable,
)
from eval_metrics_adapter import get_eval_output

router = APIRouter()


class CheckpointRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    db_name: Optional[str] = DEFAULT_DB_NAME
    thread_id: str


class RunSummaryRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    db_name: Optional[str] = DEFAULT_DB_NAME
    thread_id: str
    eval_set_id: Optional[str] = None
    run_id: Optional[str] = None


class ThreadListRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    db_name: Optional[str] = DEFAULT_DB_NAME
    limit: Optional[int] = 50


@router.post("/api/threads")
async def list_threads(request: ThreadListRequest):
    """Get list of all thread_ids."""
    try:
        threads = get_all_thread_ids(
            db=_get_checkpoint_db(),
            limit=request.limit,
        )
        return {"threads": threads}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/checkpoints")
async def get_checkpoints(request: CheckpointRequest):
    """Get all checkpoints for a thread."""
    try:
        history = fetch_full_checkpoint_history(
            db=_get_checkpoint_db(),
            thread_id=request.thread_id,
        )

        serializable_history = make_json_serializable(history)

        nodes = []
        edges = []

        for ckpt in serializable_history:
            node_id = ckpt["checkpoint_id"]
            step = ckpt["step"]
            node_name = ckpt["node_name"]

            nodes.append({
                "id": node_id,
                "label": f"[{step}] {node_name}",
                "step": step,
                "node_name": node_name,
                "data": ckpt,
            })

            parent_id = ckpt.get("parent_checkpoint_id")
            if parent_id:
                edges.append({
                    "from": parent_id,
                    "to": node_id,
                })

        return {
            "thread_id": request.thread_id,
            "checkpoint_count": len(history),
            "nodes": nodes,
            "edges": edges,
            "history": serializable_history,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/run-summary")
async def get_run_summary(request: RunSummaryRequest):
    """
    Return raw checkpoint data. All extraction and display conversion happens in the frontend.
    - first_checkpoint: Full first checkpoint (channel_values, writes, etc.)
    - last_checkpoint: Full last checkpoint
    - history: Full checkpoint list
    - eval_output: Raw eval_output from eval_outputs collection (when eval_set_id/run_id provided)
    """
    try:
        history = fetch_full_checkpoint_history(
            db=_get_checkpoint_db(),
            thread_id=request.thread_id,
        )

        if not history:
            raise HTTPException(status_code=404, detail="No checkpoints found for this thread")

        first_checkpoint = make_json_serializable(history[0])
        last_checkpoint = make_json_serializable(history[-1])
        serializable_history = make_json_serializable(history)

        eval_output = None
        if request.eval_set_id and request.run_id:
            eval_output = get_eval_output(
                eval_set_id=request.eval_set_id,
                run_id=request.run_id,
                mongo_uri=request.mongo_uri,
                db_name=request.db_name or DEFAULT_DB_NAME,
            )
            if eval_output is not None:
                eval_output = make_json_serializable(eval_output)

        return {
            "thread_id": request.thread_id,
            "checkpoint_count": len(history),
            "first_checkpoint": first_checkpoint,
            "last_checkpoint": last_checkpoint,
            "history": serializable_history,
            "eval_output": eval_output,
            "steps": [
                {"step": ckpt["step"], "node_name": ckpt["node_name"], "source": ckpt["source"]}
                for ckpt in history
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
