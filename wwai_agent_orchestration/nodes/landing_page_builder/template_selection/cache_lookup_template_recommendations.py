# nodes/landing_page_builder/template_selection/cache_lookup_template_recommendations.py
"""
Cache Lookup Template Recommendations Node - Check cache for template/section recommendations.

Checks if template recommendations exist in cache for (website_intention, trades).
Document shape: cache_key_input (website_intention, trades), cache_key_output
(resolved_template_recommendations). On hit, populates resolved_template_recommendations
and sets section_cache_hit=True to bypass template generation and section retrieval.

When cache hit occurs, all recommendations (typically 3) are returned.
Downstream nodes select the first using resolved_template_recommendations[0].
"""

import time
from typing import Dict, Any, List, Optional

from langgraph.types import RunnableConfig
from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState, TemplateResult
from wwai_agent_orchestration.nodes.landing_page_builder.template_selection.node_utils import (
    extract_trades_from_state,
    generate_section_cache_key,
    get_template_recommendations_by_cache_key,
)
from wwai_agent_orchestration.utils.landing_page_builder.ui_logs import (
    cache_lookup_html,
    make_ui_execution_log_entry_from_registry,
)

logger = get_logger(__name__)


# --- Helpers ---


def _get_use_template_cache(state: LandingPageWorkflowState) -> bool:
    """Read execution_config.cache_strategy.use_template_cache (dict or object); default True."""
    use_template_cache = True
    exec_config = getattr(state, "execution_config", None)
    if exec_config:
        if isinstance(exec_config, dict):
            cache_strategy = exec_config.get("cache_strategy", {})
            use_template_cache = cache_strategy.get("use_template_cache", True)
        else:
            cache_strategy = getattr(exec_config, "cache_strategy", None)
            if cache_strategy:
                use_template_cache = getattr(cache_strategy, "use_template_cache", True)
    return use_template_cache


def _resolved_recommendations_from_cached_doc(cached_data: Optional[Dict[str, Any]]) -> Optional[List]:
    """Return cache_key_output.resolved_template_recommendations if a non-empty list; else None."""
    if not cached_data or not isinstance(cached_data, dict):
        return None
    output = cached_data.get("cache_key_output") or {}
    recs = output.get("resolved_template_recommendations")
    if recs and isinstance(recs, list):
        return recs
    return None


def _cache_miss_result() -> Dict[str, Any]:
    """Single place for the cache-miss return value."""
    ui_output_html = cache_lookup_html()
    return {
        "template": TemplateResult(section_cache_hit=False),
        "ui_execution_log": [
            make_ui_execution_log_entry_from_registry(
                "cache_lookup_template_recommendations", ui_output_html
            )
        ],
    }


# --- Main node ---


@NodeRegistry.register(
    name="cache_lookup_template_recommendations",
    description="Check cache for template recommendations based on intent + trades",
    max_retries=1,
    timeout=10,
    tags=["smb", "cache", "optimization"],
    display_name="Selecting your page layout",
    show_node=True,
    show_output=False,
)
def cache_lookup_template_recommendations_node(
    state: LandingPageWorkflowState,
    config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """
    Look up template recommendations in cache (cache_key_input/cache_key_output shape).

    Logic:
    1. If use_template_cache disabled, return section_cache_hit=False
    2. Extract trades and website_intention, generate cache key
    3. get_template_recommendations_by_cache_key; read from cache_key_output.resolved_template_recommendations
    4. If hit: return TemplateResult(section_cache_hit=True) + resolved_template_recommendations
    5. If miss: return TemplateResult(section_cache_hit=False)

    Returns:
        Dict with template (TemplateResult), and resolved_template_recommendations on hit.
    """
    start_time = time.time()
    config = config or {}

    if not _get_use_template_cache(state):
        business_name = state.input.business_name if state.input else ""
        logger.info(
            "Template recommendations cache is disabled - skipping lookup, continuing normal flow",
            node="cache_lookup_template_recommendations",
            business_name=business_name
        )
        return _cache_miss_result()

    inp = state.input
    data = state.data
    business_name = inp.business_name if inp else ""
    website_intention = inp.website_context.website_intention if inp else ""
    trade_classification_result = data.trade_classification_result if data else None
    business_id = inp.business_id if inp else None

    logger.info(
        "Starting template recommendations cache lookup",
        node="cache_lookup_template_recommendations",
        business_name=business_name,
        website_intention=website_intention,
        has_trade_classification=bool(trade_classification_result)
    )

    trades = extract_trades_from_state(state, business_id)
    if not trades:
        logger.info(
            "No trades found - cannot generate cache key, continuing normal flow",
            node="cache_lookup_template_recommendations"
        )
        return _cache_miss_result()

    if not website_intention:
        logger.info(
            "No website_intention found - cannot generate cache key, continuing normal flow",
            node="cache_lookup_template_recommendations"
        )
        return _cache_miss_result()

    cache_key = generate_section_cache_key(website_intention, trades)

    try:
        cached_data = get_template_recommendations_by_cache_key(cache_key, config)
        recommendations = _resolved_recommendations_from_cached_doc(cached_data)

        if recommendations:
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "Template recommendations cache HIT - bypassing template generation and section retrieval",
                node="cache_lookup_template_recommendations",
                cache_key=cache_key,
                recommendations_count=len(recommendations),
                duration_ms=round(duration_ms, 2)
            )
            first_template = recommendations[0]
            template_name = first_template.get("template_name") or "Your layout"
            section_mappings = first_template.get("section_mappings") or []
            ui_output_html = cache_lookup_html(
                template_name=template_name,
                section_mappings=section_mappings,
            )
            return {
                "template": TemplateResult(section_cache_hit=True),
                "resolved_template_recommendations": recommendations,
                "ui_execution_log": [
                    make_ui_execution_log_entry_from_registry(
                        "cache_lookup_template_recommendations", ui_output_html
                    )
                ],
            }

        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "Template recommendations cache MISS - continuing normal flow",
            node="cache_lookup_template_recommendations",
            cache_key=cache_key,
            duration_ms=round(duration_ms, 2)
        )
        return _cache_miss_result()

    except Exception as e:
        logger.error(
            "Error during template recommendations cache lookup - continuing normal flow",
            node="cache_lookup_template_recommendations",
            cache_key=cache_key,
            error=str(e)
        )
        return _cache_miss_result()
