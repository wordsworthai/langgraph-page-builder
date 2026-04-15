# agent_workflows/landing_page_builder/section_retrieval_subgraph/section_retrieval_subgraph.py
"""
Section Retrieval Subgraph Builder.

This module contains the function to build the section retrieval subgraph,
which handles:
- Fan-out to parallel section retrievers
- Collection of parallel results
- Saving section cache (Redis) - populates state with resolved_template_recommendations

FLOW:
    entry_node → section_retrieval_start → [FAN-OUT: resolve_template_sections_from_repo x N] →
    cache_template_recommendations → exit_node

exit_node is typically save_template_sections. The main workflow wires save_template_sections
to the next step (autopop_start or post_processing).
"""

from typing import Dict, Any, List
from langgraph.graph import StateGraph
from langgraph.types import Send

from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.agent_workflows.landing_page_builder.cache import create_node_cache_policy
from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry

# Node imports
from wwai_agent_orchestration.nodes.landing_page_builder.template_selection.resolve_template_sections_from_repo import resolve_template_sections_from_repo_node
from wwai_agent_orchestration.nodes.landing_page_builder.template_selection.cache_template_recommendations import cache_template_recommendations_node

from wwai_agent_orchestration.core.observability.logger import get_logger
logger = get_logger(__name__)


@NodeRegistry.register(
    name="section_retrieval_start",
    description="Dummy node marking the start of parallel section retrieval fan-out",
    max_retries=1,
    timeout=90,
    tags=["smb", "routing", "fan-out"],
    display_name="Starting section retrieval",
    show_node=True,
    show_output=False,
)
def section_retrieval_start_node(state: LandingPageWorkflowState) -> Dict[str, Any]:
    """Dummy node - just passes through to fan-out"""
    return {}


def router_fan_out_parallel_section_retrievers(state: LandingPageWorkflowState) -> List[Send]:
    """
    Fan-out router that creates parallel Send() calls for each template.
    
    Returns:
        List of Send objects, one per template
    """
    t = state.template
    templates = (t.refined_templates or t.templates) if t else None
    if not templates:
        raise ValueError("No templates available for section retrieval")

    section_repo = (t.section_repo_result.section_repo if t and t.section_repo_result else []) or []
    campaign_intent = state.data.campaign_intent if state.data else None
    business_name = state.input.business_name if state.input else ""

    return [
        Send("resolve_template_sections_from_repo", {
            "template": {
                "section_retrieval_payload": {
                    "template": template,
                    "section_repo": section_repo,
                    "campaign_intent": campaign_intent,
                    "business_name": business_name,
                }
            }
        })
        for template in templates
    ]


def build_section_retrieval_subgraph(
    graph: StateGraph,
    entry_node: str,
    exit_node: str,
) -> None:
    """
    Build section retrieval subgraph.
    
    This subgraph handles the section retrieval workflow with fan-out/fan-in:
    
    Flow:
        entry_node → section_retrieval_start → [FAN-OUT: resolve_template_sections_from_repo x N] →
        cache_template_recommendations → exit_node
    
    Args:
        graph: StateGraph to add nodes to
        entry_node: Node that feeds into this subgraph (typically generate_template_structures)
        exit_node: Node this subgraph feeds into when complete (typically save_template_sections)
    """
    # --------- Add all nodes to graph ---------
    
    # Dummy router for fan-out, this router just adds a node, and does nothing.
    graph.add_node("section_retrieval_start", section_retrieval_start_node)
    
    # Section retriever - runs in parallel for each template
    graph.add_node(
        "resolve_template_sections_from_repo",
        resolve_template_sections_from_repo_node,
        cache_policy=create_node_cache_policy("resolve_template_sections_from_repo"),
    )
    
    # Persist template recommendations to cache (fan-in target)
    graph.add_node("cache_template_recommendations", cache_template_recommendations_node)
    
    # Note: save_template_sections is already added in the main workflow graph,
    # so we don't add it here to avoid duplicate node error
    
    # --------- Wire the subgraph ---------
    
    if entry_node != "section_retrieval_start":
        # Entry: entry_node → section_retrieval_start
        graph.add_edge(entry_node, "section_retrieval_start")
    else:
        # The edge to start of this graph is already defined by the caller.
        pass
    
    # Fan-out to parallel section retrievers
    graph.add_conditional_edges(
        "section_retrieval_start",
        router_fan_out_parallel_section_retrievers
    )
    
    # Fan-in: all resolve_template_sections_from_repo instances → cache_template_recommendations
    graph.add_edge("resolve_template_sections_from_repo", "cache_template_recommendations")
    
    # Exit: cache_template_recommendations → exit_node (typically save_template_sections)
    graph.add_edge("cache_template_recommendations", exit_node)
    
    logger.info("Built section retrieval subgraph")
