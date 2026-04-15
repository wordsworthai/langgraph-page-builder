"""
Section add-in-place utilities. Adds or replaces sections in a generation's 3 DBs
without creating a new generation. Used when user drops a section (lorem content).
"""

from typing import Any, Dict, List, Optional, Tuple

from wwai_agent_orchestration.utils.landing_page_builder.section_db_utils import (
    get_section_doc_and_mapping,
)
from wwai_agent_orchestration.utils.landing_page_builder.template.builder_service import (
    template_builder_service,
)
from wwai_agent_orchestration.utils.landing_page_builder.template.db_service import (
    template_db_service,
)


def _validate_add_section_params(
    mode: str,
    insert_index: int,
    replace_index: Optional[int],
) -> Tuple[int, int]:
    """Validate and normalize params. Returns (insert_index, target_index)."""
    if mode == "insert" and insert_index == -1:
        insert_index = 0
    if mode == "replace" and replace_index is None:
        raise ValueError("replace_index is required when mode='replace'")
    target_index = replace_index if mode == "replace" else insert_index
    return insert_index, target_index


async def _compile_new_section_lorem(
    section_id: str,
) -> Tuple[str, Dict[str, Any], Any]:
    """
    Compile section with ipsum lorem, extract template_json.
    Returns (new_section_unique_id, new_section_template_json, new_section_build_data).
    """
    new_section_tbo = await template_builder_service.compile_section_template(
        section_id=section_id,
    )
    if not new_section_tbo.sections or not new_section_tbo.enabled_section_ids:
        raise ValueError(f"No section data for section_id={section_id}")

    new_section_unique_id_from_tbo = new_section_tbo.enabled_section_ids[0]
    new_section_build_data = new_section_tbo.sections[new_section_unique_id_from_tbo]
    compiler_deps = new_section_build_data.compiler_deps
    if hasattr(compiler_deps, "template_json_for_compiler"):
        template_json_for_compiler = compiler_deps.template_json_for_compiler
    else:
        template_json_for_compiler = (compiler_deps or {}).get(
            "template_json_for_compiler", {}
        )
    if isinstance(template_json_for_compiler, dict):
        new_section_template_json = template_json_for_compiler
    else:
        new_section_template_json = (
            template_json_for_compiler.model_dump()
            if hasattr(template_json_for_compiler, "model_dump")
            else {}
        )
    return new_section_unique_id_from_tbo, new_section_template_json, new_section_build_data


def _apply_modification_and_rebuild_sections(
    generation_version_id: str,
    section_id: str,
    new_section_mapping: Dict[str, Any],
    section_doc: Dict[str, Any],
    mode: str,
    insert_index: int,
    replace_index: Optional[int],
    new_section_unique_id_from_tbo: str,
) -> Tuple[Dict[str, str], str, int]:
    """
    Get merged, apply_section_modification, rebuild generation_template_sections.
    Returns (template_unique_section_id_map, new_unique_id, target_index).
    """
    merged = template_db_service.get_merged_all(generation_version_id)
    existing_mappings = list(merged.get("section_mappings", []))
    if not existing_mappings:
        raise ValueError(
            f"No section_mappings in generation_template_sections for {generation_version_id}"
        )

    updated_mappings, template_unique_section_id_map = (
        template_builder_service.apply_section_modification(
            mode=mode,
            existing_mappings=existing_mappings,
            new_section_mapping=new_section_mapping,
            section_doc=section_doc,
            source_thread_id=generation_version_id,
            generation_version_id=generation_version_id,
            insert_index=insert_index,
            replace_index=replace_index,
        )
    )

    target_index = replace_index if mode == "replace" else insert_index
    new_section_mapping["section_index"] = target_index + 1

    full_mapping: List[tuple] = []
    for i, m in enumerate(updated_mappings):
        sid = m.get("section_id", "")
        key = f"{sid}_{i}"
        uid = template_unique_section_id_map.get(key, f"{sid}_unknown")
        full_mapping.append((uid, i))

    template_db_service.rebuild_template_sections(
        generation_version_id=generation_version_id,
        full_mapping=full_mapping,
        new_section_mapping=new_section_mapping,
        target_index=target_index,
        mode=mode,
    )

    new_unique_id = template_unique_section_id_map.get(
        f"{section_id}_{target_index}", new_section_unique_id_from_tbo
    )
    return template_unique_section_id_map, new_unique_id, target_index


