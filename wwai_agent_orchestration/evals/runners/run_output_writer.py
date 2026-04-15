"""Service for writing eval run output (final state, history, extractor output) to disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol


def _state_to_jsonable(obj: Any) -> Any:
    """Recursively convert state (may contain Pydantic models) to JSON-serializable dict."""
    if hasattr(obj, "model_dump"):
        return _state_to_jsonable(obj.model_dump())
    if isinstance(obj, dict):
        return {k: _state_to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_state_to_jsonable(v) for v in obj]
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    return str(obj)


class EvalRunOutputWriterProtocol(Protocol):
    """Protocol for writing eval run output to disk."""

    def write_run_output(
        self,
        run_id: str,
        thread_id: str,
        case_id: str,
        workflow_mode: str,
        final_state: dict[str, Any],
        extractor_output: dict[str, Any],
    ) -> None: ...


class EvalRunOutputWriter:
    """Writes final graph state, history, and extractor output to a folder for debugging."""

    def __init__(self, output_dir: str | Path) -> None:
        self._output_dir = Path(output_dir)

    def write_run_output(
        self,
        run_id: str,
        thread_id: str,
        case_id: str,
        workflow_mode: str,
        final_state: dict[str, Any],
        extractor_output: dict[str, Any],
    ) -> None:
        """Serialize and write run output to JSON. Creates output dir if needed."""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        fname = f"final_state_{run_id}_{case_id}.json"
        out_path = self._output_dir / fname
        payload = {
            "run_id": run_id,
            "thread_id": thread_id,
            "case_id": case_id,
            "workflow_mode": workflow_mode,
            "final_state": _state_to_jsonable(final_state),
            "extractor_output": extractor_output,
        }
        out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
