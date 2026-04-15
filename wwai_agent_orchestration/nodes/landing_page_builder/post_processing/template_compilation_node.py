# nodes/smb/template_compilation_node.py

"""
Template Compilation Node - Compile template JSON from section IDs.

This node:
1. Extracts page metadata page_type from state.
2. Delegates to compile_template_from_section_ids which is fully DB-driven:
   reads section_ids + map from generation_template_sections, builds template JSON,
   and saves compiled output to generated_templates_with_values
3. Stores compilation results in state.

For regenerate_section flow: merges parent template_json with newly generated
section in memory instead of reading from patched autopopulation_snapshots.

This node ALWAYS RUNS after autopopulation completes (before HTML compilation).
"""

import time
from typing import Dict, Any, List, Optional, Tuple
from langgraph.types import RunnableConfig

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState, PostProcessResult
from wwai_agent_orchestration.utils.landing_page_builder.template.builder_service import template_builder_service
from wwai_agent_orchestration.utils.landing_page_builder.template.template_json_sources import (
    get_template_json_from_generated_templates,
    get_template_json_from_autopopulation_snapshots,
)
from wwai_agent_orchestration.utils.landing_page_builder.template.template_json_merge import (
    merge_parent_and_new_section_template_json,
)
from wwai_agent_orchestration.utils.landing_page_builder.ui_logs import (
    compilation_html,
    make_ui_execution_log_entry_from_registry,
)

logger = get_logger(__name__)


def _get_populated_template_json_override(
    generation_version_id: str,
    workflow_name: str,
    workflow_params: Dict[str, Any],
) -> Optional[Tuple[Dict[str, Any], List]]:
    """
    Compute populated_template_json_override for compile_template_from_section_ids.

    When workflow_name is regenerate_section: merge parent + new section in memory.
    Otherwise: read from snapshot via get_template_json_for_population.

    Returns None when use_real_population is False (ipsum lorem).
    """
    if workflow_name == "template_selection":
        # Don't override, we will use ipsum lorem.
        return None
    
    if workflow_name in ["landing_page_builder", "partial_autopop", "preset_sections"]:
        # Read the template json from agents snapshot.
        return get_template_json_from_autopopulation_snapshots(generation_version_id)

    if workflow_name == "regenerate_section":
        parent_thread_id = workflow_params.get("source_thread_id")
        section_index = workflow_params.get("section_index")
        if not parent_thread_id or section_index is None or section_index < 0:
            raise ValueError("source_thread_id and section_index (>= 0) are required for regenerate_section")

        # Get the section template json from the current thread.
        section_template_json, section_index_mapping = get_template_json_from_autopopulation_snapshots(
            generation_version_id
        )
        # Get the source template json from database, since the user might have updated it.
        source_template_json, source_index_mapping = get_template_json_from_generated_templates(parent_thread_id)

        if section_template_json is None or source_template_json is None:
            raise ValueError("section_template_json or source_template_json is None")
        
        merged_template_json, merged_index_mapping = merge_parent_and_new_section_template_json(
            source_template_json=source_template_json,
            source_mapping=source_index_mapping,
            new_template_json=section_template_json,
            new_mapping=section_index_mapping,
            target_index=section_index,
        )
        return (merged_template_json, merged_index_mapping)
    
    raise ValueError(f"Unsupported workflow name: {workflow_name}")

@NodeRegistry.register(
    name="template_compilation",
    description="Compile template JSON from section IDs using stable mapping",
    max_retries=1,
    timeout=120,  # 2 minutes
    tags=["template", "compilation", "smb"],
    display_name="Compiling template",
    show_node=True,
    show_output=False,
)
async def template_compilation_node(
    state: LandingPageWorkflowState,
    config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """
    LangGraph node to compile template JSON from section IDs.

    Compilation is fully DB-driven: compile_template_from_section_ids reads
    section_ids and template_unique_section_id_map from the
    generation_template_sections collection, handles multi-page header/footer
    merging for non-homepage pages, and saves the compiled output to
    generated_templates_with_values.

    Args:
        state: Must contain:
            - generation_version_id in state.input
            - input.page_type (default "homepage")
        config: Optional configuration

    Returns:
        State updates with template_compilation_results.
    """
    start_time = time.time()

    generation_version_id = state.input.generation_version_id if state.input else None
    if not generation_version_id:
        raise ValueError("generation_version_id not found in state")

    config_dict = config or {}
    configurable = config_dict.get("configurable", {}) if isinstance(config_dict, dict) else {}
    workflow_name = configurable.get("workflow_name", None)
    if not workflow_name:
        raise ValueError("workflow_name not found in config")
    workflow_params = configurable.get("workflow_params") or {}

    populated_override = _get_populated_template_json_override(
        generation_version_id=generation_version_id,
        workflow_name=workflow_name,
        workflow_params=workflow_params,
    )

    try:
        result = await template_builder_service.compile_template_from_section_ids(
            generation_version_id=generation_version_id,
            populated_template_json_override=populated_override,
        )
        template_builder_service.save_template_build_output(
            generation_version_id=generation_version_id,
            template_build_output=result.template_build_output
        )

        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            "Template compilation completed",
            generation_version_id=generation_version_id,
            sections_count=len(result.template_build_output.sections),
            duration_ms=round(duration_ms, 2),
            node="template_compilation",
        )

        ui_output_html = compilation_html()
        return {
            "post_process": PostProcessResult(
                template_compilation_results={
                    "status": "success",
                    "generation_version_id": generation_version_id,
                    "compiled_at": time.time()
                }
            ),
            "ui_execution_log": [
                make_ui_execution_log_entry_from_registry("template_compilation", ui_output_html)
            ],
        }

    except Exception as e:
        logger.error(
            "Template compilation failed",
            error=str(e),
            generation_version_id=generation_version_id,
            node="template_compilation",
        )
        raise