"""Shared runner primitives."""

from dataclasses import dataclass
from typing import Any

from wwai_agent_orchestration.evals.types.run_record import RunRecord


@dataclass
class RunCaseResult:
    """Result envelope for one case execution."""

    run_record: RunRecord
    output: Any | None
    final_state: dict[str, Any] | None = None
    judge_result: dict[str, Any] | None = None

