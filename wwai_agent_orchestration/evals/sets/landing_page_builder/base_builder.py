"""Shared helpers for deterministic eval set builders."""

from typing import Dict

from pipeline.user_website_input_choices import (
    get_color_palette_and_font,
    get_tone_options,
)
from wwai_agent_orchestration.evals.types.eval_case import EvalCase
from wwai_agent_orchestration.evals.utils.hashing import build_case_id


def build_visual_inputs(index_seed: int) -> Dict[str, object]:
    """Build deterministic palette/font/tone inputs for a case index."""
    palette_and_font = get_color_palette_and_font(index=index_seed)
    tone_id = get_tone_options(index=index_seed)
    return {
        "palette": palette_and_font["PALETTE"],
        "font_family": palette_and_font["FONT_FAMILY"],
        "website_tone": tone_id,
    }


def finalize_case(*, case: EvalCase, eval_set_version: str) -> EvalCase:
    """Attach deterministic case id from normalized case fields."""
    case.case_id = build_case_id(
        eval_set_version=eval_set_version,
        eval_type=case.eval_type,
        workflow_mode=case.workflow_mode,
        set_inputs=case.set_inputs,
        workflow_inputs=case.workflow_inputs,
    )
    return case
