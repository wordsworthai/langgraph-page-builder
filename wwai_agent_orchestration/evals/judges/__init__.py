"""Judge abstractions and task implementations."""

from wwai_agent_orchestration.evals.judges.base import BaseJudgeTask, BaseJudgeTaskInstance
from wwai_agent_orchestration.evals.judges.integration import make_template_judge_evaluator
from wwai_agent_orchestration.evals.judges.runner import JudgeRunner

__all__ = ["BaseJudgeTask", "BaseJudgeTaskInstance", "JudgeRunner", "make_template_judge_evaluator"]

