# nodes/landing_page_builder/routing/routers.py
"""
Conditional edge router functions for Landing Page Builder workflows.

Used in add_conditional_edges() to route execution based on state.
"""

from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.core.observability.logger import get_logger

logger = get_logger(__name__)


def router_bypass_or_continue(state: LandingPageWorkflowState) -> str:
    """
    Route based on section cache hit.

    Returns:
        "bypass" → autopop_start (skip template generation and section retrieval)
        "continue" → campaign_intent_synthesizer (normal flow - enters template generation subgraph)
    """
    section_cache_hit = state.template.section_cache_hit if state.template else False

    if section_cache_hit:
        logger.info(
            "Section cache hit - bypassing template generation and section retrieval",
            node="router_bypass_or_continue"
        )
        return "bypass"
    else:
        logger.info(
            "Section cache miss - continuing normal flow",
            node="router_bypass_or_continue"
        )
        return "continue"
