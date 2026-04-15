"""Deterministic eval set builder for color palette comparison."""

from typing import Iterable, List, Optional

from pipeline.user_website_input_choices import (
    get_color_palette_and_font,
    get_color_palette_and_font_by_id,
    get_expanded_palettes,
    get_purpose_options,
    get_tone_options,
)
from wwai_agent_orchestration.constants.preset_templates import PRESET_TEMPLATES
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
    finalize_case,
)
from wwai_agent_orchestration.evals.types.eval_case import EvalCase
from wwai_agent_orchestration.evals.types.eval_set import EvalSet


def build_color_palette_eval_set(
    *,
    eval_set_id: str,
    version: str,
    seed: int,
    business_ids: Iterable[str],
    preset_template_id: str = "default",
    palette_ids: Optional[List[str]] = None,
) -> EvalSet:
    """Build eval set with same template and business, varying only color palette.

    Args:
        palette_ids: Optional list of palette IDs (e.g. ["friendly-1", "bold-2"]).
            When provided, only build cases for these palettes. When None, use all palettes.
    """
    businesses = list(business_ids)
    if not businesses:
        raise ValueError("business_ids cannot be empty.")

    if preset_template_id not in PRESET_TEMPLATES:
        raise ValueError(
            f"preset_template_id '{preset_template_id}' not in PRESET_TEMPLATES: "
            f"{list(PRESET_TEMPLATES.keys())}"
        )
    section_ids = PRESET_TEMPLATES[preset_template_id]
    if not section_ids:
        raise ValueError(f"Preset template '{preset_template_id}' has no section IDs.")

    expanded = get_expanded_palettes()
    if not expanded:
        raise ValueError("No color palettes available.")

    if palette_ids is not None:
        if not palette_ids:
            raise ValueError("palette_ids cannot be empty when provided.")
        palette_indices_or_ids: List[tuple[int | None, str | None]] = [
            (None, pid) for pid in palette_ids
        ]
    else:
        palette_indices_or_ids = [(i, None) for i in range(len(expanded))]

    business_id = businesses[0]
    purpose_id = get_purpose_options(index=seed)
    tone_id = get_tone_options(index=seed)

    cases: List[EvalCase] = []
    for case_index, (palette_index, palette_id_filter) in enumerate(palette_indices_or_ids):
        if palette_id_filter is not None:
            palette_data = get_color_palette_and_font_by_id(palette_id_filter)
            if palette_data is None:
                valid_ids = [e["palette"]["id"] for e in expanded]
                raise ValueError(
                    f"Unknown palette_id '{palette_id_filter}'. Valid IDs: {valid_ids}"
                )
            palette_index = next(
                i for i, e in enumerate(expanded) if e["palette"]["id"] == palette_id_filter
            )
        else:
            palette_data = get_color_palette_and_font(index=palette_index)
        palette = palette_data["PALETTE"]
        font_family = palette_data["FONT_FAMILY"]

        psi = PresetSectionsInput(
            business_name="",
            business_id=business_id,
            request_id="",
            section_ids=section_ids,
            execution_config=None,
            generic_context=GenericContext(query=""),
            website_context=WebsiteContext(
                website_intention=purpose_id,
                website_tone=tone_id,
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
            eval_type="color_palette",
            workflow_mode="preset_sections",
            set_inputs={
                "business_id": business_id,
                "business_index": 0,
                "website_intention": purpose_id,
                "website_tone": tone_id,
                "palette_index": palette_index,
                "palette_id": palette.get("palette_id", ""),
            },
            workflow_inputs={"preset_sections_input": preset_sections_input_to_dict(psi)},
            metadata={"preset_template_id": preset_template_id},
        )
        cases.append(finalize_case(case=case, eval_set_version=version))

    return EvalSet(
        eval_set_id=eval_set_id,
        eval_type="color_palette",
        version=version,
        seed=seed,
        description="Color palette eval set: same template and business, varying palettes.",
        cases=cases,
    )
