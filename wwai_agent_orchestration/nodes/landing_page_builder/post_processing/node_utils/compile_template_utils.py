import os

# Validate required environment variables BEFORE importing bundle_pipeline_pkg
# The bundle_pipeline_pkg reads these at import time to configure NODE_SERVER_URL
_missing_env_vars = []
if not os.environ.get('ENVIRONMENT'):
    _missing_env_vars.append('ENVIRONMENT')
if not os.environ.get('NODE_SERVER_URL'):
    _missing_env_vars.append('NODE_SERVER_URL')

if _missing_env_vars:
    raise EnvironmentError(
        f"Missing required environment variables: {', '.join(_missing_env_vars)}. "
        f"Please set these in your .env file or environment:\n"
        f"  ENVIRONMENT=local\n"
        f"  NODE_SERVER_URL=http://localhost:3002"
    )

from typing import Dict, Any, Tuple

from bundle_pipeline_pkg.wwai_dataclasses.bundle_pipeline import SectionCompilationDependencies
from bundle_pipeline_pkg.wwai_dataclasses.shopify import Section, TemplateConfig
from bundle_pipeline_pkg.shopify_template_compilation.compilation_utils.compiler import compile_template_with_dependencies
from bundle_pipeline_pkg.shopify_template_compilation.compilation_utils import html_generation_utils

# CRITICAL: The bundle_pipeline_pkg caches NODE_SERVER_URL at import time.
# If the settings were loaded before our env vars were set, NODE_SERVER_URL will be None.
# We need to directly override the cached constant in the renderer module.
from bundle_pipeline_pkg.node_service_utils import renderer as _bp_renderer
if _bp_renderer.NODE_SERVER_URL is None:
    import bundle_pipeline_pkg.lib.constants.bundle_pipeline as _bp_constants
    _bp_constants.NODE_SERVER_URL = os.environ.get('NODE_SERVER_URL')
    _bp_renderer.NODE_SERVER_URL = _bp_constants.NODE_SERVER_URL


def template_build_output_to_compilation_inputs(
    output: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Convert TemplateBuildOutput (dict form) to (section_compiler_dependencies,
    template_file_and_assets_output) for compile_section_with_dependencies.
    """
    sections = output.get("sections", {})
    section_compiler_dependencies = {
        sid: s["compiler_deps"] for sid, s in sections.items()
    }
    template_file_and_assets_output = {
        "section_id_to_section_mapping": {
            sid: s["section_mapping"] for sid, s in sections.items()
        },
        "enabled_section_ids": output.get("enabled_section_ids", []),
    }
    return section_compiler_dependencies, template_file_and_assets_output


def compile_section_with_dependencies(
    template_file_and_assets_output,
    section_compiler_dependencies,
    template_debug_folder,
    compiled_template_filename,
    tailwind_css_url = "https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"
):
    # Parse dependencies and sections into Pydantic models
    parsed_deps = {
        k: SectionCompilationDependencies.model_validate(v)
        for k, v in section_compiler_dependencies.items()
    }
    parsed_sections = {
        k: Section.model_validate(v)
        for k, v in template_file_and_assets_output.get("section_id_to_section_mapping", {}).items()
    }

    for section_id, deps in parsed_deps.items():
        assert deps.css_js_assets_path is not None, f"CSS/JS assets path is None for section {section_id}"
        assert deps.css_js_assets_path.strip() != "", f"CSS/JS assets path is empty for section {section_id}"

    # Compile with prepared dependencies
    log_message = lambda msg: print(msg)
    _, _, _, all_section_htmls, _ = compile_template_with_dependencies(
        section_dependencies=parsed_deps,
        section_id_to_section_mapping=parsed_sections,
        template_debug_folder=None,
        enabled_section_ids=None,
        sections_to_skip=None,
        log_message=log_message,
    )

    # Build a minimal TemplateConfig for full HTML generation
    template_config = TemplateConfig(
        dev="",
        page_url="shop.zive.club",
        template_filepath=f"page.{compiled_template_filename}.json",
        has_video_section=False,
    )

    # Generate full HTML
    full_template_html, full_template_output_path = html_generation_utils.generate_full_html(
        all_section_htmls,
        template_config,
        template_debug_folder=template_debug_folder,
        log_message=log_message,
        tailwind_css_url=tailwind_css_url,
    )

    return full_template_html, full_template_output_path
