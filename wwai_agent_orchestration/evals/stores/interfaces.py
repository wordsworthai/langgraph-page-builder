"""Persistence interfaces for eval framework stores."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from wwai_agent_orchestration.evals.types.eval_set import EvalSet
from wwai_agent_orchestration.evals.types.run_record import RunRecord


@runtime_checkable
class EvalStore(Protocol):
    """Store protocol for eval sets, run records, outputs, and judge results."""

    def save_eval_set(self, eval_set: EvalSet) -> bool:
        ...

    def get_eval_set(self, eval_set_id: str) -> Optional[Dict[str, Any]]:
        ...

    def save_run_record(self, run_record: RunRecord) -> bool:
        ...

    def get_run_records(
        self, eval_set_id: str, *, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        ...

    def get_latest_run_per_case(
        self, eval_set_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """Return latest run per case_id. Used for case-centric summary and resume."""
        ...

    def save_output(
        self,
        *,
        eval_set_id: str,
        case_id: str,
        run_id: str,
        workflow_mode: str,
        output: Dict[str, Any],
    ) -> bool:
        ...

    def get_outputs(self, eval_set_id: str) -> List[Dict[str, Any]]:
        ...

    def save_judge_result(
        self,
        *,
        eval_set_id: str,
        run_id: str,
        task_name: str,
        result: Dict[str, Any],
    ) -> bool:
        ...

    def get_eval_set_summary(self, eval_set_id: str) -> Dict[str, Any]:
        ...

