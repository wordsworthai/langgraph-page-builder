"""
Pure functions for applying template updates (section_updates, section_order, deleted_sections).
"""

from typing import Dict, Any, List, Optional, Tuple

from template_json_builder.models.template_build_output import (
    TemplateBuildOutput,
    SectionBuildData,
    SectionCompilerDeps,
)
from wwai_agent_orchestration.contracts.landing_page_builder.template_update import SaveTemplateRequest
from wwai_agent_orchestration.utils.landing_page_builder.template.section_utils import section_category


def _section_category(section_l0: str) -> str:
    """Return 'header', 'footer', or 'body'."""
    return section_category(section_l0)


def _validate_section_order(
    section_order: List[str],
    sections: Dict[str, Any],
    existing_section_group_unique_ids: Optional[Dict[str, List[str]]] = None,
) -> None:
    """
    Validate that section_order has header first, body middle, footer last.
    All ids must exist in sections.
    If any header sections exist, the first section must be a header.
    If any footer sections exist, the last section must be a footer.
    When existing_section_group_unique_ids is provided, categories are derived from it;
    otherwise from section_l0 in section_mapping.
    """
    if not section_order:
        return
    cat_order = {"header": 0, "body": 1, "footer": 2}
    prev_cat_rank = -1
    categories: List[str] = []

    if existing_section_group_unique_ids:
        header_set = set(existing_section_group_unique_ids.get("header_unique_ids", []))
        footer_set = set(existing_section_group_unique_ids.get("footer_unique_ids", []))

    for sid in section_order:
        if sid not in sections:
            raise ValueError(
                f"section_order contains id '{sid}' not in sections. "
                f"Valid keys: {list(sections.keys())[:5]}..."
            )
        if existing_section_group_unique_ids:
            if sid in header_set:
                cat = "header"
            elif sid in footer_set:
                cat = "footer"
            else:
                cat = "body"
        else:
            sec = sections[sid]
            mapping = sec.get("section_mapping") if isinstance(sec, dict) else getattr(sec, "section_mapping", {})
            l0 = mapping.get("section_l0", "") if isinstance(mapping, dict) else ""
            cat = _section_category(l0)
        categories.append(cat)
        rank = cat_order.get(cat, 1)
        if rank < prev_cat_rank:
            raise ValueError(
                "section_order must have header first, then body, then footer. "
                f"Found {cat} (rank {rank}) after a later category (rank {prev_cat_rank})."
            )
        prev_cat_rank = rank

    if categories and "header" in categories and categories[0] != "header":
        raise ValueError(
            "Header sections must be at the top. First section must be a header."
        )
    if categories and "footer" in categories and categories[-1] != "footer":
        raise ValueError(
            "Footer sections must be at the bottom. Last section must be a footer."
        )


