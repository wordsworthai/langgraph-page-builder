"""
Shared utilities for extracting template_json and section_id_and_index_mapping
from generated_templates_with_values and autopopulation_snapshots.

Used by builder_service (build_template_versions) and merge_source_snapshots.
"""

from typing import Any, Dict, List, Optional, Tuple

from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.utils.landing_page_builder.template.db_service import (
    template_db_service,
)

logger = get_logger(__name__)


def get_template_json_from_generated_templates(
    generation_version_id: str,
) -> Optional[Tuple[Dict[str, Any], List[Tuple[str, int]]]]:
    """
    Extract template_json and section_id_and_index_mapping from
    generated_templates_with_values (reflects user edits).

    Returns (template_json, section_id_and_index_mapping) or None if doc/tbo missing.
    """
    doc = template_db_service.get_compiled_template(generation_version_id)
    if not doc:
        return None, None

    tbo = doc.get("template_build_output")
    if not tbo:
        return None, None

    sections = tbo.get("sections", {})
    if isinstance(sections, dict):
        sections_dict = sections
    else:
        sections_dict = {
            k: v.model_dump() if hasattr(v, "model_dump") else v
            for k, v in (sections or {}).items()
        }

    enabled_ids = tbo.get("enabled_section_ids", [])
    if not enabled_ids and hasattr(tbo, "enabled_section_ids"):
        enabled_ids = list(tbo.enabled_section_ids or [])

    if not enabled_ids:
        return None, None

    template_json: Dict[str, Any] = {}
    for sid in enabled_ids:
        sec = sections_dict.get(sid)
        if not sec:
            continue
        compiler_deps = sec.get("compiler_deps", {})
        if hasattr(compiler_deps, "template_json_for_compiler"):
            tj = compiler_deps.template_json_for_compiler
        else:
            tj = (compiler_deps or {}).get("template_json_for_compiler", {})
        if isinstance(tj, dict):
            template_json[sid] = tj
        elif hasattr(tj, "model_dump"):
            template_json[sid] = tj.model_dump()
        else:
            template_json[sid] = {}

    section_id_and_index_mapping = [(uid, idx) for idx, uid in enumerate(enabled_ids)]
    return template_json, section_id_and_index_mapping


def get_template_json_from_autopopulation_snapshots(
    generation_version_id: str,
) -> Tuple[Dict[str, Any], List]:
    """
    Extract template_json and section_id_and_index_mapping from
    autopopulation_snapshots collection.

    Uses template_db_service.get_snapshot (sync), reads last_label,
    returns (template_json, section_id_and_index_mapping).

    Raises ValueError if doc/last_label/snapshot/template_json/section_id_and_index_mapping missing.
    """
    snapshot_doc = template_db_service.get_snapshot(generation_version_id)
    if snapshot_doc is None:
        raise ValueError(
            f"No snapshot document found for generation_version_id: {generation_version_id}"
        )

    last_label = snapshot_doc.get("last_label")
    if last_label is None:
        raise ValueError(
            f"last_label is missing in snapshot document for "
            f"generation_version_id={generation_version_id}"
        )

    snapshots = snapshot_doc.get("snapshots", {})
    if last_label not in snapshots:
        raise ValueError(
            f"Snapshot with label '{last_label}' not found in snapshots for "
            f"generation_version_id={generation_version_id}"
        )

    snapshot_data = snapshots[last_label]
    populated_template_json = snapshot_data.get("template_json")
    summary = snapshot_data.get("summary") or {}
    section_id_and_index_mapping = summary.get("section_id_and_index_mapping")

    if populated_template_json is None:
        raise ValueError(
            f"template_json is missing in snapshot '{last_label}' for "
            f"generation_version_id={generation_version_id}"
        )
    if section_id_and_index_mapping is None:
        raise ValueError(
            f"section_id_and_index_mapping is missing in snapshot '{last_label}' for "
            f"generation_version_id={generation_version_id}"
        )

    return populated_template_json, section_id_and_index_mapping


def get_template_json_for_population(
    generation_version_id: str,
) -> Optional[Tuple[Dict[str, Any], List]]:
    """
    Get template_json and section_id_and_index_mapping for populated_template_json_override.

    Pick-correct logic: try generated_templates_with_values first (user edits),
    then autopopulation_snapshots (agent output). Returns None if both fail
    (caller uses ipsum lorem).
    """
    result = get_template_json_from_generated_templates(generation_version_id)
    if result is not None:
        return result

    try:
        return get_template_json_from_autopopulation_snapshots(generation_version_id)
    except ValueError as e:
        logger.warning(
            "Both generated_templates and autopopulation_snapshots failed, falling back to ipsum lorem",
            generation_version_id=generation_version_id,
            error=str(e),
        )
        return None
