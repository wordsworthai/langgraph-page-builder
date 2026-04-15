"""Helpers to integrate judge execution into eval runners."""

from __future__ import annotations

from typing import Any, Optional

from wwai_agent_orchestration.evals.judges.runner import JudgeRunner
from wwai_agent_orchestration.evals.judges.tasks.landing_page_builder.template_eval.task import (
    TemplateEvalJudgeTask,
    TemplateEvalJudgeTaskInstance,
)
from wwai_agent_orchestration.evals.runners.base_runner import RunCaseResult
from wwai_agent_orchestration.evals.types.eval_case import EvalCase


def make_template_judge_evaluator(
    *,
    judge_runner: JudgeRunner,
    store: Optional[Any] = None,
) -> Any:
    """Create async judge evaluator callable compatible with RunnerDependencies."""

    async def _evaluate(eval_case: EvalCase, result: RunCaseResult) -> dict | None:
        if result.run_record.status != "completed":
            return None
        if result.final_state is None or result.output is None:
            return None
        task = TemplateEvalJudgeTask()
        try:
            judge_result = await judge_runner.run(
                task=task,
                task_instance_cls=TemplateEvalJudgeTaskInstance,
                run=result.run_record.model_dump(),
                state=result.final_state,
                output=result.output.model_dump()
                if hasattr(result.output, "model_dump")
                else dict(result.output),
            )
        except Exception as exc:
            judge_result = {
                "parse_error": True,
                "parse_error_reason": str(exc),
                "model_name": judge_runner.model_name,
                "prompt_version": task.prompt_version,
            }
        if store is not None:
            store.save_judge_result(
                eval_set_id=result.run_record.eval_set_id,
                run_id=result.run_record.run_id,
                task_name=task.TASK_NAME,
                result=judge_result,
            )
        return judge_result

    return _evaluate

