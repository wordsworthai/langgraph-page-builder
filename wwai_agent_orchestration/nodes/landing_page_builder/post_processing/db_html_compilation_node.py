# nodes/smb/db_html_compilation_node.py

"""
DB-driven HTML Compilation Node - reads from generated_templates_with_values DB.

1. Reads compiled template data from generated_templates_with_values (saved by
   template_compilation_node). Template compilation runs first and persists
   the template versions; this node does not build or save.
2. For non-homepage pages, merges parent header/footer from DB automatically
3. Compiles sections into HTML and uploads to S3

Rationale: In production, this node may not return (timeout/async). The template
version value is persisted by template_compilation_node, which always runs and returns.
"""

import os
import tempfile
import shutil
from typing import Dict, Any, Optional, Tuple
from langgraph.types import RunnableConfig

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.core.observability.logger import get_logger

from template_json_builder.utils.s3_upload import get_s3_client, upload_file_to_s3
from wwai_agent_orchestration.nodes.landing_page_builder.post_processing.node_utils.compile_template_utils import (
    compile_section_with_dependencies,
    template_build_output_to_compilation_inputs,
)
from wwai_agent_orchestration.utils.landing_page_builder.template.db_service import template_db_service
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import PostProcessResult

logger = get_logger(__name__)


def _extract_node_context(
    state: Dict[str, Any], 
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """Parse generation_version_id, page_type, parent_gvid, and config from state/config."""
    config = config or {}
    generation_version_id = (
        config.get("configurable", {}).get("thread_id")
        or (state.input.generation_version_id if state.input else None)
    )
    if not generation_version_id:
        raise ValueError("generation_version_id not found in config or state.input")

    workflow_name = config.get("configurable", {}).get("workflow_name")
    if not workflow_name:
        raise ValueError("workflow_name not found in config")

    page_type = getattr(state.input, "page_type", "homepage") if state.input else "homepage"
    
    parent_generation_version_id = None
    # For curated page, first generation, we expect parent generation id to be passed in 
    # config.
    if page_type != "homepage" and workflow_name == "preset_sections":
        parent_generation_version_id = config.get("configurable", {}).get("parent_generation_version_id")
        if not parent_generation_version_id:
            raise ValueError("parent_generation_version_id not found in config for non homepage page")

    return {
        "generation_version_id": generation_version_id,
        "page_type": page_type,
        "parent_generation_version_id": parent_generation_version_id,
    }


def _get_compilation_inputs_from_db(
    generation_version_id: str, 
    page_type: str, 
    parent_generation_version_id: Optional[str]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Read template_build_output from DB, convert to (deps, tfa) for HTML compilation."""
    tbo = template_db_service.get_template_build_output(
        generation_version_id=generation_version_id,
        page_type=page_type,
        parent_generation_version_id=parent_generation_version_id,
    )
    return template_build_output_to_compilation_inputs(tbo)


def _compile_html_and_upload_to_s3(
    generation_version_id: str,
    section_compiler_dependencies: Dict[str, Any],
    template_file_and_assets_output: Dict[str, Any],
) -> str:
    """Call compile_section_with_dependencies. Returns output path."""

    temp_dir = tempfile.mkdtemp(prefix=f"db_html_compilation_{generation_version_id}_")

    _, full_template_output_path = compile_section_with_dependencies(
        template_file_and_assets_output,
        section_compiler_dependencies,
        temp_dir,
        "template_debug.html",
        tailwind_css_url="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4",
    )

    s3_client, s3_client_err = get_s3_client()
    if s3_client is None:
        raise RuntimeError(f"Failed to create S3 client: {s3_client_err}")

    html_upload_status = upload_file_to_s3(
        client=s3_client,
        local_filename=full_template_output_path,
        s3_file_dir=f"ai_pages/{generation_version_id}",
        filename_prefix="compiled_template",
        bucket_name=os.environ.get("S3_BUCKET_NAME", ""),
        bucket_location=os.environ.get("S3_BUCKET_REGION", ""),
        overwrite=True,
        content_type="text/html",
    )

    if not html_upload_status.status:
        raise RuntimeError(f"Failed to upload HTML to S3: {html_upload_status.message}")
    
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    return html_upload_status.response.get("s3_url")


@NodeRegistry.register(
    name="db_html_compilation",
    description="DB-driven HTML compilation - reads from generated_templates_with_values",
    max_retries=1,
    timeout=120,
    tags=["html", "compilation", "smb", "db_driven"],
    display_name="Compiling HTML (DB)",
    show_node=True,
    show_output=False,
)
def db_html_compilation_node(
    state: Dict[str, Any],
    config: Optional[RunnableConfig] = None,
) -> Dict[str, Any]:
    """
    DB-driven HTML compilation node.

    Reads compiled template from generated_templates_with_values (saved by
    template_compilation_node). Does not build or save template versions.

    Args:
        state: Must contain:
            - generation_version_id in state.input
            - input.page_type (default "homepage")
            - input.parent_generation_version_id (for non-homepage)
        config: Optional configuration

    Returns:
        State updates with html_compilation_results.
    """
    config = config or {}
    ctx = _extract_node_context(state, config)

    logger.info(
        "[db_html_compilation] START",
        generation_version_id=ctx["generation_version_id"],
        page_type=ctx["page_type"],
    )

    try:
        deps, tfa = _get_compilation_inputs_from_db(
            ctx["generation_version_id"], 
            ctx["page_type"], 
            ctx["parent_generation_version_id"]
        )

        html_s3_url = _compile_html_and_upload_to_s3(
            ctx["generation_version_id"], 
            deps, 
            tfa
        )

        logger.info(
            "[db_html_compilation] COMPLETE",
            generation_version_id=ctx["generation_version_id"],
            html_s3_url=html_s3_url,
        )

        return {
            "post_process": PostProcessResult(
                html_compilation_results={
                    "compiled_html_s3_url": html_s3_url,
                }
            ),
        }

    except Exception as e:
        logger.error(
            "[db_html_compilation] FAILED",
            error=str(e),
            generation_version_id=ctx["generation_version_id"],
            node="db_html_compilation",
        )
        raise