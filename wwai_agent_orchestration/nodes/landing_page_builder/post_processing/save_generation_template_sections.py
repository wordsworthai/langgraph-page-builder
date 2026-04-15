"""
Save Generation Template Sections - Persist template section list for a generation.

For each generation we persist the ordered list of section IDs that form the chosen
landing page template. Sections are classified into header, body, and footer groups
to enable cross-page sharing (e.g. non-homepage pages reuse homepage's header/footer).

Also creates and persists template_unique_section_id_map for stable section ID mapping.
Used by template-json-builder and downstream compilation.
"""

import time
from typing import Dict, Any, List, Optional

from langgraph.types import RunnableConfig
from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.utils.landing_page_builder.template.builder_service import template_builder_service
from wwai_agent_orchestration.utils.landing_page_builder.template.section_utils import extract_section_ids
from wwai_agent_orchestration.utils.landing_page_builder.ui_logs import (
    save_sections_html,
    make_ui_execution_log_entry_from_registry,
)

logger = get_logger(__name__)


@NodeRegistry.register(
    name="save_generation_template_sections",
    description="Save template section list (ordered section IDs) for this generation",
    max_retries=1,
    timeout=10,
    tags=["database", "save", "smb", "puck"]
)
def save_generation_template_sections_node(
    state: Dict[str, Any],
    config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """
    Save template section list for this generation.

    Sections are classified into header/body/footer groups based on section_l0.
    For homepage pages all groups are populated; for non-homepage pages only body
    is populated (header and footer are empty).

    Args:
        state: Must contain:
            - generation_version_id (in config or state)
            - resolved_template_recommendations (list)
            - input.page_type (str, default "homepage")

    Returns:
        Dict with template_unique_section_id_map and ui_execution_log.
    """
    start_time = time.time()

    if hasattr(state, 'model_dump'):
        state = state.model_dump()

    config_dict = config if config is not None else {}

    logger.info(
        "Saving generation template sections from first template",
        node="save_generation_template_sections"
    )

    # ====================================================================
    # STEP 1: VALIDATE REQUIRED FIELDS
    # ====================================================================
    generation_version_id = config_dict.get("configurable", {}).get("thread_id") or state.get("generation_version_id")

    if not generation_version_id:
        raise ValueError("generation_version_id not found in config or state")

    resolved_template_recommendations = state.get('resolved_template_recommendations', [])
    if not resolved_template_recommendations:
        raise ValueError("No resolved_template_recommendations found")

    # ====================================================================
    # STEP 2: EXTRACT PAGE METADATA FROM STATE
    # ====================================================================
    input_data = state.get("input") or {}
    if isinstance(input_data, dict):
        page_type = input_data.get("page_type", "homepage")
    else:
        page_type = getattr(input_data, "page_type", "homepage")

    # ====================================================================
    # STEP 3: EXTRACT FIRST TEMPLATE'S SECTION MAPPINGS
    # ====================================================================
    first_template = resolved_template_recommendations[0]
    section_mappings = first_template.get('section_mappings', [])
    section_ids = extract_section_ids(section_mappings)

    if not section_ids:
        raise ValueError("No section IDs found in template")

    logger.info(
        "Extracted section IDs from template",
        template_id=first_template.get('template_id'),
        template_name=first_template.get('template_name'),
        page_type=page_type,
        section_count=len(section_ids),
    )

    # ====================================================================
    # STEP 4: CREATE OR REUSE MAPPING, CLASSIFY, BUILD DOC, SAVE
    # ====================================================================
    template_unique_section_id_map = template_builder_service.create_and_save_template_sections(
        generation_version_id=generation_version_id,
        section_mappings=section_mappings,
        section_ids=section_ids,
        page_type=page_type,
        existing_map=state.get("template_unique_section_id_map"),
        template_id=first_template.get('template_id'),
        template_name=first_template.get('template_name'),
    )

    # ====================================================================
    # STEP 5: RETURN
    # ====================================================================
    duration_ms = (time.time() - start_time) * 1000

    logger.info(
        "Section IDs extracted and saved",
        generation_version_id=generation_version_id,
        section_count=len(section_ids),
        page_type=page_type,
        duration_ms=round(duration_ms, 2)
    )

    ui_output_html = save_sections_html(section_count=len(section_ids))
    return {
        "template_unique_section_id_map": template_unique_section_id_map,
        "ui_execution_log": [
            make_ui_execution_log_entry_from_registry("save_generation_template_sections", ui_output_html)
        ],
    }
