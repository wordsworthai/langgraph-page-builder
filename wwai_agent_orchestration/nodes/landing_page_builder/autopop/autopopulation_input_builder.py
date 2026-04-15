# nodes/smb/autopop/autopopulation_input_builder.py
"""
Autopopulation Input Builder Node - Builds LangGraph input for autopopulation workflow.

This node supports two modes based on config.configurable.workflow_name:

1. Full autopop (landing_page_builder, partial_autopop, preset_sections):
   - Reads section_ids from state.resolved_template_recommendations
   - Uses full template_unique_section_id_map from state

2. Single-section regenerate (regenerate_section):
   - Reads section_id and section_index from config.configurable.workflow_params
   - Uses filtered template map for the single section (exact key {section_id}_{section_index})

In both cases, calls build_langgraph_input and stores result in state.autopopulation_langgraph_state.

ASYNC NODE: This node is async because it calls async function build_langgraph_input.
LangGraph natively supports async nodes - just define as 'async def' and use 'await'.
"""

import time
from typing import Dict, Any, List, Tuple

from langgraph.types import RunnableConfig
from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.core.database import db_manager
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils import autopop_helpers
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils.autopop_input_utils import (
    get_use_mock_autopopulation,
    get_palette_and_fonts_input,
    get_section_ids_from_resolved_template_recommendations,
)
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from template_json_builder.build_langgraph_input import build_langgraph_input
from wwai_agent_orchestration.utils.landing_page_builder.template.template_json_sources import get_template_json_from_generated_templates

logger = get_logger(__name__)


def _get_section_ids_and_template_map(
    state: LandingPageWorkflowState,
    config: RunnableConfig,
) -> Tuple[List[str], Dict[str, str]]:
    """
    Resolve section_id_list and template_unique_section_id_map based on workflow.

    - regenerate_section: single section from workflow_params, filtered map
    - else: all sections from resolved_template_recommendations, full map
    """
    config = config or {}
    configurable = config.get("configurable", {})
    workflow_name = configurable.get("workflow_name")
    workflow_params = configurable.get("workflow_params") or {}

    if workflow_name == "regenerate_section" and workflow_params.get("section_id"):
        section_id = workflow_params["section_id"]
        section_index = workflow_params.get("section_index", 0)
        full_map = state.template_unique_section_id_map or {}
        exact_key = f"{section_id}_{section_index}"
        template_json_stable_key = full_map.get(exact_key)
        if not template_json_stable_key:
            raise ValueError(
                f"Could not find entry for section_id={section_id} in template_unique_section_id_map. "
                f"Available keys: {list(full_map.keys())}"
            )
        filtered_map = {f"{section_id}_0": template_json_stable_key}
        return ([section_id], filtered_map)

    section_ids = get_section_ids_from_resolved_template_recommendations(state)
    template_map = state.template_unique_section_id_map
    if not template_map:
        raise ValueError(
            "template_unique_section_id_map not found in state. "
            "save_generation_template_sections must run before autopopulation_input_builder."
        )
    return (section_ids, template_map)

def _get_populated_template_json_override(
    source_thread_id: str,
    workflow_name: str
) -> Tuple[Any, Any]:
    """
    Get populated_template_json_override for compile_template_from_section_ids.
    """
    if workflow_name == "partial_autopop":
        # Lets restore with values in db, on top of that, we will merge correct agent output 
        # and get the final response in finalize and template compilation stage.
        generated_template_json, generated_index_mapping = get_template_json_from_generated_templates(source_thread_id)
        if generated_template_json is None:
            raise ValueError("generated_template_json is None")
        if generated_index_mapping is None:
            raise ValueError("generated_index_mapping is None")
        return generated_template_json, generated_index_mapping
    # In every other case, we will pass None and start from ipsum lorem.
    return None

@NodeRegistry.register(
    name="autopopulation_input_builder",
    description="Build autopopulation LangGraph input state from section IDs",
    max_retries=1,
    timeout=60,
    tags=["autopopulation", "langgraph", "builder", "async"],
    display_name="Preparing template data",
    show_node=False,
    show_output=False,
)
async def autopopulation_input_builder_node(
    state: LandingPageWorkflowState,
    config: RunnableConfig = None,
) -> Dict[str, Any]:
    """
    Build AutopopulationLangGraphAgentsState from section IDs.

    Mode is determined by config.configurable.workflow_name:
    - regenerate_section: single section from workflow_params, filtered template map
    - else: all sections from resolved_template_recommendations, full template map

    ASYNC NODE: Uses 'await' to call async build_langgraph_input directly.
    LangGraph natively supports async nodes - no event loop gymnastics needed.

    Args:
        state: LandingPageWorkflowState with resolved_template_recommendations or template_unique_section_id_map
        config: Node configuration (RunnableConfig from LangGraph); workflow_name and workflow_params used for regenerate_section mode

    Returns:
        Dict with autopopulation_langgraph_state

    Raises:
        ValueError: If section_ids are missing or invalid
    """
    start_time = time.time()

    run_id = state.input.generation_version_id if state.input else None
    if not run_id:
        raise ValueError(
            "autopopulation_input_builder requires generation_version_id in state.input"
        )

    section_ids, template_unique_section_id_map = _get_section_ids_and_template_map(
        state, config
    )

    use_mock_autopopulation = get_use_mock_autopopulation(state.execution_config)
    business_name = state.input.business_name if state.input else ""

    logger.info(
        "Building autopopulation LangGraph input",
        node="autopopulation_input_builder",
        section_count=len(section_ids),
        run_id=run_id,
        business_name=business_name,
    )

    mongo_client = db_manager.client
    store = autopop_helpers.get_store()
    palette_and_fonts_input = get_palette_and_fonts_input(state)

    populated_template_json_override = _get_populated_template_json_override(
        config.get("configurable", {}).get("workflow_params", {}).get("source_thread_id"), 
        config.get("configurable", {}).get("workflow_name")
    )
    langgraph_state = await build_langgraph_input(
        section_id_list=section_ids,
        mongo_client=mongo_client,
        store=store,
        run_id=run_id,
        bypass_prompt_cache=False,
        is_dev_mode=False,
        extra_meta={"use_mock": use_mock_autopopulation},
        palette_and_fonts_input=palette_and_fonts_input,
        template_unique_section_id_map=template_unique_section_id_map,
        populated_template_json_override=populated_template_json_override
    )

    duration_ms = (time.time() - start_time) * 1000

    logger.info(
        "Autopopulation LangGraph input built successfully",
        node="autopopulation_input_builder",
        duration_ms=duration_ms,
        run_id=run_id,
    )

    return {
        "autopopulation_langgraph_state": langgraph_state,
    }
