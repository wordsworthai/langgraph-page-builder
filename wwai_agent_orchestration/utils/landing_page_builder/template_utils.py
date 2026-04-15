"""
Thin wrapper for template compilation. Provides compile-only, read-from-DB, save-updates,
curated/template options helpers, and sections-for-replacement (categories + sections).
"""
import os
import re
import shutil
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple

from template_json_builder.models.template_build_output import TemplateBuildOutput

from wwai_agent_orchestration.contracts.landing_page_builder.page_structure import TemplateWithPageInfo
from wwai_agent_orchestration.contracts.landing_page_builder.curated_options import (
    CuratedPagesResponse,
    TemplateOptionsResponse,
)
from wwai_agent_orchestration.contracts.landing_page_builder.section_options import (
    CategoryResponse,
    SectionMetadataResponse,
)
from wwai_agent_orchestration.contracts.landing_page_builder.template_update import SaveTemplateRequest
from wwai_agent_orchestration.utils.landing_page_builder.template import cache_options
from wwai_agent_orchestration.utils.landing_page_builder.template import curated_options
from wwai_agent_orchestration.utils.landing_page_builder.template import replacement_sections
from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.utils.landing_page_builder.template.builder_service import template_builder_service
from wwai_agent_orchestration.utils.landing_page_builder.template.db_service import template_db_service

logger = get_logger(__name__)


def _asset_to_str(asset: Any) -> str:
    """Extract liquid content string from an asset (dict or object with value attr)."""
    if isinstance(asset, dict):
        return asset.get("value", "") or ""
    return getattr(asset, "value", "") or ""


async def _upload_edited_assets_and_get_path(
    edited_section_mapping: Dict,
    unique_id: str,
) -> Optional[str]:
    """
    Upload edited css_files and js_files from edited_section_mapping to S3.
    Returns new css_js_assets_path or None on failure (caller keeps original).
    """
    from template_json_builder.models.schema_and_code.shopify_section import Section
    from template_json_builder.utils.upload_css_js_assets import batch_upload_section_files_with_checksum
    from template_json_builder.utils.s3_upload import generate_s3_url

    content = edited_section_mapping.get("content") or {}
    css_files_raw = content.get("css_files") or {}
    js_files_raw = content.get("js_files") or {}
    if not css_files_raw and not js_files_raw:
        return None

    # Ensure keys have .css/.js extension so S3 path matches Liquid asset_url (e.g. contact-card-form.js)
    # Liquid requests contact-card-form.js but keys may be contact-card-form
    def _ensure_ext(d: dict, ext: str) -> dict:
        return {
            (k if k.lower().endswith(ext) else f"{k}{ext}"): v
            for k, v in d.items()
        }
    css_files = _ensure_ext(css_files_raw, ".css")
    js_files = _ensure_ext(js_files_raw, ".js")
    modified_content = {**content, "css_files": css_files, "js_files": js_files}
    modified_mapping = {**edited_section_mapping, "content": modified_content}

    try:
        section = Section.model_validate(modified_mapping)
    except Exception as e:
        logger.warning(
            "compile_section_to_html: could not validate edited_section_mapping for asset upload",
            error=str(e),
        )
        return None

    sections = {unique_id: section}
    s3_dir = "boilerplate_files"
    bucket_name = os.environ.get("S3_BUCKET_NAME", "")
    bucket_location = os.environ.get("S3_BUCKET_REGION", "")

    upload_response = await batch_upload_section_files_with_checksum(
        sections=sections,
        s3_dir=s3_dir,
        db=None,
        overwrite=True,
        bucket_name=bucket_name,
        bucket_location=bucket_location,
    )

    if not upload_response.status:
        logger.warning(
            "compile_section_to_html: edited CSS/JS upload failed, preview may show stale assets. "
            "If you see 'No .env file found', ensure .env exists with AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.",
            upload_error=upload_response.message,
        )
        return None

    return generate_s3_url(s3_dir, bucket_name, bucket_location)


