"""Batch runner for eval sets with bounded concurrency and retry."""

import asyncio
import sys
from collections import defaultdict

from wwai_agent_orchestration.evals.runners.base_runner import RunCaseResult
from wwai_agent_orchestration.evals.runners.workflow_runner import RunnerDependencies, run_case
from wwai_agent_orchestration.evals.types.eval_set import EvalSet


def _eval_log(msg: str) -> None:
    """Print eval progress to stderr (always visible, bypasses log config)."""
    print(f"[Eval] {msg}", file=sys.stderr, flush=True)


async def run_eval_set(
    eval_set: EvalSet,
    deps: RunnerDependencies,
    *,
    max_concurrency: int = 4,
    max_attempts: int = 1,
) -> dict[str, object]:
    """Run all cases in an eval set and return summary + per-case results."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    semaphore = asyncio.Semaphore(max_concurrency)
    final_results: dict[str, RunCaseResult] = {}
    total = len(eval_set.cases)

    async def _run_with_retry(case, index: int) -> None:
        attempt = 1
        result: RunCaseResult | None = None
        while attempt <= max_attempts:
            async with semaphore:
                _eval_log(
                    f"Starting case {index + 1}/{total} case_id={case.case_id} attempt={attempt}"
                )
                result = await run_case(case, deps, attempt=attempt)
            if result.run_record.status == "completed":
                break
            attempt += 1
        if result is not None:
            final_results[case.case_id] = result

    await asyncio.gather(
        *[_run_with_retry(case, i) for i, case in enumerate(eval_set.cases)]
    )

    status_counts = defaultdict(int)
    judge_counts = defaultdict(int)
    for result in final_results.values():
        status_counts[result.run_record.status] += 1
        if result.judge_result is not None:
            if result.judge_result.get("parse_error"):
                judge_counts["failed"] += 1
            else:
                judge_counts["completed"] += 1

    return {
        "eval_set_id": eval_set.eval_set_id,
        "total_cases": len(eval_set.cases),
        "completed": status_counts.get("completed", 0),
        "failed": status_counts.get("failed", 0),
        "judge_completed": judge_counts.get("completed", 0),
        "judge_failed": judge_counts.get("failed", 0),
        "results": list(final_results.values()),
    }

