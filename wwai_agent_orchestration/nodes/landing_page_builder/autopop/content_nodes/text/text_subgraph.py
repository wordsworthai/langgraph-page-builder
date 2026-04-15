# nodes/smb/autopop/content_nodes/text/text_subgraph.py
"""
Text subgraph builder.

This module builds the text pipeline subgraph which handles:
- Content text generation (parallelized by section)

Flow:
entry_node → content_text_fanout_router → [FAN-OUT: parallel content_text_section_agent nodes] → content_text_collect → content_text_snapshot → exit_node
"""

from langgraph.graph import StateGraph

from wwai_agent_orchestration.nodes.landing_page_builder.autopop.content_nodes.text import (
    content_text_fanout_router,
    content_text_fanout,
    content_text_section_agent,
    content_text_collect,
    content_text_snapshot,
)
# Import content data context fetcher
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.content_nodes.content_data_context_fetcher import content_data_context_fetcher_node


def build_text_subgraph(
    graph: StateGraph,
    entry_node: str,
    exit_node: str,
    add_exit_edge: bool = True,
) -> None:
    """
    Build text pipeline subgraph.
    
    This subgraph handles the content text generation workflow:
    - Content text generation (parallelized by section)
    
    Flow:
    entry_node → content_data_context_fetcher → content_text_fanout_router → [FAN-OUT: parallel content_text_section_agent nodes] → content_text_collect → content_text_snapshot → exit_node
    
    Args:
        graph: StateGraph to add nodes to
        entry_node: Name of the node that feeds into the text pipeline
        exit_node: Name of the node that the text pipeline feeds into
    """
    # Add content data context fetcher node (runs after content_planner, before text generation)
    graph.add_node("content_data_context_fetcher", content_data_context_fetcher_node)
    
    # Text pipeline nodes
    graph.add_node("content_text_fanout_router", content_text_fanout_router)
    graph.add_node("content_text_section_agent", content_text_section_agent)
    graph.add_node("content_text_collect", content_text_collect)
    graph.add_node("content_text_snapshot", content_text_snapshot)
    
    # Wire the text pipeline
    # First fetch context data, then fan out to parallel section agents
    graph.add_edge(entry_node, "content_data_context_fetcher")
    graph.add_edge("content_data_context_fetcher", "content_text_fanout_router")
    # Fan-out: content_text_fanout_router → parallel content_text_section_agent nodes
    graph.add_conditional_edges(
        "content_text_fanout_router",
        content_text_fanout
    )
    # Fan-in: All content_text_section_agent nodes → content_text_collect
    graph.add_edge("content_text_section_agent", "content_text_collect")
    graph.add_edge("content_text_collect", "content_text_snapshot")
    if add_exit_edge:
        graph.add_edge("content_text_snapshot", exit_node)