def _patch_autopopulation_snapshots(
    generation_version_id: str,
    new_unique_id: str,
    new_section_template_json: Dict[str, Any],
    template_unique_section_id_map: Dict[str, str],
    mode: str,
    replace_index: Optional[int],
    target_index: int,
    section_id: str,
) -> None:
    """Add new section to autopopulation_snapshots."""
    snapshot_doc = template_db_service.get_snapshot(generation_version_id)
    if not snapshot_doc:
        return

    snapshots = snapshot_doc.get("snapshots", {})
    final_snap = snapshots.get("final_autopopulation", {})
    source_template_json = dict(final_snap.get("template_json", {}))
    source_template_json[new_unique_id] = new_section_template_json

    source_mapping = (final_snap.get("summary") or {}).get(
        "section_id_and_index_mapping", []
    )
    if mode == "replace" and replace_index is not None:
        full_mapping_for_snap = [
            (entry[0], idx) for idx, entry in enumerate(source_mapping)
        ]
        full_mapping_for_snap[replace_index] = (new_unique_id, replace_index)
    else:
        full_mapping_for_snap = []
        src_idx = 0
        for pos in range(len(source_mapping) + 1):
            if pos == target_index:
                full_mapping_for_snap.append((new_unique_id, pos))
            else:
                if src_idx < len(source_mapping):
                    entry = source_mapping[src_idx]
                    uid = entry[0] if isinstance(entry, (list, tuple)) else entry
                    full_mapping_for_snap.append((uid, pos))
                    src_idx += 1

    patched_snap = {
        **final_snap,
        "template_json": source_template_json,
    }
    if "summary" in patched_snap:
        patched_snap["summary"] = {
            **patched_snap["summary"],
            "section_id_and_index_mapping": full_mapping_for_snap,
        }
    new_snapshots = {**snapshots, "final_autopopulation": patched_snap}
    patched_doc = {**snapshot_doc, "snapshots": new_snapshots}
    patched_doc.pop("_id", None)
    template_db_service.save_snapshot(
        generation_version_id=generation_version_id,
        document=patched_doc,
    )


def _patch_generated_templates_with_values(
    generation_version_id: str,
    new_unique_id: str,
    new_section_build_data: Any,
    section_id: str,
    target_index: int,
    mode: str,
) -> None:
    """Add new section to generated_templates_with_values."""
    compiled_doc = template_db_service.get_compiled_template(generation_version_id)
    if not compiled_doc:
        return

    tbo_dict = compiled_doc.get("template_build_output", {})
    if isinstance(tbo_dict, dict):
        sections_dict = dict(tbo_dict.get("sections", {}))
        enabled = list(tbo_dict.get("enabled_section_ids", []))
        section_id_list = list(tbo_dict.get("section_id_list", []))
    else:
        sections_dict = {
            k: v.model_dump() if hasattr(v, "model_dump") else v
            for k, v in (tbo_dict.sections or {}).items()
        }
        enabled = list(tbo_dict.enabled_section_ids or [])
        section_id_list = list(tbo_dict.section_id_list or [])

    new_section_data = (
        new_section_build_data.model_dump()
        if hasattr(new_section_build_data, "model_dump")
        else dict(new_section_build_data)
    )
    sections_dict[new_unique_id] = new_section_data

    if mode == "replace":
        enabled[target_index] = new_unique_id
        section_id_list[target_index] = section_id
    else:
        enabled.insert(target_index, new_unique_id)
        section_id_list.insert(target_index, section_id)

    from template_json_builder.models.template_build_output import (
        SectionBuildData,
        TemplateBuildOutput,
    )

    sections_out = {
        sid: SectionBuildData.model_validate(s) if isinstance(s, dict) else s
        for sid, s in sections_dict.items()
    }
    modified_tbo = TemplateBuildOutput(
        sections=sections_out,
        enabled_section_ids=enabled,
        section_id_list=section_id_list,
    )

    _, template_unique_section_id_map, section_group_unique_ids, page_type = (
        template_builder_service.get_section_ids_and_map(generation_version_id)
    )
    template_db_service.save_compiled_template(
        generation_version_id=generation_version_id,
        template_build_output=modified_tbo,
        page_type=page_type,
        section_group_unique_ids=section_group_unique_ids,
        template_unique_section_id_map=template_unique_section_id_map,
    )


async def add_section_in_place(
    generation_version_id: str,
    section_id: str,
    insert_index: int,
    mode: str = "insert",
    replace_index: Optional[int] = None,
) -> None:
    """
    Add or replace a section in a generation's 3 DBs in place (no new generation).

    Uses ipsum_lorem content for the new section. Called from external server.
    Updates: generation_template_sections, autopopulation_snapshots, generated_templates_with_values.

    Args:
        generation_version_id: The generation to modify (in-place).
        section_id: Repo ObjectId of the section to add/replace.
        insert_index: Position for insert mode (-1 = beginning).
        mode: "insert" or "replace".
        replace_index: 0-based index for replace mode (required when mode="replace").
    """
    insert_index, target_index = _validate_add_section_params(
        mode=mode,
        insert_index=insert_index,
        replace_index=replace_index,
    )

    (
        new_section_unique_id_from_tbo,
        new_section_template_json,
        new_section_build_data,
    ) = await _compile_new_section_lorem(section_id)

    section_doc, new_section_mapping = get_section_doc_and_mapping(section_id)

    (
        template_unique_section_id_map,
        new_unique_id,
        target_index,
    ) = _apply_modification_and_rebuild_sections(
        generation_version_id=generation_version_id,
        section_id=section_id,
        new_section_mapping=new_section_mapping,
        section_doc=section_doc,
        mode=mode,
        insert_index=insert_index,
        replace_index=replace_index,
        new_section_unique_id_from_tbo=new_section_unique_id_from_tbo,
    )

    _patch_autopopulation_snapshots(
        generation_version_id=generation_version_id,
        new_unique_id=new_unique_id,
        new_section_template_json=new_section_template_json,
        template_unique_section_id_map=template_unique_section_id_map,
        mode=mode,
        replace_index=replace_index,
        target_index=target_index,
        section_id=section_id,
    )

    _patch_generated_templates_with_values(
        generation_version_id=generation_version_id,
        new_unique_id=new_unique_id,
        new_section_build_data=new_section_build_data,
        section_id=section_id,
        target_index=target_index,
        mode=mode,
    )
