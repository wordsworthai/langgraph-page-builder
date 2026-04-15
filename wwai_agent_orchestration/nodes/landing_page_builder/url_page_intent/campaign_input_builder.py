# nodes/landing_page_builder/url_page_intent/campaign_input_builder.py

"""
Campaign input builder node - combines query and/or page_context (from page_context_extractor).
Builds campaign_intent from data.page_context (merged Gemini/ScrapingBee/screenshot output).
"""

import time
from typing import Dict, Any, Optional

from langgraph.types import RunnableConfig

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import CampaignIntent

logger = get_logger(__name__)


def _get_page_context(state: Dict[str, Any]) -> str:
    """Resolve page_context from state.data or top-level."""
    data = state.get("data") or {}
    if isinstance(data, dict):
        return data.get("page_context") or ""
    return getattr(data, "page_context", None) or ""


@NodeRegistry.register(
    name="campaign_input_builder",
    description="Build campaign_intent from query and/or page_context (from page_context_extractor)",
    max_retries=0,  # Pure function, no retry needed
    tags=["transform"],
)
def campaign_input_builder_node(state: Dict[str, Any], config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """
    Build campaign_intent from available state.

    Uses page_context (from page_context_extractor) or query. Combines both when present.

    Args:
        state: Contains:
            - 'query': User query text (optional)
            - 'page_url': Page URL (optional), from input.generic_context
            - 'data.page_context': Merged page context from page_context_extractor (optional)
        config: Not used

    Returns:
        State updates with data.campaign_intent and data.input_type
    """
    start_time = time.time()

    if hasattr(state, "model_dump"):
        state = state.model_dump()

    inp_gc = (state.get("input") or {}).get("generic_context") or {}
    query = (
        state.get("query")
        or (inp_gc.get("query") if isinstance(inp_gc, dict) else getattr(inp_gc, "query", None))
    )
    page_url = (
        state.get("page_url")
        or (inp_gc.get("page_url") if isinstance(inp_gc, dict) else getattr(inp_gc, "page_url", None))
    )
    page_context = _get_page_context(state)

    has_query = bool(query and str(query).strip())
    has_page_context = bool(page_context and str(page_context).strip())

    logger.info(
        "Building campaign input",
        node="campaign_input_builder",
        has_query=has_query,
        has_page_context=has_page_context,
    )

    # ========================================================================
    # DETERMINE INPUT TYPE AND BUILD CAMPAIGN_INTENT
    # Uses page_context (from page_context_extractor) or query
    # ========================================================================

    # Case 1: Query only (no page context)
    if has_query and not page_context:
        input_type = "query_only"
        campaign_intent = {"campaign_query": str(query).strip()}
        logger.info("Input type: Query only")

    # Case 2: page_context only (from page_context_extractor)
    elif has_page_context and not has_query:
        input_type = "page_context_only"
        campaign_intent = {"campaign_query": page_context.strip(), "page_url": page_url}
        logger.info("Input type: page_context only")

    # Case 3: Query + page_context
    elif has_query and has_page_context:
        input_type = "query_and_page_context"
        combined = f"User Query: {str(query).strip()}\n\nPage Context:\n{page_context.strip()}"
        campaign_intent = {"campaign_query": combined, "page_url": page_url}
        logger.info("Input type: Query + page_context")

    # Case 4: Error - no input
    else:
        raise ValueError(
            "Must have at least one of: query or page_context. "
            f"Got: has_query={has_query}, has_page_context={has_page_context}"
        )
    
    duration_ms = (time.time() - start_time) * 1000

    logger.info(
        "Campaign input built",
        node="campaign_input_builder",
        input_type=input_type,
        campaign_query_length=len(campaign_intent["campaign_query"]),
        duration_ms=round(duration_ms, 2),
    )

    return {
        "data": {
            "campaign_intent": CampaignIntent(campaign_query=campaign_intent["campaign_query"]),
            "input_type": input_type,
        },
    }