"""
Fetch Sections By ID Node - Direct section lookup for PresetSectionsLandingPageWorkflow.

Fetches specific sections from the section repo by MongoDB ObjectId, builds
resolved_template_recommendations in the format expected by downstream nodes
(save_template_sections, autopopulation_input_builder).

Used exclusively by PresetSectionsLandingPageWorkflow when section_ids are passed as direct input.
"""

import hashlib
import time
import uuid
from typing import Dict, Any, List, Optional

from bson import ObjectId
from langgraph.types import RunnableConfig

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.core.database import DocumentNotFoundError
from wwai_agent_orchestration.utils.landing_page_builder.ui_logs import (
    loading_sections_html,
    make_ui_execution_log_entry_from_registry,
)
from wwai_agent_orchestration.data.providers.section_catalog_provider import SectionCatalogProvider
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.constants.section_types import HEADER_SECTION_L0_LIST, FOOTER_SECTION_L0_LIST

logger = get_logger(__name__)


def _generate_query_hash_simple(business_name: str, website_intention: str, website_tone: str) -> str:
    """Generate query hash from individual params."""
    hash_input = f"{business_name}_{website_intention}_{website_tone}"
    return hashlib.md5(hash_input.encode()).hexdigest()


def _validate_header_footer_sections(
    sections: List[Dict[str, Any]],
    page_type: str,
) -> None:
    """
    Validate header/footer section presence based on page_type.

    - Homepage: Must include at least one header section and one footer section.
    - Non-homepage: Must NOT include any header or footer sections (inherited from parent).

    Raises:
        ValueError: If validation fails.
    """
    header_l0_set = set(HEADER_SECTION_L0_LIST)
    footer_l0_set = set(FOOTER_SECTION_L0_LIST)
    disallowed_l0 = header_l0_set | footer_l0_set

    section_l0_values = [s.get("section_l0", "") for s in sections]

    if page_type == "homepage":
        has_header = any(l0 in header_l0_set for l0 in section_l0_values)
        has_footer = any(l0 in footer_l0_set for l0 in section_l0_values)
        if not has_header:
            raise ValueError(
                f"Homepage (page_type='{page_type}') must include at least one header section. "
                f"Header section_l0 values: {HEADER_SECTION_L0_LIST}. "
                f"Found section_l0 values: {list(set(section_l0_values))}."
            )
        if not has_footer:
            raise ValueError(
                f"Homepage (page_type='{page_type}') must include at least one footer section. "
                f"Footer section_l0 values: {FOOTER_SECTION_L0_LIST}. "
                f"Found section_l0 values: {list(set(section_l0_values))}."
            )
    else:
        for section in sections:
            l0 = section.get("section_l0", "")
            if l0 in disallowed_l0:
                raise ValueError(
                    f"Non-homepage page (page_type='{page_type}') must not include "
                    f"header/footer sections. Found section_l0='{l0}' in section "
                    f"{section.get('_id')}. Header/footer are inherited from the "
                    f"parent (homepage) generation."
                )


