"""Thin checkpoint reader abstraction around workflow graph state/history."""

from typing import Any, Callable, Dict, Optional


class CheckpointReader:
    """Fetch final state and checkpoint history by thread id."""

    def __init__(
        self,
        *,
        history_fetcher: Optional[Callable[[str], list[Dict[str, Any]]]] = None,
    ) -> None:
        self._history_fetcher = history_fetcher

    def get_final_state(
        self,
        thread_id: str,
        *,
        workflow: Any | None = None,
    ) -> Dict[str, Any]:
        """Read final state from workflow graph first, then fallback to checkpoint history."""
        if workflow is not None:
            config = {"configurable": {"thread_id": thread_id, **getattr(workflow, "config", {})}}
            state = workflow.graph.get_state(config)
            if state is None:
                return {}
            return state.values if hasattr(state, "values") else state

        history = self.get_history(thread_id)
        if not history:
            return {}
        return history[-1].get("channel_values", {})

    def get_history(self, thread_id: str) -> list[Dict[str, Any]]:
        """Read checkpoint history using injected fetcher or default utility."""
        if self._history_fetcher is not None:
            return self._history_fetcher(thread_id)

        from wwai_agent_orchestration.utils.checkpoint.checkpoint_utils import (
            fetch_full_checkpoint_history,
        )
        from wwai_agent_orchestration.core.database import db_manager

        db = db_manager.get_database("checkpointing_db")
        return fetch_full_checkpoint_history(db=db, thread_id=thread_id)

