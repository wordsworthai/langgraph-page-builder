"""High-level entrypoints for building and running eval sets."""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from wwai_agent_orchestration.evals.checkpoints.checkpoint_reader import CheckpointReader
from wwai_agent_orchestration.evals.runners.run_output_writer import EvalRunOutputWriter
from wwai_agent_orchestration.evals.graph_output_extractors.landing_page_builder import (
    LandingPageExtractor,
    PresetSectionsExtractor,
    TemplateSelectionExtractor,
)
from wwai_agent_orchestration.evals.graph_output_extractors.output_extractor_base import (
    ExtractorRegistry,
)
from wwai_agent_orchestration.evals.judges.integration import make_template_judge_evaluator
from wwai_agent_orchestration.evals.judges.runner import JudgeRunner
from wwai_agent_orchestration.evals.runners.batch_runner import run_eval_set
from wwai_agent_orchestration.evals.runners.workflow_runner import (
    RunnerDependencies,
    default_workflow_executor,
    run_case,
)
from wwai_agent_orchestration.evals.stores.interfaces import EvalStore
from wwai_agent_orchestration.evals.types.eval_case import EvalCase
from wwai_agent_orchestration.evals.types.eval_set import EvalSet


def build_default_extractor_registry() -> ExtractorRegistry:
    registry = ExtractorRegistry()
    registry.register("landing_page", LandingPageExtractor())
    registry.register("template_selection", TemplateSelectionExtractor())
    registry.register("preset_sections", PresetSectionsExtractor())
    return registry


def _status_persistor(store: Optional[EvalStore]):
    def _persist(run_record):
        if store is not None:
            store.save_run_record(run_record)

    return _persist


def _output_persistor(store: Optional[EvalStore]):
    """Return callback that persists output as each case completes (incremental save)."""

    def _persist(result):
        if store is None or result.output is None:
            return
        output_payload = (
            result.output.model_dump()
            if hasattr(result.output, "model_dump")
            else dict(result.output)
        )
        store.save_output(
            eval_set_id=result.run_record.eval_set_id,
            case_id=result.run_record.case_id,
            run_id=result.run_record.run_id,
            workflow_mode=result.output.workflow_mode,
            output=output_payload,
        )

    return _persist


async def run_eval_set_entrypoint(
    *,
    eval_set: EvalSet,
    store: Optional[EvalStore] = None,
    max_concurrency: int = 4,
    max_attempts: int = 1,
    enable_judge: bool = False,
    judge_runner: Optional[JudgeRunner] = None,
    workflow_executor=None,
    dry_run: bool = False,
    dump_output_dir: Optional[str] = None,
    persist_eval_set: bool = True,
) -> dict[str, Any]:
    """Run an eval set and optionally persist artifacts."""
    if store is not None and persist_eval_set:
        store.save_eval_set(eval_set)
    if dry_run:
        return {
            "eval_set_id": eval_set.eval_set_id,
            "total_cases": len(eval_set.cases),
            "completed": 0,
            "failed": 0,
            "judge_completed": 0,
            "judge_failed": 0,
            "results": [],
            "dry_run": True,
        }

    output_dir = dump_output_dir
    run_output_writer = EvalRunOutputWriter(output_dir) if output_dir else None

    deps = RunnerDependencies(
        checkpoint_reader=CheckpointReader(),
        extractor_registry=build_default_extractor_registry(),
        on_status_change=_status_persistor(store),
        on_output_ready=_output_persistor(store),
        workflow_executor=workflow_executor or default_workflow_executor,
        run_output_writer=run_output_writer,
    )
    if enable_judge:
        deps.judge_evaluator = make_template_judge_evaluator(
            judge_runner=judge_runner or JudgeRunner(),
            store=store,
        )

    summary = await run_eval_set(
        eval_set,
        deps,
        max_concurrency=max_concurrency,
        max_attempts=max_attempts,
    )
    if store is not None:
        for result in summary["results"]:
            if result.output is not None:
                output_payload = (
                    result.output.model_dump()
                    if hasattr(result.output, "model_dump")
                    else dict(result.output)
                )
                store.save_output(
                    eval_set_id=eval_set.eval_set_id,
                    case_id=result.run_record.case_id,
                    run_id=result.run_record.run_id,
                    workflow_mode=result.output.workflow_mode,
                    output=output_payload,
                )
    return summary


