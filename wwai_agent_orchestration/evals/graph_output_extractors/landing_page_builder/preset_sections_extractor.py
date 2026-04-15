"""Extractor for preset sections workflow outputs."""

from typing import Any, Dict

from wwai_agent_orchestration.evals.graph_output_extractors.output_extractor_base import BaseOutputExtractor
from wwai_agent_orchestration.evals.types.landing_page_builder import PresetSectionsOutput


def _to_dict(obj: Any) -> Dict[str, Any]:
    """Convert Pydantic model or dict to dict for uniform access."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return {}


def _extract_html_results(final_state: Dict[str, Any], history: list[Dict[str, Any]] | None) -> Dict[str, Any] | None:
    post_process = _to_dict(final_state.get("post_process"))
    html_results = post_process.get("html_compilation_results")
    if html_results and isinstance(html_results, dict):
        return html_results
    if not history:
        return None
    for checkpoint in reversed(history):
        channel_values = checkpoint.get("channel_values", {})
        pp = _to_dict(channel_values.get("post_process"))
        html_results = pp.get("html_compilation_results")
        if html_results and isinstance(html_results, dict):
            return html_results
        for write in checkpoint.get("writes", []):
            if write.get("channel") == "post_process":
                value = _to_dict(write.get("value"))
                html_results = value.get("html_compilation_results")
                if html_results and isinstance(html_results, dict):
                    return html_results
    return None


def _get_generation_version_id(final_state: Dict[str, Any]) -> str | None:
    """Read generation_version_id from post_process, top-level state, or input."""
    post_process = _to_dict(final_state.get("post_process"))
    tcr = post_process.get("template_compilation_results")
    if isinstance(tcr, dict) and tcr.get("generation_version_id"):
        return tcr.get("generation_version_id")
    gvid = final_state.get("generation_version_id")
    if gvid is not None:
        return gvid
    inp = _to_dict(final_state.get("input"))
    gvid = inp.get("generation_version_id")
    if gvid is not None:
        return gvid
    return inp.get("request_id")


class PresetSectionsExtractor(BaseOutputExtractor):
    """Extract final output for preset sections runs."""

    def extract(self, final_state: Dict[str, Any], history: list[Dict[str, Any]] | None = None) -> PresetSectionsOutput:
        html_results = _extract_html_results(final_state, history)
        # execution_config is at state root; fallback to input.execution_config, then input.section_ids.
        exec_config = _to_dict(final_state.get("execution_config"))
        routing = exec_config.get("routing") or {}
        section_ids = (routing.get("section_ids") or []) if isinstance(routing, dict) else []
        if not section_ids:
            inp = _to_dict(final_state.get("input"))
            inp_exec = _to_dict(inp.get("execution_config"))
            inp_routing = inp_exec.get("routing") or {}
            section_ids = (inp_routing.get("section_ids") or []) if isinstance(inp_routing, dict) else []
        if not section_ids:
            inp = _to_dict(final_state.get("input"))
            section_ids = inp.get("section_ids") or []
        return PresetSectionsOutput(
            section_ids=section_ids or [],
            generation_version_id=_get_generation_version_id(final_state),
            html_url=(html_results or {}).get("compiled_html_s3_url") if isinstance(html_results, dict) else None,
            artifact_ref=(html_results or {}).get("compiled_html_path") if isinstance(html_results, dict) else None,
            raw_output={"html_compilation_results": html_results} if html_results else {},
        )