def apply_template_updates(
    tbo: TemplateBuildOutput,
    request: SaveTemplateRequest,
    existing_section_group_unique_ids: Optional[Dict[str, List[str]]] = None,
) -> TemplateBuildOutput:
    """
    Apply SaveTemplateRequest to TemplateBuildOutput. Returns modified TemplateBuildOutput.
    When existing_section_group_unique_ids is provided, section_order validation uses it for categories.
    """
    sections_dict = {k: v.model_dump() if hasattr(v, "model_dump") else v for k, v in tbo.sections.items()}
    enabled = list(tbo.enabled_section_ids)
    section_id_list = list(tbo.section_id_list)

    # 1. Apply section_updates
    for sid, update in request.section_updates.items():
        if sid not in sections_dict:
            raise ValueError(f"section_updates key '{sid}' not in sections")
        sec = sections_dict[sid]
        compiler_deps = sec.get("compiler_deps", {})
        if isinstance(compiler_deps, dict):
            compiler_deps = dict(compiler_deps)
        else:
            compiler_deps = compiler_deps.model_dump() if hasattr(compiler_deps, "model_dump") else dict(compiler_deps)
        compiler_deps["template_json_for_compiler"] = update.template_json_for_compiler
        sec = dict(sec)
        sec["compiler_deps"] = compiler_deps
        sections_dict[sid] = sec

    # 2. Apply deleted_sections
    if request.deleted_sections:
        for sid in request.deleted_sections:
            if sid in sections_dict:
                del sections_dict[sid]
        enabled = [e for e in enabled if e in sections_dict]
        section_id_list = []
        for e in enabled:
            sec = sections_dict.get(e)
            if sec:
                mapping = sec.get("section_mapping") or {}
                repo_id = mapping.get("section_id", e.rsplit("_", 1)[0])
            else:
                repo_id = e.rsplit("_", 1)[0]
            section_id_list.append(repo_id)

    if not sections_dict:
        raise ValueError("Cannot delete all sections; at least one section must remain.")

    # 3. Apply section_order
    if request.section_order:
        _validate_section_order(
            request.section_order,
            sections_dict,
            existing_section_group_unique_ids=existing_section_group_unique_ids,
        )
        order_in_dict = [s for s in request.section_order if s in sections_dict]
        for sid in request.section_order:
            if sid not in sections_dict:
                raise ValueError(f"section_order contains id '{sid}' not in sections (or deleted)")
        remaining = [s for s in enabled if s not in order_in_dict]
        enabled = order_in_dict + remaining
        section_id_list = []
        for e in enabled:
            sec = sections_dict.get(e)
            if sec:
                mapping = sec.get("section_mapping") or {}
                repo_id = mapping.get("section_id", e.rsplit("_", 1)[0])
            else:
                repo_id = e.rsplit("_", 1)[0]
            section_id_list.append(repo_id)

    sections_out = {}
    for sid, sec in sections_dict.items():
        sec_d = sec if isinstance(sec, dict) else sec.model_dump()
        compiler_deps = sec_d.get("compiler_deps", {})
        if isinstance(compiler_deps, dict):
            cd = SectionCompilerDeps(**compiler_deps)
        else:
            cd = compiler_deps
        sections_out[sid] = SectionBuildData(
            compiler_deps=cd,
            section_mapping=sec_d.get("section_mapping", {}),
            editor_field_visibility=sec_d.get("editor_field_visibility", {}),
            code_generation_config=sec_d.get("code_generation_config", {}),
        )

    return TemplateBuildOutput(
        sections=sections_out,
        enabled_section_ids=enabled,
        section_id_list=section_id_list,
    )


def recompute_metadata_from_tbo(
    tbo: TemplateBuildOutput,
    existing_section_group_unique_ids: Optional[Dict[str, List[str]]] = None,
) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    """
    Recompute section_group_unique_ids and template_unique_section_id_map from TemplateBuildOutput.
    When existing_section_group_unique_ids is provided, classification is preserved from it
    (header/body/footer) so sections keep their group; otherwise section_l0 from section_mapping is used.
    Returns (section_group_unique_ids, template_unique_section_id_map).
    """
    header_ids: List[str] = []
    body_ids: List[str] = []
    footer_ids: List[str] = []

    if existing_section_group_unique_ids:
        header_set = set(existing_section_group_unique_ids.get("header_unique_ids", []))
        body_set = set(existing_section_group_unique_ids.get("body_unique_ids", []))
        footer_set = set(existing_section_group_unique_ids.get("footer_unique_ids", []))
        for sid in tbo.enabled_section_ids:
            if sid in header_set:
                header_ids.append(sid)
            elif sid in footer_set:
                footer_ids.append(sid)
            else:
                body_ids.append(sid)
    else:
        for sid in tbo.enabled_section_ids:
            sec = tbo.sections.get(sid)
            if not sec:
                continue
            mapping = sec.section_mapping if hasattr(sec, "section_mapping") else sec.get("section_mapping", {})
            l0 = mapping.get("section_l0", "") if isinstance(mapping, dict) else ""
            cat = _section_category(l0)
            if cat == "header":
                header_ids.append(sid)
            elif cat == "footer":
                footer_ids.append(sid)
            else:
                body_ids.append(sid)

    section_group_unique_ids = {
        "header_unique_ids": header_ids,
        "body_unique_ids": body_ids,
        "footer_unique_ids": footer_ids,
    }

    template_unique_section_id_map: Dict[str, str] = {}
    for idx, sid in enumerate(tbo.enabled_section_ids):
        bare = sid.rsplit("_", 1)[0]
        key = f"{bare}_{idx}"
        template_unique_section_id_map[key] = sid

    return section_group_unique_ids, template_unique_section_id_map
