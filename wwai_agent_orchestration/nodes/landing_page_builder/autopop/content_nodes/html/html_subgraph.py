# nodes/smb/autopop/content_nodes/html/html_subgraph.py
"""
HTML subgraph builder.

This module builds the HTML content pipeline subgraph which handles:
- Content HTML generation (maps, embeds) for all sections in a single node

Flow:
entry_node → content_html_agent → content_html_snapshot → exit_node
"""

from langgraph.graph import StateGraph

from wwai_agent_orchestration.nodes.landing_page_builder.autopop.content_nodes.html import (
    content_html_agent,
    content_html_snapshot,
)


def build_html_subgraph(
    graph: StateGraph,
    entry_node: str,
    exit_node: str,
    add_exit_edge: bool = True,
) -> None:
    """
    Build HTML content pipeline subgraph.

    This subgraph handles HTML embed content (maps, YouTube, etc.) for all sections
    in a single node (no section-wise fan-out).

    Flow:
    entry_node → content_html_agent → content_html_snapshot → exit_node

    Args:
        graph: StateGraph to add nodes to
        entry_node: Name of the node that feeds into the HTML pipeline
        exit_node: Name of the node that the HTML pipeline feeds into
        add_exit_edge: If True, add edge from content_html_snapshot to exit_node
    """
    graph.add_node("content_html_agent", content_html_agent)
    graph.add_node("content_html_snapshot", content_html_snapshot)

    graph.add_edge(entry_node, "content_html_agent")
    graph.add_edge("content_html_agent", "content_html_snapshot")
    if add_exit_edge:
        graph.add_edge("content_html_snapshot", exit_node)
