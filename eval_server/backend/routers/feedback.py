"""Human feedback endpoints."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from eval_metrics_adapter import (
    resolve_case_id_from_run,
    resolve_run_id_from_thread,
)
from wwai_agent_orchestration.evals.human_feedback import (
    FeedbackService,
    MongoFeedbackStore,
    MongoRunResolver,
    get_taxonomy,
)

from .common import (
    DEFAULT_MONGO_URI,
    DEFAULT_DB_NAME,
    make_json_serializable,
)

router = APIRouter()

HUMAN_FEEDBACK_DB = "eval"


class FeedbackRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    db_name: Optional[str] = DEFAULT_DB_NAME
    thread_id: str


class FeedbackSaveRequest(BaseModel):
    mongo_uri: Optional[str] = DEFAULT_MONGO_URI
    db_name: Optional[str] = DEFAULT_DB_NAME
    thread_id: str
    eval_set_id: Optional[str] = None
    run_id: Optional[str] = None
    business_id: Optional[str] = None
    feedback: dict


@router.get("/api/feedback/taxonomy")
async def get_feedback_taxonomy(task_type: str = Query(..., alias="task_type")):
    """Get taxonomy for a task type (raw taxonomy passed to frontend)."""
    try:
        taxonomy = get_taxonomy(task_type=task_type, version="v1")
        return make_json_serializable(taxonomy.model_dump(mode="json"))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/feedback")
async def get_feedback(request: FeedbackRequest):
    """Get human feedback for a specific thread."""
    try:
        db_name = request.db_name or HUMAN_FEEDBACK_DB
        run_id = resolve_run_id_from_thread(
            thread_id=request.thread_id,
            mongo_uri=request.mongo_uri,
            db_name=db_name,
        )
        if not run_id:
            return {"feedback": None}

        store = MongoFeedbackStore(
            mongo_uri=request.mongo_uri,
            db_name=db_name,
        )
        doc = store.get_feedback_by_run(run_id)
        if not doc:
            return {"feedback": None}

        # Shape expected by EvalView: {feedback: {key: value}, ...}
        return {"feedback": make_json_serializable(doc)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/feedback/save")
async def save_feedback(request: FeedbackSaveRequest):
    """Save human feedback for a specific thread/eval example."""
    try:
        db_name = request.db_name or HUMAN_FEEDBACK_DB
        eval_set_id = request.eval_set_id
        run_id = request.run_id

        if not eval_set_id or not run_id:
            raise HTTPException(
                status_code=400,
                detail="eval_set_id and run_id are required for taxonomy-based feedback",
            )

        case_id = resolve_case_id_from_run(
            eval_set_id=eval_set_id,
            run_id=run_id,
            mongo_uri=request.mongo_uri,
            db_name=db_name,
        )
        if not case_id:
            raise HTTPException(
                status_code=404,
                detail=f"No case found for eval_set_id={eval_set_id!r}, run_id={run_id!r}",
            )

        store = MongoFeedbackStore(
            mongo_uri=request.mongo_uri,
            db_name=db_name,
        )
        run_resolver = MongoRunResolver(
            mongo_uri=request.mongo_uri,
            db_name=db_name,
        )
        service = FeedbackService(store=store, run_resolver=run_resolver)

        service.save_feedback_by_case(
            eval_set_id=eval_set_id,
            case_id=case_id,
            feedback=request.feedback,
        )
        return {"success": True}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
