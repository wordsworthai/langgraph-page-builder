"""Factory for building eval sets by type, with optional sampling."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from wwai_agent_orchestration.evals.sets.landing_page_builder import (
    build_color_palette_eval_set,
    build_curated_pages_eval_set,
    build_landing_page_eval_set,
    build_section_coverage_eval_set,
    build_template_selection_eval_set,
)
from wwai_agent_orchestration.evals.types.eval_set import EvalSet


def _load_sections_for_coverage(
    section_query_filter: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Load sections from repository for section coverage eval set building."""
    from wwai_agent_orchestration.data.repositories.section_repository import (
        SectionRepositoryService,
    )

    service = SectionRepositoryService()
    sections = service.fetch_sections_with_metadata(query_filter=section_query_filter)
    print(f"Loaded {len(sections)} sections for section coverage eval set building.")
    return sections


def _sample_eval_set(eval_set: EvalSet, max_cases: int) -> EvalSet:
    """Return a new EvalSet with cases capped to max_cases and '(sampled)' in description."""
    return EvalSet(
        eval_set_id=eval_set.eval_set_id,
        eval_type=eval_set.eval_type,
        version=eval_set.version,
        seed=eval_set.seed,
        description=f"{eval_set.description or ''} (sampled)".strip(),
        cases=eval_set.cases[:max_cases],
    )


def build_eval_set(
    *,
    eval_set_id: str,
    eval_type: str,
    version: str,
    seed: int,
    business_ids: Iterable[str],
    middle_section_count: int = 3,
    section_query_filter: Optional[Dict[str, Any]] = None,
    max_cases: Optional[int] = None,
    fixed_visual_inputs: Optional[Dict[str, Any]] = None,
    preset_template_id: str = "default",
    palette_ids: Optional[List[str]] = None,
    homepage_generation_version_id: Optional[str] = None,
    curated_page_paths: Optional[List[str]] = None,
) -> EvalSet:
    """Build eval set by eval type."""
    if eval_type == "landing_page":
        result = build_landing_page_eval_set(
            eval_set_id=eval_set_id,
            version=version,
            seed=seed,
            business_ids=business_ids,
        )
    elif eval_type == "template_selection":
        result = build_template_selection_eval_set(
            eval_set_id=eval_set_id,
            version=version,
            seed=seed,
            business_ids=business_ids,
        )
    elif eval_type == "section_coverage":
        sections = _load_sections_for_coverage(section_query_filter)
        result = build_section_coverage_eval_set(
            eval_set_id=eval_set_id,
            version=version,
            seed=seed,
            business_ids=business_ids,
            middle_section_count=middle_section_count,
            sections=sections,
            fixed_visual_inputs=fixed_visual_inputs,
        )
    elif eval_type == "color_palette":
        result = build_color_palette_eval_set(
            eval_set_id=eval_set_id,
            version=version,
            seed=seed,
            business_ids=business_ids,
            preset_template_id=preset_template_id,
            palette_ids=palette_ids,
        )
    elif eval_type == "curated_pages":
        if not homepage_generation_version_id:
            raise ValueError("homepage_generation_version_id is required for curated_pages eval type")
        result = build_curated_pages_eval_set(
            eval_set_id=eval_set_id,
            version=version,
            seed=seed,
            business_ids=business_ids,
            homepage_generation_version_id=homepage_generation_version_id,
            curated_page_paths=curated_page_paths,
            max_cases=max_cases,
        )
    else:
        raise ValueError(f"Unsupported eval_type: {eval_type}")

    if max_cases is not None and len(result.cases) > max_cases:
        result = _sample_eval_set(result, max_cases)
    return result
