"""Extractor for landing page workflow outputs."""

from typing import Any, Dict, List

from wwai_agent_orchestration.evals.graph_output_extractors.landing_page_builder.preset_sections_extractor import (
    _extract_html_results,
    _get_generation_version_id,
)
from wwai_agent_orchestration.evals.graph_output_extractors.landing_page_builder.template_selection_extractor import (
    _load_from_resolved_recommendations,
    _load_templates_from_state,
)
from wwai_agent_orchestration.evals.graph_output_extractors.output_extractor_base import BaseOutputExtractor
from wwai_agent_orchestration.evals.types.landing_page_builder import LandingPageOutput


def _extract_selected_sections(final_state: Dict[str, Any]) -> List[str]:
    """Extract section IDs from templates or resolved_template_recommendations."""
    templates = _load_templates_from_state(final_state)
    if templates:
        first_template = templates[0]
        sections = first_template.get("section_info") or first_template.get("sections") or []
        selected = []
        for section in sections:
            if isinstance(section, dict):
                section_id = section.get("section_id")
                if section_id:
                    selected.append(str(section_id))
        if selected:
            return selected

    # Fallback to resolved_template_recommendations
    _, _, section_ids, _ = _load_from_resolved_recommendations(final_state)
    return section_ids


class LandingPageExtractor(BaseOutputExtractor):
    """Extract final output for end-to-end landing page runs."""

    def extract(self, final_state: Dict[str, Any], history: list[Dict[str, Any]] | None = None) -> LandingPageOutput:
        html_results = _extract_html_results(final_state, history)
        templates = _load_templates_from_state(final_state)
        (
            resolved_template_id,
            resolved_template_name,
            _resolved_section_ids,
            _resolved_section_plan,
        ) = _load_from_resolved_recommendations(final_state)

        first_template = templates[0] if templates else {}
        template_id = (
            first_template.get("template_id")
            or first_template.get("template_name")
            or resolved_template_id
            or resolved_template_name
            or None
        )
        return LandingPageOutput(
            generation_version_id=_get_generation_version_id(final_state),
            html_url=(html_results or {}).get("compiled_html_s3_url") if isinstance(html_results, dict) else None,
            template_id=template_id,
            selected_sections=_extract_selected_sections(final_state),
            artifact_ref=(html_results or {}).get("compiled_html_path") if isinstance(html_results, dict) else None,
            raw_output={"html_compilation_results": html_results} if html_results else {},
        )
