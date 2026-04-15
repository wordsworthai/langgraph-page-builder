"""Extractor for template selection workflow outputs."""

from typing import Any, Dict, List, Tuple

from wwai_agent_orchestration.evals.graph_output_extractors.landing_page_builder.preset_sections_extractor import (
    _extract_html_results,
    _get_generation_version_id,
)
from wwai_agent_orchestration.evals.graph_output_extractors.output_extractor_base import BaseOutputExtractor
from wwai_agent_orchestration.evals.types.landing_page_builder import TemplateSelectionOutput


def _to_dict(obj: Any) -> Dict[str, Any]:
    """Convert Pydantic model or dict to dict for uniform access."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return {}


def _load_templates_from_state(final_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Load templates from state: root, nested template channel, or resolved_template_recommendations."""
    # Root (backward compat with fixtures)
    templates = final_state.get("refined_templates") or final_state.get("templates") or []
    if templates:
        return templates

    # Nested template channel (TemplateResult)
    template_channel = final_state.get("template")
    t = _to_dict(template_channel)
    templates = t.get("refined_templates") or t.get("templates") or []
    if templates:
        return templates

    # Fallback: derive from resolved_template_recommendations
    resolved = final_state.get("resolved_template_recommendations") or []
    if resolved:
        first = _to_dict(resolved[0]) if resolved else {}
        section_mappings = first.get("section_mappings") or []
        section_info = [
            {"section_id": m.get("section_id"), "section_l0": m.get("section_l0"), "section_l1": m.get("section_l1")}
            for m in section_mappings
            if isinstance(m, dict)
        ]
        template_like = {
            "template_id": first.get("template_id"),
            "template_name": first.get("template_name"),
            "section_info": section_info,
            "section_mappings": section_mappings,
        }
        return [template_like]

    return []


def _load_from_resolved_recommendations(
    final_state: Dict[str, Any],
) -> Tuple[str | None, str | None, List[str], List[Dict[str, Any]]]:
    """Extract (template_id, template_name, section_ids, section_plan) from resolved_template_recommendations."""
    resolved = final_state.get("resolved_template_recommendations") or []
    if not resolved:
        return None, None, [], []
    first = _to_dict(resolved[0])
    template_id = first.get("template_id")
    template_name = first.get("template_name")
    section_mappings = first.get("section_mappings") or []
    section_ids = [str(m["section_id"]) for m in section_mappings if isinstance(m, dict) and m.get("section_id")]
    section_plan = [m for m in section_mappings if isinstance(m, dict)]
    return template_id, template_name, section_ids, section_plan


class TemplateSelectionExtractor(BaseOutputExtractor):
    """Extract final output for template selection runs."""

    def extract(
        self, final_state: Dict[str, Any], history: list[Dict[str, Any]] | None = None
    ) -> TemplateSelectionOutput:
        templates = _load_templates_from_state(final_state)
        (
            resolved_template_id,
            _resolved_template_name,
            _resolved_section_ids,
            resolved_section_plan,
        ) = _load_from_resolved_recommendations(final_state)

        selected_template = templates[0] if templates else {}
        selected_id = (
            selected_template.get("template_id")
            or selected_template.get("template_name")
            or resolved_template_id
            or None
        )
        section_plan = (
            selected_template.get("section_info")
            or selected_template.get("sections")
            or (resolved_section_plan if resolved_section_plan else None)
        )
        html_results = _extract_html_results(final_state, history)
        html_url = (html_results or {}).get("compiled_html_s3_url") if isinstance(html_results, dict) else None
        return TemplateSelectionOutput(
            template_id=selected_id,
            selected_template_index=0 if templates else None,
            rationale=selected_template.get("reasoning"),
            section_plan=section_plan,
            generation_version_id=_get_generation_version_id(final_state),
            html_url=html_url,
            raw_output={"templates": templates, "template_count": len(templates)},
        )
