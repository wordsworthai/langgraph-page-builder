"""Deterministic eval set builder for preset-sections coverage."""

from typing import Any, Dict, Iterable, List, Optional

from pipeline.user_website_input_choices import get_purpose_options
from wwai_agent_orchestration.constants.section_types import (
    FOOTER_SECTION_L0_LIST,
    HEADER_SECTION_L0_LIST,
)
from wwai_agent_orchestration.contracts.landing_page_builder.user_input import (
    BrandContext,
    ExternalDataContext,
    GenericContext,
    WebsiteContext,
)
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_inputs import (
    PresetSectionsInput,
    preset_sections_input_to_dict,
)
from wwai_agent_orchestration.evals.sets.landing_page_builder.base_builder import (
    build_visual_inputs,
    finalize_case,
)
from wwai_agent_orchestration.evals.types.eval_case import EvalCase
from wwai_agent_orchestration.evals.types.eval_set import EvalSet


def _section_id(section: Dict[str, Any]) -> str:
    value = section.get("section_id") or section.get("_id")
    if value is None:
        raise ValueError(f"Section is missing identifier: {section}")
    return str(value)


def _validate_full_section_coverage(
    cases: list,
    header_sections: List[Dict[str, Any]],
    footer_sections: List[Dict[str, Any]],
    middle_sections: List[Dict[str, Any]],
) -> None:
    """Raise ValueError if any header, footer, or middle section is not used in any case."""
    used: set[str] = set()
    for case in cases:
        used.update(
            case.workflow_inputs["preset_sections_input"]["section_ids"]
        )
    expected_headers = {_section_id(s) for s in header_sections}
    expected_footers = {_section_id(s) for s in footer_sections}
    expected_middle = {_section_id(s) for s in middle_sections}
    missing = (
        (expected_headers - used) | (expected_footers - used) | (expected_middle - used)
    )
    if missing:
        raise ValueError(f"Sections not used in any case: {sorted(missing)}")


def build_section_coverage_eval_set(
    *,
    eval_set_id: str,
    version: str,
    seed: int,
    business_ids: Iterable[str],
    middle_section_count: int = 3,
    sections: List[Dict[str, Any]],
    fixed_visual_inputs: Optional[Dict[str, Any]] = None,
) -> EvalSet:
    """Build deterministic preset-section cases with one-way section coverage."""
    businesses = list(business_ids)
    if not businesses:
        raise ValueError("business_ids cannot be empty.")
    if middle_section_count < 1:
        raise ValueError("middle_section_count must be >= 1.")

    all_sections = sections
    if not all_sections:
        raise ValueError("No sections available to build section coverage eval set.")

    header_sections = sorted(
        [
            section
            for section in all_sections
            if section.get("section_l0") in HEADER_SECTION_L0_LIST
        ],
        key=_section_id,
    )
    footer_sections = sorted(
        [
            section
            for section in all_sections
            if section.get("section_l0") in FOOTER_SECTION_L0_LIST
        ],
        key=_section_id,
    )
    middle_sections = sorted(
        [
            section
            for section in all_sections
            if section.get("section_l0") not in HEADER_SECTION_L0_LIST
            and section.get("section_l0") not in FOOTER_SECTION_L0_LIST
        ],
        key=_section_id,
    )

    if not header_sections:
        raise ValueError("No header sections found for coverage eval set.")
    if not footer_sections:
        raise ValueError("No footer sections found for coverage eval set.")
    if not middle_sections:
        raise ValueError("No middle sections found for coverage eval set.")

    num_middle_chunks = (
        len(middle_sections) + middle_section_count - 1
    ) // middle_section_count
    num_cases = max(
        num_middle_chunks, len(header_sections), len(footer_sections)
    )

    cases: list[EvalCase] = []
    for case_index in range(num_cases):
        chunk_index = case_index % num_middle_chunks
        chunk_start = chunk_index * middle_section_count
        middle_chunk = middle_sections[chunk_start : chunk_start + middle_section_count]
        chunk_ids = [_section_id(section) for section in middle_chunk]
        header_id = _section_id(header_sections[case_index % len(header_sections)])
        footer_id = _section_id(footer_sections[case_index % len(footer_sections)])
        section_ids = [header_id, *chunk_ids, footer_id]

        business_id = businesses[case_index % len(businesses)]
        business_index = case_index % len(businesses)
        index_seed = seed + case_index
        visual_inputs = build_visual_inputs(index_seed)
        purpose_id = get_purpose_options(index=index_seed)
        palette = fixed_visual_inputs["palette"] if fixed_visual_inputs else visual_inputs["palette"]
        font_family = fixed_visual_inputs["font_family"] if fixed_visual_inputs else visual_inputs["font_family"]
        psi = PresetSectionsInput(
            business_name="",
            business_id=business_id,
            request_id="",
            section_ids=section_ids,
            execution_config=None,
            generic_context=GenericContext(query=""),
            website_context=WebsiteContext(
                website_intention=purpose_id,
                website_tone=visual_inputs["website_tone"],
            ),
            brand_context=BrandContext(
                palette=palette,
                font_family=font_family,
            ),
            external_data_context=ExternalDataContext(yelp_url=""),
        )
        case = EvalCase(
            case_id="",
            eval_set_id=eval_set_id,
            eval_type="section_coverage",
            workflow_mode="preset_sections",
            set_inputs={
                "business_id": business_id,
                "business_index": business_index,
                "website_intention": purpose_id,
                "website_tone": visual_inputs["website_tone"],
            },
            workflow_inputs={"preset_sections_input": preset_sections_input_to_dict(psi)},
            metadata={"coverage_chunk_size": middle_section_count},
        )
        cases.append(finalize_case(case=case, eval_set_version=version))

    _validate_full_section_coverage(
        cases, header_sections, footer_sections, middle_sections
    )

    return EvalSet(
        eval_set_id=eval_set_id,
        eval_type="section_coverage",
        version=version,
        seed=seed,
        description="Section coverage eval set using preset sections.",
        cases=cases,
    )