async def run_single_case_entrypoint(
    *,
    eval_case: EvalCase,
    store: Optional[EvalStore] = None,
    enable_judge: bool = False,
    judge_runner: Optional[JudgeRunner] = None,
    workflow_executor=None,
    dump_output_dir: Optional[str] = None,
) -> dict[str, Any]:
    """Run a single case using standard dependencies."""
    output_dir = dump_output_dir
    run_output_writer = EvalRunOutputWriter(output_dir) if output_dir else None

    deps = RunnerDependencies(
        checkpoint_reader=CheckpointReader(),
        extractor_registry=build_default_extractor_registry(),
        on_status_change=_status_persistor(store),
        workflow_executor=workflow_executor or default_workflow_executor,
        run_output_writer=run_output_writer,
    )
    if enable_judge:
        deps.judge_evaluator = make_template_judge_evaluator(
            judge_runner=judge_runner or JudgeRunner(),
            store=store,
        )
    result = await run_case(eval_case, deps)
    output_payload = (
        (result.output.model_dump() if hasattr(result.output, "model_dump") else dict(result.output))
        if result.output is not None
        else None
    )
    if store is not None and result.output is not None:
        store.save_output(
            eval_set_id=eval_case.eval_set_id,
            case_id=result.run_record.case_id,
            run_id=result.run_record.run_id,
            workflow_mode=result.output.workflow_mode,
            output=output_payload,
        )
    return {
        "status": result.run_record.status,
        "run_record": result.run_record.model_dump(),
        "output": output_payload,
        "judge_result": result.judge_result,
    }


async def resume_eval_set_entrypoint(
    *,
    eval_set_id: str,
    store: EvalStore,
    max_concurrency: int = 4,
    max_attempts: int = 1,
    enable_judge: bool = False,
    judge_runner: Optional[JudgeRunner] = None,
    workflow_executor=None,
    dump_output_dir: Optional[str] = None,
) -> dict[str, Any]:
    """Resume failed/running runs for a stored eval set."""
    eval_set_doc = store.get_eval_set(eval_set_id)
    if not eval_set_doc:
        raise ValueError(f"No eval set found for eval_set_id={eval_set_id}")

    eval_set = EvalSet.model_validate(eval_set_doc)
    # Use latest run per case: resume (a) failed/running, (b) never started (no run record)
    latest_by_case = store.get_latest_run_per_case(eval_set_id)
    case_ids = {
        cid
        for cid, run in latest_by_case.items()
        if run.get("status") in ("failed", "running")
    }
    # Add cases never run (in eval set, not in latest_by_case)
    all_case_ids = {c.case_id for c in eval_set.cases}
    never_started = all_case_ids - set(latest_by_case.keys())
    case_ids = case_ids | never_started
    if not case_ids:
        return {
            "eval_set_id": eval_set_id,
            "total_cases": 0,
            "completed": 0,
            "failed": 0,
            "judge_completed": 0,
            "judge_failed": 0,
            "results": [],
            "resumed": True,
        }
    resumed_cases = [case for case in eval_set.cases if case.case_id in case_ids]
    resumed_eval_set = EvalSet(
        eval_set_id=eval_set.eval_set_id,
        eval_type=eval_set.eval_type,
        version=eval_set.version,
        seed=eval_set.seed,
        description=f"{eval_set.description or ''} (resume)".strip(),
        cases=resumed_cases,
    )
    summary = await run_eval_set_entrypoint(
        eval_set=resumed_eval_set,
        store=store,
        max_concurrency=max_concurrency,
        max_attempts=max_attempts,
        enable_judge=enable_judge,
        judge_runner=judge_runner,
        workflow_executor=workflow_executor,
        dry_run=False,
        dump_output_dir=dump_output_dir,
        persist_eval_set=False,  # Do not overwrite original eval set with resumed subset
    )
    summary["resumed"] = True
    return summary


def run_async(coro):
    """Run async entrypoint in sync contexts."""
    return asyncio.run(coro)