def _merge_snippets_for_compiler(
    original_snippets: dict,
    edited_snippets: dict,
) -> Dict[str, str]:
    """
    Merge original compiler snippets with edited ones.
    Original may include snippets the section template needs (e.g. main_local-font) that
    don't appear in the editor. Edited adds/overrides from the code editor (e.g. main_link).
    """
    original_str = {
        k: (v if isinstance(v, str) else _asset_to_str(v))
        for k, v in (original_snippets or {}).items()
    }
    edited_str = {name: _asset_to_str(asset) for name, asset in (edited_snippets or {}).items()}
    return {**original_str, **edited_str}


def _apply_edited_section_mapping(
    section_build_data: Any,
    edited_section_mapping: Dict,
) -> Any:
    """
    Apply edited_section_mapping to section build data: replace section_mapping and merge
    snippets_for_compiler so both original required snippets and editor changes are included.
    Returns validated SectionBuildData.
    """
    from template_json_builder.models.template_build_output import SectionBuildData

    updated = section_build_data.model_dump()
    updated["section_mapping"] = edited_section_mapping

    compiler_deps = updated.get("compiler_deps") or {}
    if not isinstance(compiler_deps, dict):
        compiler_deps = compiler_deps.model_dump() if hasattr(compiler_deps, "model_dump") else {}
    else:
        compiler_deps = dict(compiler_deps)

    original_snippets = compiler_deps.get("snippets_for_compiler") or {}
    if not isinstance(original_snippets, dict):
        original_snippets = original_snippets.model_dump() if hasattr(original_snippets, "model_dump") else {}

    edited_snippets = (edited_section_mapping.get("content") or {}).get("snippets") or {}
    compiler_deps["snippets_for_compiler"] = _merge_snippets_for_compiler(
        original_snippets, edited_snippets
    )
    updated["compiler_deps"] = compiler_deps

    return SectionBuildData.model_validate(updated)


