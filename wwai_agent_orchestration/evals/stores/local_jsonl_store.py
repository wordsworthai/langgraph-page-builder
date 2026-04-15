"""Local JSONL-backed EvalStore implementation for development/testing."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from wwai_agent_orchestration.evals.stores.interfaces import EvalStore
from wwai_agent_orchestration.evals.stores.key_conventions import (
    CanonicalKeys,
    normalize_task_type,
    validate_canonical_keys,
)
from wwai_agent_orchestration.evals.types.eval_set import EvalSet
from wwai_agent_orchestration.evals.types.run_record import RunRecord


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


class LocalJsonlEvalStore(EvalStore):
    """JSONL file-backed store for local iteration and tests."""

    def __init__(self, *, root_dir: str | Path) -> None:
        self._root = Path(root_dir)
        self._root.mkdir(parents=True, exist_ok=True)
        self._eval_sets_file = self._root / "eval_sets.jsonl"
        self._runs_file = self._root / "runs.jsonl"
        self._outputs_file = self._root / "outputs.jsonl"
        self._judge_results_file = self._root / "judge_results.jsonl"

    def _append(self, file_path: Path, payload: Dict[str, Any]) -> None:
        with file_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, default=_json_default) + "\n")

    def _read_all(self, file_path: Path) -> List[Dict[str, Any]]:
        if not file_path.exists():
            return []
        records = []
        with file_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def save_eval_set(self, eval_set: EvalSet) -> bool:
        payload = eval_set.model_dump()
        payload["saved_at"] = _now_iso()
        self._append(self._eval_sets_file, payload)
        return True

    def get_eval_set(self, eval_set_id: str) -> Optional[Dict[str, Any]]:
        matches = [
            record
            for record in self._read_all(self._eval_sets_file)
            if record.get("eval_set_id") == eval_set_id
        ]
        return matches[-1] if matches else None

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
        payload["task_type"] = task_type
        payload["saved_at"] = _now_iso()
        self._append(self._runs_file, payload)
        return True

    def get_run_records(
        self, eval_set_id: str, *, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        runs = [
            record
            for record in self._read_all(self._runs_file)
            if record.get("eval_set_id") == eval_set_id
        ]
        if status is not None:
            runs = [record for record in runs if record.get("status") == status]
        return runs

    def get_latest_run_per_case(
        self, eval_set_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """Return latest run per case_id (by saved_at). Case-centric view."""
        runs = [
            record
            for record in self._read_all(self._runs_file)
            if record.get("eval_set_id") == eval_set_id
        ]
        # Sort by saved_at desc (most recent first); fallback to updated_at
        runs.sort(
            key=lambda r: r.get("saved_at") or r.get("updated_at") or "",
            reverse=True,
        )
        latest: Dict[str, Dict[str, Any]] = {}
        for run in runs:
            cid = run.get("case_id")
            if cid and cid not in latest:
                latest[cid] = run
        return latest

    def save_output(
        self,
        *,
        eval_set_id: str,
        case_id: str,
        run_id: str,
        workflow_mode: str,
        output: Dict[str, Any],
    ) -> bool:
        payload = {
            "eval_set_id": eval_set_id,
            "case_id": case_id,
            "run_id": run_id,
            "workflow_mode": workflow_mode,
            "output": output,
            "saved_at": _now_iso(),
        }
        self._append(self._outputs_file, payload)
        return True

    def get_outputs(self, eval_set_id: str) -> List[Dict[str, Any]]:
        return [
            record
            for record in self._read_all(self._outputs_file)
            if record.get("eval_set_id") == eval_set_id
        ]

    def save_judge_result(
        self,
        *,
        eval_set_id: str,
        run_id: str,
        task_name: str,
        result: Dict[str, Any],
    ) -> bool:
        payload = {
            "eval_set_id": eval_set_id,
            "run_id": run_id,
            "task_name": task_name,
            "result": result,
            "saved_at": _now_iso(),
        }
        self._append(self._judge_results_file, payload)
        return True

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

