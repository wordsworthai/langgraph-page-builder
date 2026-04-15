"""Deterministic eval set builder for template selection workflow."""

from typing import Iterable, Optional

from pipeline.user_website_input_choices import get_all_purpose_options
from wwai_agent_orchestration.contracts.landing_page_builder.user_input import (
    ExternalDataContext,
    GenericContext,
    WebsiteContext,
)
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_inputs import (
    TemplateSelectionInput,
    template_selection_input_to_dict,
)
from wwai_agent_orchestration.evals.sets.landing_page_builder.base_builder import (
    build_visual_inputs,
    finalize_case,
)
from wwai_agent_orchestration.evals.types.eval_case import EvalCase
from wwai_agent_orchestration.evals.types.eval_set import EvalSet


def build_template_selection_eval_set(
    *,
    eval_set_id: str,
    version: str,
    seed: int,
    business_ids: Iterable[str],
    purpose_ids: Optional[list[str]] = None,
) -> EvalSet:
    """Build deterministic business x purpose eval cases for template selection."""
    businesses = list(business_ids)
    if not businesses:
        raise ValueError("business_ids cannot be empty.")

    if purpose_ids is None:
        purpose_ids = [purpose["id"] for purpose in get_all_purpose_options()]

    cases: list[EvalCase] = []
    case_index = 0
    for business_index, business_id in enumerate(businesses):
        for purpose_id in purpose_ids:
            visual_inputs = build_visual_inputs(seed + case_index)
            tsi = TemplateSelectionInput(
                business_name="",
                business_id=business_id,
                execution_config=None,
                request_id="",
                generic_context=GenericContext(query=""),
                website_context=WebsiteContext(
                    website_intention=purpose_id,
                    website_tone=visual_inputs["website_tone"],
                ),
                external_data_context=ExternalDataContext(yelp_url=""),
            )
            case = EvalCase(
                case_id="",
                eval_set_id=eval_set_id,
                eval_type="template_selection",
                workflow_mode="template_selection",
                set_inputs={
                    "business_id": business_id,
                    "business_index": business_index,
                    "website_intention": purpose_id,
                    "website_tone": visual_inputs["website_tone"],
                },
                workflow_inputs={"template_selection_input": template_selection_input_to_dict(tsi)},
            )
            cases.append(finalize_case(case=case, eval_set_version=version))
            case_index += 1

    return EvalSet(
        eval_set_id=eval_set_id,
        eval_type="template_selection",
        version=version,
        seed=seed,
        description="Template selection eval set: business x purpose matrix.",
        cases=cases,
    )
