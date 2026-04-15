# nodes/landing_page_builder/template_selection/cache_template_recommendations.py
"""
Cache Template Recommendations Node - Save template/section recommendations to cache.

This node saves resolved_template_recommendations to MongoDB (cache_key_input:
website_intention + trades, cache_key_output: resolved_template_recommendations).
Only saves if section_cache_hit=False (to avoid re-saving cached data).

Note: Saving always happens regardless of use_template_cache setting.
The use_template_cache parameter only controls cache checking (reading) in
cache_lookup_template_recommendations, not cache saving (writing).
"""

import time
from typing import Dict, Any, Optional, List, Tuple

from langgraph.types import RunnableConfig
from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.nodes.landing_page_builder.template_selection.node_utils import (
    extract_trades_from_state,
    generate_section_cache_key,
    save_template_recommendations_cache,
)

logger = get_logger(__name__)


# --- Helpers ---


def _get_resolved_recommendations_to_cache(state: LandingPageWorkflowState) -> Optional[List]:
    """Return list to cache if section_cache_hit=False and we have a non-empty list; else None. Logs skip reasons."""
    section_cache_hit = state.template.section_cache_hit if state.template else False
    if section_cache_hit:
        logger.debug(
            "Skipping cache save - data came from cache",
            node="cache_template_recommendations"
        )
        return None

    resolved = getattr(state, "resolved_template_recommendations", None)
    if not resolved or not isinstance(resolved, list):
        logger.warning(
            "No resolved_template_recommendations to cache - skipping save",
            node="cache_template_recommendations"
        )
        return None

    if len(resolved) == 0:
        logger.debug(
            "Empty resolved_template_recommendations - skipping cache save",
            node="cache_template_recommendations"
        )
        return None

    return resolved


def _get_cache_key_inputs(state: LandingPageWorkflowState) -> Optional[Tuple[str, List, str]]:
    """Return (cache_key, trades, website_intention) or None if trades/website_intention missing. Logs warnings."""
    business_id = state.input.business_id if state.input else None
    trades = extract_trades_from_state(state, business_id)
    website_intention = state.input.website_context.website_intention if state.input else None

    if not trades:
        logger.warning(
            "No trades found - cannot generate cache key, skipping save",
            node="cache_template_recommendations"
        )
        return None

    if not website_intention:
        logger.warning(
            "No website_intention found - cannot generate cache key, skipping save",
            node="cache_template_recommendations"
        )
        return None

    cache_key = generate_section_cache_key(website_intention, trades)
    return (cache_key, trades, website_intention)


# --- Main node ---


@NodeRegistry.register(
    name="cache_template_recommendations",
    description="Save template recommendations to cache for future use",
    max_retries=1,
    timeout=10,
    tags=["smb", "cache", "optimization"],
    display_name="Caching template recommendations",
    show_node=True,
    show_output=False,
)
def cache_template_recommendations_node(
    state: LandingPageWorkflowState,
    config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """
    Save template recommendations to cache (cache_key_input + cache_key_output shape).

    Logic:
    1. Only save if section_cache_hit=False (avoid re-saving cached data)
    2. Extract trades and website_intention
    3. Generate cache key
    4. Save to MongoDB via save_template_recommendations_cache

    Args:
        state: LandingPageWorkflowState
        config: Node configuration
            - save_database_name: Database name (default: 'template_generation')

    Returns:
        Dict with section_cache_saved, section_cache_key (state fields unchanged)
    """
    start_time = time.time()
    config = config or {}

    resolved_template_recommendations = _get_resolved_recommendations_to_cache(state)
    if resolved_template_recommendations is None:
        return {}

    key_inputs = _get_cache_key_inputs(state)
    if key_inputs is None:
        return {}

    cache_key, trades, website_intention = key_inputs

    try:
        success = save_template_recommendations_cache(
            cache_key=cache_key,
            resolved_template_recommendations=resolved_template_recommendations,
            trades=trades,
            website_intention=website_intention,
            config=config
        )
        duration_ms = (time.time() - start_time) * 1000

        if success:
            logger.info(
                "Saved template recommendations to cache",
                node="cache_template_recommendations",
                cache_key=cache_key,
                recommendations_count=len(resolved_template_recommendations),
                trades_count=len(trades),
                duration_ms=round(duration_ms, 2)
            )
            return {
                "section_cache_saved": True,
                "section_cache_key": cache_key
            }

        logger.warning(
            "Failed to save template recommendations to cache",
            node="cache_template_recommendations",
            cache_key=cache_key
        )
        return {"section_cache_saved": False}

    except Exception as e:
        logger.error(
            "Error saving template recommendations cache - non-fatal, continuing",
            node="cache_template_recommendations",
            cache_key=cache_key,
            error=str(e)
        )
        return {
            "section_cache_saved": False,
            "section_cache_error": str(e)
        }
