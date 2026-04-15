"""MongoDB store for feedback snapshots."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo import MongoClient

from wwai_agent_orchestration.evals.human_feedback.storage.interfaces import FeedbackStore
from wwai_agent_orchestration.evals.human_feedback.storage.key_utils import (
    build_feedback_doc_id,
)
from wwai_agent_orchestration.evals.human_feedback.types import HumanFeedbackSnapshot


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MongoFeedbackStore(FeedbackStore):
    """Mongo-backed latest snapshot store for human feedback."""

    def __init__(
        self,
        *,
        mongo_uri: Optional[str] = None,
        db_name: str = "eval",
        collection_name: str = "human_feedback",
        db: Any | None = None,
    ) -> None:
        if db is not None:
            self._db = db
        else:
            uri = mongo_uri or os.getenv(
                "MONGO_CONNECTION_URI",
                "mongodb://localhost:27017/",
            )
            self._db = MongoClient(uri)[db_name]
        self._feedback = self._db[collection_name]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        try:
            self._feedback.create_index([("eval_set_id", 1), ("run_id", 1)], unique=True)
            self._feedback.create_index([("run_id", 1)], unique=True)
            self._feedback.create_index([("eval_set_id", 1), ("task_type", 1)])
            self._feedback.create_index([("updated_at", -1)])
        except Exception:
            pass

    def save_feedback(self, snapshot: HumanFeedbackSnapshot) -> bool:
        payload = snapshot.model_dump()
        payload.pop("created_at", None)
        payload["_id"] = build_feedback_doc_id(snapshot.eval_set_id, snapshot.run_id)
        payload["updated_at"] = _utcnow()
        self._feedback.update_one(
            {"_id": payload["_id"]},
            {"$set": payload, "$setOnInsert": {"created_at": _utcnow()}},
            upsert=True,
        )
        return True

    def get_feedback_by_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        return self._feedback.find_one({"run_id": run_id})

    def get_feedback_for_eval_set(self, eval_set_id: str) -> List[Dict[str, Any]]:
        return list(self._feedback.find({"eval_set_id": eval_set_id}))

    def get_feedback_for_task(
        self,
        *,
        task_type: str,
        eval_set_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"task_type": task_type}
        if eval_set_id:
            query["eval_set_id"] = eval_set_id
        return list(self._feedback.find(query))