@NodeRegistry.register(
    name="fetch_sections_by_id",
    description="Fetch sections from repo by ID and build resolved_template_recommendations",
    max_retries=1,
    timeout=30,
    tags=["routing", "preset_sections", "bypass"],
    display_name="Loading selected sections",
    show_node=True,
    show_output=False,
)
def fetch_sections_by_id_node(
    state: LandingPageWorkflowState,
    config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """
    Fetch specific sections from section repo by ID and build workflow state.

    Reads section_ids from execution_config.routing.section_ids (populated by PresetSectionsLandingPageWorkflow).
    Returns templates and resolved_template_recommendations in the format expected
    by save_template_sections and autopopulation_input_builder.

    Args:
        state: LandingPageWorkflowState with execution_config.routing.section_ids and input
        config: Node configuration

    Returns:
        State updates: templates, resolved_template_recommendations, query_hash, etc.

    Raises:
        ValueError: If section_ids missing or no sections found
    """
    start_time = time.time()

    exec_config = state.execution_config
    if not exec_config:
        raise ValueError(
            "fetch_sections_by_id requires execution_config with section_ids"
        )
    if hasattr(exec_config, "routing"):
        section_ids = exec_config.routing.section_ids
    elif isinstance(exec_config, dict):
        routing = exec_config.get("routing") or {}
        section_ids = routing.get("section_ids") if isinstance(routing, dict) else None
    else:
        section_ids = None
    if not section_ids:
        raise ValueError(
            "fetch_sections_by_id requires execution_config.routing.section_ids (non-empty list)"
        )

    inp = state.input
    business_name = inp.business_name if inp else ""
    website_intention = inp.website_context.website_intention if inp and inp.website_context else "generate_leads"
    website_tone = inp.website_context.website_tone if inp and inp.website_context else "professional"

    logger.info(
        "Fetching sections by ID",
        node="fetch_sections_by_id",
        section_count=len(section_ids),
        business_name=business_name,
    )

    section_catalog = SectionCatalogProvider()

    try:
        # Fetch one section at a time to preserve input order (MongoDB $in does not guarantee order)
        sections = []
        for sid in section_ids:
            try:
                doc_list = section_catalog.fetch_sections_with_metadata(
                    query_filter={"_id": ObjectId(sid)}
                )
                if not doc_list:
                    raise ValueError(f"No section found for _id={sid}")
                sections.append(doc_list[0])
            except DocumentNotFoundError as e:
                raise ValueError(f"No section found for _id={sid}") from e

        logger.info(
            "Successfully fetched sections",
            node="fetch_sections_by_id",
            fetched=len(sections),
            requested=len(section_ids),
        )

        # Validate header/footer presence: homepage must have both; non-homepage must have neither
        page_type = getattr(inp, "page_type", "homepage") if inp else "homepage"
        _validate_header_footer_sections(sections, page_type)

        query_hash = _generate_query_hash_simple(business_name, website_intention, website_tone)
        template_id = str(uuid.uuid4())

        template = {
            "template_id": template_id,
            "template_name": "Custom Section Selection",
            "section_info": [
                {
                    "section_index": idx,
                    "section_l0": section.get("section_l0"),
                    "section_l1": section.get("section_l1"),
                    "reasoning": "User selected section",
                }
                for idx, section in enumerate(sections, 1)
            ],
            "business_name": business_name,
            "query_hash": query_hash,
        }

        section_mapped = {
            "template_id": template_id,
            "template_name": "Custom Section Selection",
            "section_mappings": [
                {
                    "section_index": idx,
                    "section_id": str(section["_id"]),
                    "section_l0": section.get("section_l0"),
                    "section_l1": section.get("section_l1"),
                    "desktop_screenshot": section.get("desktop_image_url"),
                    "mobile_screenshot": section.get("mobile_image_url"),
                }
                for idx, section in enumerate(sections, 1)
            ],
            "sections_mapped": len(sections),
        }

        resolved_template_recommendations = [section_mapped]
        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            "Fetch sections by ID complete",
            node="fetch_sections_by_id",
            template_id=template_id,
            sections_count=len(sections),
            duration_ms=round(duration_ms, 2),
        )

        ui_output_html = loading_sections_html(
            section_mappings=section_mapped["section_mappings"]
        )
        return {
            "templates": [template],
            "template_count": 1,
            "resolved_template_recommendations": resolved_template_recommendations,
            "recommendation_count": len(resolved_template_recommendations),
            "query_hash": query_hash,
            "model_used": "preset_sections",
            "ui_execution_log": [
                make_ui_execution_log_entry_from_registry("fetch_sections_by_id", ui_output_html)
            ],
        }

    except DocumentNotFoundError as e:
        raise ValueError(f"No sections found for IDs: {section_ids}") from e
    except ValueError:
        raise
    except Exception as e:
        logger.error(
            "Failed to fetch sections by ID",
            node="fetch_sections_by_id",
            error=str(e),
        )
        raise ValueError(f"Failed to fetch sections: {str(e)}") from e
