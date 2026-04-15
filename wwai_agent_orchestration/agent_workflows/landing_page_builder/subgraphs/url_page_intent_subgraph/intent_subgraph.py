"""
Intent Subgraph Builder.

Builds the intent/campaign production flow: page_context_extractor (when page_url)
then campaign_input_builder. Mergeable into SMB or used standalone in template workflow.

FLOW:
    entry_node --[conditional]--> page_context_extractor --> campaign_input_builder --> exit_node
                    \\                  (query only) --------------------------------->/
"""

from typing import Any, Union
from langgraph.graph import StateGraph

from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.contracts.landing_page_builder.user_input import (
    get_page_url_from_state,
    get_query_from_state,
)

from wwai_agent_orchestration.nodes.landing_page_builder.url_page_intent.page_context_extractor import (
    page_context_extractor_node,
)
from wwai_agent_orchestration.nodes.landing_page_builder.url_page_intent.campaign_input_builder import (
    campaign_input_builder_node,
)

from wwai_agent_orchestration.core.observability.logger import get_logger

logger = get_logger(__name__)


def should_extract_page_context(state: Union[LandingPageWorkflowState, Any]) -> str:
    """
    Decide if we need to extract page context from URL.
    - page_url provided -> page_context_extractor
    - query only -> skip to campaign builder
    """
    page_url = get_page_url_from_state(state)
    query = get_query_from_state(state)
    has_page_url = bool(page_url)
    has_query = bool(query)

    if has_page_url:
        return "page_context_extractor"
    elif has_query:
        return "campaign_input_builder"
    else:
        raise ValueError("Must provide either query or page_url")


def build_intent_subgraph(
    graph: StateGraph,
    entry_node: str,
    exit_node: str,
) -> None:
    """
    Build intent/campaign production subgraph.

    Flow:
        entry_node --[conditional: page_url vs query]-->
          - page_context_extractor --> campaign_input_builder --> exit_node
          - campaign_input_builder --> exit_node  (query only)

    Args:
        graph: StateGraph to add nodes to
        entry_node: Node or START that feeds into this subgraph
        exit_node: Node or END this subgraph feeds into when complete
    """
    graph.add_node("page_context_extractor", page_context_extractor_node)
    graph.add_node("campaign_input_builder", campaign_input_builder_node)

    graph.add_conditional_edges(
        entry_node,
        should_extract_page_context,
        {
            "page_context_extractor": "page_context_extractor",
            "campaign_input_builder": "campaign_input_builder",
        },
    )
    graph.add_edge("page_context_extractor", "campaign_input_builder")
    graph.add_edge("campaign_input_builder", exit_node)

    logger.info("Built intent subgraph")
