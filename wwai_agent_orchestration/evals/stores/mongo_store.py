"""MongoDB-backed EvalStore implementation."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo import MongoClient

from wwai_agent_orchestration.evals.stores.interfaces import EvalStore
from wwai_agent_orchestration.evals.stores.key_conventions import (
    CanonicalKeys,
    build_eval_set_doc_id,
    build_judge_doc_id,
    build_output_doc_id,
    build_run_doc_id,
    normalize_task_type,
    validate_canonical_keys,
)
from wwai_agent_orchestration.evals.types.eval_set import EvalSet
from wwai_agent_orchestration.evals.types.run_record import RunRecord


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MongoEvalStore(EvalStore):
    """Mongo-backed persistence implementation for eval artifacts."""

    def __init__(
        self,
        *,
        mongo_uri: Optional[str] = None,
        db_name: str = "eval",
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

        self._eval_sets = self._db["eval_sets"]
        self._runs = self._db["eval_runs"]
        self._outputs = self._db["eval_outputs"]
        self._judge_results = self._db["eval_judge_results"]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        try:
            self._eval_sets.create_index([("eval_set_id", 1)], unique=True)
            self._runs.create_index([("eval_set_id", 1), ("run_id", 1)], unique=True)
            self._runs.create_index([("eval_set_id", 1), ("status", 1)])
            self._runs.create_index([("case_id", 1), ("attempt", -1)])
            self._outputs.create_index([("eval_set_id", 1), ("run_id", 1)], unique=True)
            self._judge_results.create_index(
                [("eval_set_id", 1), ("run_id", 1), ("task_name", 1)], unique=True
            )
        except Exception:
            pass

    def save_eval_set(self, eval_set: EvalSet) -> bool:
        payload = eval_set.model_dump()
        payload.pop("created_at", None)
        payload["_id"] = build_eval_set_doc_id(eval_set.eval_set_id)
        payload["updated_at"] = _utcnow()
        self._eval_sets.update_one(
            {"_id": payload["_id"]},
            {"$set": payload, "$setOnInsert": {"created_at": _utcnow()}},
            upsert=True,
        )
        return True

    def get_eval_set(self, eval_set_id: str) -> Optional[Dict[str, Any]]:
        return self._eval_sets.find_one({"eval_set_id": eval_set_id})

    def save_run_record(self, run_record: RunRecord) -> bool:
        task_type = normalize_task_type(run_record.task_type)
        validate_canonical_keys(
            CanonicalKeys(
                eval_set_id=run_record.eval_set_id,
                case_id=run_record.case_id,
                run_id=run_record.run_id,
                thread_id=run_record.thread_id,
                task_type=task_type,
            )
        )
        payload = run_record.model_dump()
        payload.pop("created_at", None)
        payload["task_type"] = task_type
        payload["_id"] = build_run_doc_id(run_record.eval_set_id, run_record.run_id)
        payload["updated_at"] = _utcnow()
        self._runs.update_one(
            {"_id": payload["_id"]},
            {"$set": payload, "$setOnInsert": {"created_at": _utcnow()}},
            upsert=True,
        )
        return True

    def get_run_records(
        self, eval_set_id: str, *, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"eval_set_id": eval_set_id}
        if status is not None:
            query["status"] = status
        return list(self._runs.find(query))

    def save_output(
        self,
        *,
        eval_set_id: str,
        case_id: str,
        run_id: str,
        workflow_mode: str,
        output: Dict[str, Any],
    ) -> bool:
        doc_id = build_output_doc_id(eval_set_id, run_id, case_id)
        now = _utcnow()
        payload = {
            "_id": doc_id,
            "eval_set_id": eval_set_id,
            "case_id": case_id,
            "run_id": run_id,
            "workflow_mode": workflow_mode,
            "output": output,
            "updated_at": now,
        }
        self._outputs.update_one(
            {"_id": doc_id},
            {"$set": payload, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        return True

    def get_outputs(self, eval_set_id: str) -> List[Dict[str, Any]]:
        return list(self._outputs.find({"eval_set_id": eval_set_id}))

    def save_judge_result(
        self,
        *,
        eval_set_id: str,
        run_id: str,
        task_name: str,
        result: Dict[str, Any],
    ) -> bool:
        now = _utcnow()
        doc_id = build_judge_doc_id(eval_set_id, run_id, task_name)
        payload = {
            "_id": doc_id,
            "eval_set_id": eval_set_id,
            "run_id": run_id,
            "task_name": task_name,
            "result": result,
            "updated_at": now,
        }
        self._judge_results.update_one(
            {"_id": doc_id},
            {"$set": payload, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        return True

    def get_latest_run_per_case(
        self, eval_set_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """Return latest run per case_id (by updated_at). Case-centric view."""
        all_runs = list(
            self._runs.find({"eval_set_id": eval_set_id}).sort("updated_at", -1)
        )
        latest: Dict[str, Dict[str, Any]] = {}
        for run in all_runs:
            cid = run.get("case_id")
            if cid and cid not in latest:
                latest[cid] = run
        return latest

    def get_eval_set_summary(self, eval_set_id: str) -> Dict[str, Any]:
        """Case-centric summary: total from eval set, counts by latest run status per case."""
        latest_by_case = self.get_latest_run_per_case(eval_set_id)
        eval_set_doc = self.get_eval_set(eval_set_id)
        if eval_set_doc and "cases" in eval_set_doc:
            total = len(eval_set_doc["cases"])
        else:
            total = len(latest_by_case)
        completed = sum(
            1 for r in latest_by_case.values() if r.get("status") == "completed"
        )
        failed = sum(1 for r in latest_by_case.values() if r.get("status") == "failed")
        running = sum(
            1 for r in latest_by_case.values() if r.get("status") == "running"
        )
        return {
            "eval_set_id": eval_set_id,
            "total": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "progress_pct": (completed / total * 100) if total else 0.0,
        }

