"""Canonical eval contracts used across the eval framework."""

from wwai_agent_orchestration.evals.types.eval_case import EvalCase
from wwai_agent_orchestration.evals.types.eval_set import EvalSet
from wwai_agent_orchestration.evals.types.run_record import RunRecord
from wwai_agent_orchestration.evals.types.landing_page_builder import (
    LandingPageOutput,
    PresetSectionsOutput,
    TemplateSelectionOutput,
)
from wwai_agent_orchestration.evals.types.landing_page_builder.judge import (
    TemplateEvalJudgeResult,
    parse_template_eval_result,
)

__all__ = [
    "EvalCase",
    "EvalSet",
    "RunRecord",
    "LandingPageOutput",
    "PresetSectionsOutput",
    "TemplateSelectionOutput",
    "TemplateEvalJudgeResult",
    "parse_template_eval_result",
]