def build_minimal_template_for_section_ops(
    resolved_template_recommendations: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build minimal template dict (template_id, template_name) for section operations.
    Used by get_resolved_and_map_from_db when building resolved from DB.
    """
    if not resolved_template_recommendations:
        return {}
    first = resolved_template_recommendations[0]
    return {
        "template_id": first.get("template_id"),
        "template_name": first.get("template_name"),
    }


def get_resolved_and_map_from_db(
    source_thread_id: str,
    first_template: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Read section_mappings and template_unique_section_id_map from DB.
    For regenerate_section: section is already in place (from add_section_in_place);
    no apply_section_modification needed.
    Returns (resolved_template_recommendations, template_unique_section_id_map).
    """
    merged = template_db_service.get_merged_all(source_thread_id)
    section_mappings = list(merged.get("section_mappings", []))
    template_unique_section_id_map = dict(merged.get("template_unique_section_id_map", {}))
    resolved = [{**first_template, "section_mappings": section_mappings}]
    return resolved, template_unique_section_id_map


def get_section_mappings_from_db(source_thread_id: str) -> List[Dict[str, Any]]:
    """
    Fetch section_mappings from generation_template_sections for regenerate_section workflow.

    User may edit sections (e.g. via drag-drop add_section_in_place); always use DB
    as source of truth for the current section list.
    """
    merged = template_db_service.get_merged_all(source_thread_id)
    return list(merged.get("section_mappings", []))


async def compile_and_get_ipsum_lorem_template_for_generation_version_id(
    generation_version_id: str,
    parent_generation_version_id: Optional[str] = None,
) -> TemplateWithPageInfo:
    """
    Compile template from section IDs using ipsum lorem only.
    Returns TemplateWithPageInfo (template + page structure).
    Does NOT save to DB. Use template_compilation_node or save_template_build_output to persist.

    When parent_generation_version_id is provided (non-homepage):
    fetches header/footer section IDs from parent's generation_template_sections,
    merges with current body, compiles with ipsum lorem.
    """
    return await template_builder_service.compile_template_from_section_ids(
        generation_version_id=generation_version_id,
        populated_template_json_override=None,
        parent_generation_version_id=parent_generation_version_id,
    )


def get_template_for_generation_version_id_from_db(
    generation_version_id: str,
    page_type: str = "homepage",
    parent_generation_version_id: Optional[str] = None,
) -> TemplateWithPageInfo:
    """
    Read compiled template from DB and return TemplateWithPageInfo (template + page structure).
    Use when you need up-to-date data (e.g. after someone overwrote the compiled output).
    """
    return template_builder_service.get_template_build_output(
        generation_version_id=generation_version_id,
        page_type=page_type,
        parent_generation_version_id=parent_generation_version_id,
    )


async def compile_section_with_ipsum_lorem(
    section_id: str,
) -> TemplateBuildOutput:
    """
    Compile a single section. Returns TemplateBuildOutput.
    Uses ipsum_lorem by default (no autopopulation).
    """
    return await template_builder_service.compile_section_template(
        section_id=section_id,
    )


async def compile_batch_section_templates_with_ipsum_lorem(
    section_ids: List[str],
) -> TemplateBuildOutput:
    """
    Compile multiple sections in one call. Returns TemplateBuildOutput.
    Uses ipsum_lorem only (no autopopulation).
    """
    return await template_builder_service.compile_batch_section_templates(
        section_ids=section_ids,
    )


async def compile_batch_section_ids_to_html(section_ids: List[str]) -> str:
    """
    Compile multiple section IDs to full HTML. Uses ipsum_lorem only.
    Returns full HTML string for preview (e.g. Curated Page Builder).
    """
    from wwai_agent_orchestration.nodes.landing_page_builder.post_processing.node_utils.compile_template_utils import (
        compile_section_with_dependencies,
        template_build_output_to_compilation_inputs,
    )

    if not section_ids:
        return "<!DOCTYPE html><html><body><p>No sections to compile.</p></body></html>"

    tbo = await compile_batch_section_templates_with_ipsum_lorem(section_ids)
    if not tbo.sections or not tbo.enabled_section_ids:
        raise ValueError("No section data returned for batch compile")

    tbo_dict = tbo.model_dump()
    deps, tfa = template_build_output_to_compilation_inputs(tbo_dict)

    temp_dir = tempfile.mkdtemp(prefix="compile_batch_")
    try:
        full_html, _ = compile_section_with_dependencies(
            template_file_and_assets_output=tfa,
            section_compiler_dependencies=deps,
            template_debug_folder=temp_dir,
            compiled_template_filename="preview.html",
        )
        return full_html
    finally:
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass


async def compile_section_to_html(
    section_id: str,
    edited_section_mapping: Optional[Dict] = None,
) -> str:
    """
    Build TemplateBuildOutput from section_id, optionally overlay edited section_mapping,
    and compile to HTML. Returns the full HTML string.

    Used by the code editor "Compile" button to preview edits without saving.
    """
    from wwai_agent_orchestration.nodes.landing_page_builder.post_processing.node_utils.compile_template_utils import (
        compile_section_with_dependencies,
        template_build_output_to_compilation_inputs,
    )

    tbo = await compile_section_with_ipsum_lorem(section_id)
    if not tbo.sections or not tbo.enabled_section_ids:
        raise ValueError(f"No section data for section_id={section_id}")

    unique_id = tbo.enabled_section_ids[0]
    section_build_data = tbo.sections[unique_id]
    add_cache_buster = False

    if edited_section_mapping is not None:
        content = edited_section_mapping.get("content") or {}
        tbo.sections[unique_id] = _apply_edited_section_mapping(
            section_build_data, edited_section_mapping
        )
        # Upload edited CSS/JS to S3 and update path so preview uses edited assets
        content = edited_section_mapping.get("content") or {}
        css_keys = list((content.get("css_files") or {}).keys())
        js_keys = list((content.get("js_files") or {}).keys())
        has_assets = bool(css_keys or js_keys)
        if has_assets:
            new_path = await _upload_edited_assets_and_get_path(
                edited_section_mapping, unique_id
            )
            if new_path is not None:
                from template_json_builder.models.template_build_output import SectionBuildData

                final_section = tbo.sections[unique_id]
                updated = final_section.model_dump()
                compiler_deps = updated.get("compiler_deps") or {}
                if not isinstance(compiler_deps, dict):
                    compiler_deps = compiler_deps.model_dump() if hasattr(compiler_deps, "model_dump") else {}
                else:
                    compiler_deps = dict(compiler_deps)
                compiler_deps["css_js_assets_path"] = new_path
                updated["compiler_deps"] = compiler_deps
                tbo.sections[unique_id] = SectionBuildData.model_validate(updated)
                add_cache_buster = True

    tbo_dict = tbo.model_dump()
    deps, tfa = template_build_output_to_compilation_inputs(tbo_dict)

    temp_dir = tempfile.mkdtemp(prefix="compile_section_")
    try:
        full_html, _ = compile_section_with_dependencies(
            template_file_and_assets_output=tfa,
            section_compiler_dependencies=deps,
            template_debug_folder=temp_dir,
            compiled_template_filename="preview.html",
        )
        # Add ?v=timestamp to boilerplate_files asset URLs to bust cache (avoids S3 clutter)
        if add_cache_buster:
            ts = int(time.time())
            # Match URLs without existing query params (stop before ?)
            full_html = re.sub(
                r'(https://[^"\'?\s]*boilerplate_files/[^"\'?\s]*\.(?:js|css))(?=["\'\s>])',
                rf'\1?v={ts}',
                full_html,
            )
        return full_html
    finally:
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass


def save_template_updates(
    generation_version_id: str,
    request: SaveTemplateRequest,
) -> None:
    """
    Apply SaveTemplateRequest to the existing document and overwrite in DB.
    Fetches current doc, applies section_updates, section_order, deleted_sections,
    recomputes metadata, and saves back to the same generation_version_id.
    """
    template_builder_service.save_template_updates(
        generation_version_id=generation_version_id,
        request=request,
    )


def get_curated_pages() -> CuratedPagesResponse:
    """Fetch curated pages from section_repo_prod.curated_pages. Returns CuratedPagesResponse."""
    pages = curated_options.get_curated_pages()
    return CuratedPagesResponse(pages=pages)


def get_template_options_for_editor(
    business_id: str,
    current_section_ids: Optional[List[str]] = None,
) -> TemplateOptionsResponse:
    """Fetch template options from template_cache for editor. Returns TemplateOptionsResponse."""
    options = cache_options.get_template_options_from_cache(
        business_id=business_id,
        current_section_ids=current_section_ids,
    )
    return TemplateOptionsResponse(options=options)


def get_categories_for_replacement() -> List[CategoryResponse]:
    """Fetch L0 categories from section repository (SMB filter). Returns List[CategoryResponse]."""
    return replacement_sections.get_categories_for_replacement()


def get_body_sections_for_replacement(
    category_key: Optional[str] = None,
) -> List[SectionMetadataResponse]:
    """Fetch body sections only for replacement. Returns List[SectionMetadataResponse]."""
    return replacement_sections.get_sections_for_replacement(
        category_key=category_key,
        section_type="body",
    )


def get_header_sections_for_replacement(
    category_key: Optional[str] = None,
) -> List[SectionMetadataResponse]:
    """Fetch header sections only for replacement. Returns List[SectionMetadataResponse]."""
    return replacement_sections.get_sections_for_replacement(
        category_key=category_key,
        section_type="header",
    )


def get_footer_sections_for_replacement(
    category_key: Optional[str] = None,
) -> List[SectionMetadataResponse]:
    """Fetch footer sections only for replacement. Returns List[SectionMetadataResponse]."""
    return replacement_sections.get_sections_for_replacement(
        category_key=category_key,
        section_type="footer",
    )
