"""Deterministic eval set builder for end-to-end landing page workflow."""

from typing import Iterable

from pipeline.user_website_input_choices import get_purpose_options
from wwai_agent_orchestration.contracts.landing_page_builder.user_input import (
    BrandContext,
    ExternalDataContext,
    GenericContext,
    WebsiteContext,
)
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_inputs import (
    LandingPageInput,
    landing_page_input_to_dict,
)
from wwai_agent_orchestration.evals.sets.landing_page_builder.base_builder import (
    build_visual_inputs,
    finalize_case,
)
from wwai_agent_orchestration.evals.types.eval_case import EvalCase
from wwai_agent_orchestration.evals.types.eval_set import EvalSet


def build_landing_page_eval_set(
    *,
    eval_set_id: str,
    version: str,
    seed: int,
    business_ids: Iterable[str],
) -> EvalSet:
    """Build deterministic one-case-per-business landing page eval set."""
    businesses = list(business_ids)
    if not businesses:
        raise ValueError("business_ids cannot be empty.")

    cases: list[EvalCase] = []
    for business_index, business_id in enumerate(businesses):
        case_index = seed + business_index
        purpose_id = get_purpose_options(index=case_index)
        visual_inputs = build_visual_inputs(case_index)
        lpi = LandingPageInput(
            business_name="",
            business_id=business_id,
            execution_config=None,
            request_id="",
            generic_context=GenericContext(query=""),
            website_context=WebsiteContext(
                website_intention=purpose_id,
                website_tone=visual_inputs["website_tone"],
            ),
            brand_context=BrandContext(
                palette=visual_inputs["palette"],
                font_family=visual_inputs["font_family"],
            ),
            external_data_context=ExternalDataContext(yelp_url=""),
        )
        case = EvalCase(
            case_id="",
            eval_set_id=eval_set_id,
            eval_type="landing_page",
            workflow_mode="landing_page",
            set_inputs={
                "business_id": business_id,
                "business_index": business_index,
                "website_intention": purpose_id,
                "website_tone": visual_inputs["website_tone"],
            },
            workflow_inputs={"landing_page_input": landing_page_input_to_dict(lpi)},
        )
        cases.append(finalize_case(case=case, eval_set_version=version))

    return EvalSet(
        eval_set_id=eval_set_id,
        eval_type="landing_page",
        version=version,
        seed=seed,
        description="Landing page eval set: one deterministic case per business.",
        cases=cases,
    )
