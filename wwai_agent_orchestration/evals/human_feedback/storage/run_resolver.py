"""Run resolver: resolve (eval_set_id, case_id) to run metadata from eval store."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from pymongo import MongoClient


@dataclass(frozen=True)
class ResolvedRun:
    """Run metadata resolved from eval_outputs + eval_runs."""

    run_id: str
    thread_id: str
    task_type: str
    task_details: Dict[str, Any]
    workflow_mode: str


@runtime_checkable
class RunResolver(Protocol):
    """Protocol for resolving (eval_set_id, case_id) to run metadata."""

    def resolve(self, eval_set_id: str, case_id: str) -> Optional[ResolvedRun]:
        ...

    def list_cases_with_outputs(
        self,
        eval_set_id: str,
        *,
        case_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[tuple[str, str]]:
        """Return list of (eval_set_id, case_id) pairs that have outputs."""
        ...


OUTPUTS_COLLECTION = "eval_outputs"
RUNS_COLLECTION = "eval_runs"


class MongoRunResolver(RunResolver):
    """Mongo-backed run resolver using eval_outputs and eval_runs."""

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
        self._outputs = self._db[OUTPUTS_COLLECTION]
        self._runs = self._db[RUNS_COLLECTION]

    def resolve(self, eval_set_id: str, case_id: str) -> Optional[ResolvedRun]:
        output_docs = list(
            self._outputs.find(
                {"eval_set_id": eval_set_id, "case_id": case_id}
            ).sort("updated_at", -1)
        )
        if not output_docs:
            return None
        output = output_docs[0]
        run_id = output.get("run_id")
        workflow_mode = output.get("workflow_mode", "unknown")
        if not run_id:
            return None

        run_doc = self._runs.find_one(
            {"eval_set_id": eval_set_id, "run_id": run_id}
        )
        if not run_doc:
            return None

        thread_id = run_doc.get("thread_id", "")
        task_type = run_doc.get("task_type", "landing_page")
        task_details = run_doc.get("task_details") or {}

        return ResolvedRun(
            run_id=run_id,
            thread_id=thread_id,
            task_type=task_type,
            task_details=task_details,
            workflow_mode=workflow_mode,
        )

    def list_cases_with_outputs(
        self,
        eval_set_id: str,
        *,
        case_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[tuple[str, str]]:
        query: Dict[str, Any] = {"eval_set_id": eval_set_id}
        if case_id is not None:
            query["case_id"] = case_id
        cursor = self._outputs.find(query).sort("updated_at", -1)
        if limit is not None:
            cursor = cursor.limit(limit)
        pairs: List[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for doc in cursor:
            cid = doc.get("case_id")
            if cid and (eval_set_id, cid) not in seen:
                seen.add((eval_set_id, cid))
                pairs.append((eval_set_id, cid))
        return pairs
