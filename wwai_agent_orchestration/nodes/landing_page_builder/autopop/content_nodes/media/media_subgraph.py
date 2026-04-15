# nodes/smb/autopop/content_nodes/media/media_subgraph.py
"""
Media subgraph builder.

This module builds the media pipeline subgraph which handles:
- Content media (image + video) generation

Two processing paths (conditional routing):
1. Parallel path: Fan-out to section-level agents (one section per node)
2. Template-level path: Parallel image and video nodes processing all sections together (enables deduplication)

Flow (Parallel):
entry_node → content_media_router → content_media_fanout_router → [FAN-OUT: parallel content_media_section_agent nodes] → content_media_collect → content_media_snapshot → exit_node

Flow (Template-level):
entry_node → content_media_router → content_media_template_level_router → [content_media_image_template_level_agent, content_media_video_template_level_agent (parallel)] → content_media_collect → content_media_snapshot → exit_node
"""

from langgraph.graph import StateGraph

from wwai_agent_orchestration.nodes.landing_page_builder.autopop.content_nodes.media import (
    content_media_router_node,
    content_media_router_condition,
    content_media_fanout_router,
    content_media_fanout,
    content_media_template_level_router,
    content_media_section_agent,
    content_media_image_template_level_agent,
    content_media_video_template_level_agent,
    content_media_collect,
    content_media_snapshot,
)
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.content_nodes.media.media_data_context_fetcher import (
    media_data_context_fetcher_node
)


def build_media_parallel_subgraph(
    graph: StateGraph,
    entry_node: str,
    exit_node: str
) -> None:
    """
    Build parallel media subgraph (section-level agents).
    
    This subgraph handles fan-out to section-level agents where each section
    is processed in parallel by separate agent nodes.
    
    Flow:
    entry_node → [FAN-OUT: parallel content_media_section_agent nodes] → exit_node
    
    Args:
        graph: StateGraph to add nodes to
        entry_node: Name of the node that feeds into the parallel path (should be "content_media_fanout_router")
        exit_node: Name of the node that the parallel path feeds into (should be "content_media_collect")
    """
    # Add parallel path nodes (entry_node router already added in build_media_subgraph)
    graph.add_node("content_media_section_agent", content_media_section_agent)
    
    # Fan-out: entry_node → parallel content_media_section_agent nodes
    graph.add_conditional_edges(
        entry_node,
        content_media_fanout
    )
    
    # Fan-in: All content_media_section_agent nodes → exit_node
    graph.add_edge("content_media_section_agent", exit_node)


def build_media_template_level_subgraph(
    graph: StateGraph,
    entry_node: str,
    exit_node: str
) -> None:
    """
    Build template-level media subgraph (image and video agents).
    
    This subgraph handles parallel image and video processing where all sections
    are processed together in a single call, enabling deduplication across sections.
    
    Flow:
    entry_node → [content_media_image_template_level_agent, content_media_video_template_level_agent (parallel)] → exit_node
    
    Args:
        graph: StateGraph to add nodes to
        entry_node: Name of the node that feeds into the template-level path (should be "content_media_template_level_router")
        exit_node: Name of the node that the template-level path feeds into (should be "content_media_collect")
    """
    # Add template-level path nodes (entry_node router already added in build_media_subgraph)
    graph.add_node("content_media_image_template_level_agent", content_media_image_template_level_agent)
    graph.add_node("content_media_video_template_level_agent", content_media_video_template_level_agent)
    
    # Both image and video nodes run in parallel from entry_node
    graph.add_edge(entry_node, "content_media_image_template_level_agent")
    graph.add_edge(entry_node, "content_media_video_template_level_agent")
    
    # Both converge at exit_node
    graph.add_edge("content_media_image_template_level_agent", exit_node)
    graph.add_edge("content_media_video_template_level_agent", exit_node)


def build_media_subgraph(
    graph: StateGraph,
    entry_node: str,
    exit_node: str,
    add_exit_edge: bool = True,
) -> None:
    """
    Build media pipeline subgraph.
    
    This subgraph handles the content media generation workflow with two paths:
    - Parallel path: Fan-out to section-level agents (one section per node)
    - Template-level path: Parallel image and video nodes processing all sections together (enables deduplication)
    
    Flow (Parallel):
    entry_node → media_data_context_fetcher → content_media_router → content_media_fanout_router → [FAN-OUT: parallel content_media_section_agent nodes] → content_media_collect → content_media_snapshot → exit_node
    
    Flow (Template-level):
    entry_node → media_data_context_fetcher → content_media_router → content_media_template_level_router → [content_media_image_template_level_agent, content_media_video_template_level_agent (parallel)] → content_media_collect → content_media_snapshot → exit_node
    
    Args:
        graph: StateGraph to add nodes to
        entry_node: Name of the node that feeds into the media pipeline (typically "content_planner")
        exit_node: Name of the node that the media pipeline feeds into
    """
    # Add media data context fetcher node (fetches all recommendations upfront)
    graph.add_node("media_data_context_fetcher", media_data_context_fetcher_node)
    
    # Add shared nodes
    graph.add_node("content_media_router", content_media_router_node)
    
    # The end nodes which collect response from the parallel and template-level subgraphs
    # and then snapshot the final response.
    graph.add_node("content_media_collect", content_media_collect)
    graph.add_node("content_media_snapshot", content_media_snapshot)
    
    # Top level nodes that route to the parallel and template-level subgraphs.
    graph.add_node("content_media_fanout_router", content_media_fanout_router)
    graph.add_node("content_media_template_level_router", content_media_template_level_router)
    
    # Wire the entry point: entry_node → media_data_context_fetcher → content_media_router
    # First fetch all media recommendations, then route to processing paths
    graph.add_edge(entry_node, "media_data_context_fetcher")
    graph.add_edge("media_data_context_fetcher", "content_media_router")
    
    # Conditional routing: router decides which path to take
    graph.add_conditional_edges(
        "content_media_router",
        content_media_router_condition,
        {
            "parallel": "content_media_fanout_router",
            "template_level": "content_media_template_level_router"
        }
    )
    
    # Build parallel  subgraphs starting from the top level nodes.
    build_media_parallel_subgraph(graph, "content_media_fanout_router", "content_media_collect")
    
    # Build template-level subgraphs starting from the top level nodes.
    build_media_template_level_subgraph(graph, "content_media_template_level_router", "content_media_collect")
    
    # Both paths converge at collect, then snapshot, then exit.
    graph.add_edge("content_media_collect", "content_media_snapshot")
    if add_exit_edge:
        graph.add_edge("content_media_snapshot", exit_node)
