"""Single-case workflow runner."""

import inspect
import sys
import time
import traceback
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

from wwai_agent_orchestration.evals.checkpoints.checkpoint_reader import CheckpointReader

from wwai_agent_orchestration.evals.runners.run_output_writer import EvalRunOutputWriter
from wwai_agent_orchestration.evals.graph_output_extractors.output_extractor_base import ExtractorRegistry
from wwai_agent_orchestration.evals.runners.base_runner import RunCaseResult
from wwai_agent_orchestration.evals.types.eval_case import EvalCase
from wwai_agent_orchestration.evals.types.run_record import RunRecord
from wwai_agent_orchestration.evals.utils.hashing import build_run_id, build_thread_id


WorkflowExecutor = Callable[[EvalCase, str, dict[str, Any]], Awaitable[Any]]
StatusCallback = Callable[[RunRecord], None]
OutputReadyCallback = Callable[[RunCaseResult], None]
JudgeResultCallback = Callable[[RunCaseResult], None]
JudgeEvaluator = Callable[[EvalCase, RunCaseResult], Awaitable[dict[str, Any] | None] | dict[str, Any] | None]

def _eval_log(msg: str) -> None:
    """Print eval progress to stderr (always visible, bypasses log config)."""
    print(f"[Eval] {msg}", file=sys.stderr, flush=True)


async def default_workflow_executor(
    eval_case: EvalCase,
    thread_id: str,
    workflow_config: dict[str, Any],
) -> Any:
    """Execute workflow by dispatching to the appropriate executor based on workflow_mode."""
    if eval_case.workflow_mode in ("preset_sections", "landing_page", "template_selection"):
        from wwai_agent_orchestration.evals.runners.landing_page_builder import (
            execute_landing_page_workflow,
        )
        return await execute_landing_page_workflow(eval_case, thread_id, workflow_config)
    raise ValueError(f"Unsupported workflow_mode: {eval_case.workflow_mode}")


@dataclass
class RunnerDependencies:
    """Dependency bundle for running eval cases. Each field plugs into the run_case workflow."""

    # Reads final graph state and checkpoint history by thread_id after workflow execution.
    # Used to extract output and pass state to the judge.
    checkpoint_reader: CheckpointReader

    # Maps workflow_mode (e.g. preset_sections, landing_page) to an output extractor.
    # Used to extract typed output from raw final_state and history.
    extractor_registry: ExtractorRegistry

    # Executes the workflow (e.g. landing page graph) for the given eval_case and thread_id.
    # Returns the workflow instance so we can read its final state.
    workflow_executor: WorkflowExecutor = default_workflow_executor

    # Optional config passed to workflow_executor (e.g. model overrides, timeout).
    workflow_config: dict[str, Any] | None = None

    # Called when run status changes (running -> completed/failed). Used by batch runner to persist
    # RunRecord to storage.
    on_status_change: Optional[StatusCallback] = None

    # Called when a case completes with output. Used to persist output incrementally (per-case)
    # so outputs are not lost if the batch is interrupted before completion.
    on_output_ready: Optional[OutputReadyCallback] = None

    # Optional LLM-as-judge evaluator. Runs after successful completion to score output quality.
    judge_evaluator: Optional[JudgeEvaluator] = None

    # Called when judge returns a result. Used to persist judge results to storage.
    on_judge_result: Optional[JudgeResultCallback] = None

    # When set, writes final state, history, and extractor output to a folder for debugging.
    run_output_writer: Optional[EvalRunOutputWriter] = None


def _to_task_type(eval_case: EvalCase) -> str:
    task_type = eval_case.eval_type
    if not task_type or not str(task_type).strip():
        raise ValueError("eval_case.eval_type must be defined and non-empty")
    return task_type


