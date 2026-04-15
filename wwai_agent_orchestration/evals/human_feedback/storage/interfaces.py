"""Feedback persistence protocol."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from wwai_agent_orchestration.evals.human_feedback.types import HumanFeedbackSnapshot


@runtime_checkable
class FeedbackStore(Protocol):
    """Store protocol for human feedback snapshots."""

    def save_feedback(self, snapshot: HumanFeedbackSnapshot) -> bool:
        ...

    def get_feedback_by_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        ...

    def get_feedback_for_eval_set(self, eval_set_id: str) -> List[Dict[str, Any]]:
        ...

    def get_feedback_for_task(
        self,
        *,
        task_type: str,
        eval_set_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        ...
