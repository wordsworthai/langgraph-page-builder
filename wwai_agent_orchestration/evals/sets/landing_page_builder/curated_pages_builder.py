"""Deterministic eval set builder for curated pages from section_repo_prod.curated_pages."""

from typing import Iterable, List, Optional

from bson import ObjectId

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
from wwai_agent_orchestration.data.providers.section_catalog_provider import (
    SectionCatalogProvider,
)
from wwai_agent_orchestration.evals.sets.landing_page_builder.base_builder import (
    build_visual_inputs,
    finalize_case,
)
from wwai_agent_orchestration.evals.types.eval_case import EvalCase
from wwai_agent_orchestration.evals.types.eval_set import EvalSet
from wwai_agent_orchestration.utils.landing_page_builder.template_utils import (
    get_curated_pages,
)


def _filter_out_header_footer_sections(section_ids: List[str]) -> List[str]:
    """
    Filter out header/footer sections; return only body section IDs in order.
    Uses section repo to look up section_l0 for each ID.
    """
    if not section_ids:
        return []
    disallowed_l0 = set(HEADER_SECTION_L0_LIST) | set(FOOTER_SECTION_L0_LIST)
    try:
        provider = SectionCatalogProvider()
        sections = provider.fetch_sections_with_metadata(
            query_filter={"_id": {"$in": [ObjectId(sid) for sid in section_ids]}}
        )
    except Exception:
        return section_ids  # Fallback: use all if lookup fails

    id_to_l0 = {str(s.get("_id", "")): s.get("section_l0", "") for s in sections}
    return [
        sid for sid in section_ids
        if id_to_l0.get(sid, "") not in disallowed_l0
    ]


def _is_homepage(page_path: str) -> bool:
    """True if page_path indicates a homepage (no parent needed)."""
    return (page_path or "").strip() in ("", "/", "homepage")


def build_curated_pages_eval_set(
    *,
    eval_set_id: str,
    version: str,
    seed: int,
    business_ids: Iterable[str],
    homepage_generation_version_id: str,
    curated_page_paths: Optional[List[str]] = None,
    max_cases: Optional[int] = None,
) -> EvalSet:
    """
    Build eval set from curated pages in section_repo_prod.curated_pages.

    Each curated page becomes one EvalCase. Body section IDs are filtered
    (header/footer removed). Non-homepage pages use parent_generation_version_id
    for header/footer merge at compilation.
    """
    businesses = list(business_ids)
    if not businesses:
        raise ValueError("business_ids cannot be empty.")
    if not homepage_generation_version_id or not homepage_generation_version_id.strip():
        raise ValueError("homepage_generation_version_id is required.")

    response = get_curated_pages()
    all_pages = response.pages

    if curated_page_paths is not None:
        path_set = set(curated_page_paths)
        pages = [p for p in all_pages if p.page_path in path_set]
    else:
        pages = list(all_pages)

    if not pages:
        raise ValueError(
            "No curated pages found. "
            "Ensure section_repo_prod.curated_pages has documents, "
            "or pass curated_page_paths to filter."
        )

    cases: List[EvalCase] = []
    for case_index, page in enumerate(pages):
        body_section_ids = _filter_out_header_footer_sections(page.section_ids or [])
        if not body_section_ids:
            continue

        business_id = businesses[case_index % len(businesses)]
        business_index = case_index % len(businesses)
        index_seed = seed + case_index
        visual_inputs = build_visual_inputs(index_seed)
        purpose_id = get_purpose_options(index=index_seed)

        is_homepage = _is_homepage(page.page_path)
        page_type = "homepage" if is_homepage else page.page_path
        parent_gvid = None if is_homepage else homepage_generation_version_id

        psi = PresetSectionsInput(
            business_name="",
            business_id=business_id,
            request_id="",
            section_ids=body_section_ids,
            execution_config=None,
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
            page_type=page_type,
            parent_generation_version_id=parent_gvid,
        )

        case = EvalCase(
            case_id="",
            eval_set_id=eval_set_id,
            eval_type="curated_pages",
            workflow_mode="preset_sections",
            set_inputs={
                "business_id": business_id,
                "business_index": business_index,
                "page_path": page.page_path,
                "page_title": page.page_title,
                "website_intention": purpose_id,
                "website_tone": visual_inputs["website_tone"],
            },
            workflow_inputs={"preset_sections_input": preset_sections_input_to_dict(psi)},
            metadata={
                "page_path": page.page_path,
                "page_title": page.page_title,
                "body_section_count": len(body_section_ids),
            },
        )
        cases.append(finalize_case(case=case, eval_set_version=version))

    if not cases:
        raise ValueError(
            "No eval cases generated. All curated pages had no body sections "
            "after filtering header/footer."
        )

    if max_cases is not None and len(cases) > max_cases:
        cases = cases[:max_cases]

    return EvalSet(
        eval_set_id=eval_set_id,
        eval_type="curated_pages",
        version=version,
        seed=seed,
        description="Curated pages eval set from section_repo_prod.curated_pages.",
        cases=cases,
    )