async def run_case(
    eval_case: EvalCase,
    deps: RunnerDependencies,
    *,
    run_id: str | None = None,
    thread_id: str | None = None,
    attempt: int = 1,
) -> RunCaseResult:
    """Run one eval case: execute workflow, extract output, optionally run judge.

    Flow:
    1. Build RunRecord (running) and notify via on_status_change.
    2. Execute workflow via workflow_executor.
    3. Read final state and history from checkpoint_reader.
    4. Run output extractor (from extractor_registry) to get typed output.
    5. Mark completed, notify status, optionally run judge_evaluator and on_judge_result.
    6. On exception: mark failed, set error_message, notify status.
    """
    run_id = run_id or build_run_id()
    thread_id = thread_id or build_thread_id(run_id)
    # run_record tracks status, timing, and metadata; persisted via on_status_change.
    run_record = RunRecord(
        run_id=run_id,
        thread_id=thread_id,
        case_id=eval_case.case_id,
        eval_set_id=eval_case.eval_set_id,
        task_type=_to_task_type(eval_case),
        task_details=dict(eval_case.set_inputs),
        request_id=thread_id,
        inputs=eval_case.workflow_inputs,
        status="running",
        attempt=attempt,
    )
    if deps.on_status_change:
        deps.on_status_change(run_record)

    start_time = time.time()
    try:
        _eval_log(f"run_case: executing workflow case_id={eval_case.case_id} thread_id={thread_id}")
        # Execute workflow (e.g. landing page graph); stream runs to completion.
        workflow = await deps.workflow_executor(eval_case, thread_id, deps.workflow_config or {})
        _eval_log(f"run_case: workflow done, reading checkpoint case_id={eval_case.case_id}")
        # Read final graph state and checkpoint history for output extraction.
        final_state = deps.checkpoint_reader.get_final_state(thread_id, workflow=workflow)
        history = deps.checkpoint_reader.get_history(thread_id)
        _eval_log(f"run_case: checkpoint read, extracting output case_id={eval_case.case_id}")
        # Extract typed output (e.g. PresetSectionsOutput, TemplateSelectionOutput) from raw state.
        extractor = deps.extractor_registry.resolve(eval_case.workflow_mode)
        output = extractor.extract(final_state, history)
        _eval_log(f"run_case: extraction complete case_id={eval_case.case_id} status=completed")
        output_dump = output.model_dump() if hasattr(output, "model_dump") else dict(output)
        if deps.run_output_writer is not None:
            deps.run_output_writer.write_run_output(
                run_id=run_id,
                thread_id=thread_id,
                case_id=eval_case.case_id,
                workflow_mode=eval_case.workflow_mode,
                final_state=final_state,
                extractor_output=output_dump,
            )
        run_record.status = "completed"
        run_record.duration_ms = (time.time() - start_time) * 1000
        run_record.generation_version_id = (
            getattr(output, "generation_version_id", None)
            or final_state.get("generation_version_id")
        )
        if deps.on_status_change:
            deps.on_status_change(run_record)
        result = RunCaseResult(run_record=run_record, output=output, final_state=final_state)
        if deps.on_output_ready and result.output is not None:
            deps.on_output_ready(result)
        # Run optional LLM-as-judge; persist if on_judge_result is set.
        if deps.judge_evaluator is not None:
            judge_value = deps.judge_evaluator(eval_case, result)
            if inspect.isawaitable(judge_value):
                judge_value = await judge_value
            if judge_value is not None:
                result.judge_result = judge_value
                if deps.on_judge_result is not None:
                    deps.on_judge_result(result)
        return result
    except Exception as exc:
        # On failure: persist error details and notify status.
        _eval_log(f"run_case: failed case_id={eval_case.case_id} error={exc.__class__.__name__}: {exc}")
        run_record.status = "failed"
        error_text = str(exc).strip()
        if not error_text:
            error_text = repr(exc)
        run_record.error_message = (
            f"{exc.__class__.__name__}: {error_text}\n\nTraceback:\n{traceback.format_exc()}"
        )
        run_record.duration_ms = (time.time() - start_time) * 1000
        if deps.on_status_change:
            deps.on_status_change(run_record)
        return RunCaseResult(run_record=run_record, output=None, final_state=None)

