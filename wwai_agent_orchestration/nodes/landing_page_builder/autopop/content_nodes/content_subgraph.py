# nodes/smb/autopop/content_nodes/content_subgraph.py
"""
Content subgraph builder.

This module builds the content pipeline subgraph which handles:
- Content planning
- Content text generation (parallelized by section)
- Content media generation (parallelized by section)

Flow:
entry_node → content_planner
  ├─→ [Content Text Pipeline] content_text_fanout_router → [FAN-OUT: parallel content_text_section_agent nodes] → content_text_collect → content_text_snapshot → exit_node
  └─→ [Content Media Pipeline] content_media_fanout_router → [FAN-OUT: parallel content_media_section_agent nodes] → content_media_collect → content_media_snapshot → exit_node

Both text and media pipelines run in parallel after content_planner.
"""

from langgraph.graph import StateGraph

# Import content planner
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.content_nodes.content_planner import content_planner

# Import subgraph builders
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.content_nodes.text.text_subgraph import build_text_subgraph
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.content_nodes.media.media_subgraph import build_media_subgraph
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.content_nodes.html.html_subgraph import build_html_subgraph


def build_content_subgraph(
    graph: StateGraph,
    entry_node: str = "autopopulation_input_builder",
    exit_node: str = "final_snapshot",
    add_exit_edge: bool = True,
) -> None:
    """
    Build content pipeline subgraph.
    
    This subgraph handles the content autopopulation workflow:
    - Content planning
    - Content text generation (parallelized by section)
    - Content media generation (parallelized by section)
    
    Flow:
    entry_node → content_planner
      ├─→ [Content Text Pipeline] content_data_context_fetcher → content_text_fanout_router → [FAN-OUT: parallel content_text_section_agent nodes] → content_text_collect → content_text_snapshot → exit_node
      └─→ [Content Media Pipeline] media_data_context_fetcher → content_media_router → [parallel or template-level paths] → content_media_collect → content_media_snapshot → exit_node
    
    Content data context is fetched after content planning but before text generation.
    Media data context (recommendations) is fetched after content planning but before media processing.
    
    Args:
        graph: StateGraph to add nodes to
        entry_node: Name of the node that feeds into the content pipeline (default: "autopopulation_input_builder")
        exit_node: Name of the node that the content pipeline feeds into (default: "final_snapshot")
    """
    # Add content planner node
    graph.add_node("content_planner", content_planner)
    
    # Wire the content pipeline
    # Entry point: from autopopulation_input_builder (or specified entry_node)
    graph.add_edge(entry_node, "content_planner")
    
    # Build text and media subgraphs (both run in parallel after content_planner)
    # Text subgraph includes content_data_context_fetcher after content_planner
    build_text_subgraph(
        graph,
        entry_node="content_planner",
        exit_node=exit_node,
        add_exit_edge=add_exit_edge,
    )
    # Media subgraph: includes media_data_context_fetcher internally
    build_media_subgraph(
        graph,
        entry_node="content_planner",
        exit_node=exit_node,
        add_exit_edge=add_exit_edge,
    )
    # HTML subgraph: single node processes all sections (no fan-out)
    build_html_subgraph(
        graph,
        entry_node="content_planner",
        exit_node=exit_node,
        add_exit_edge=add_exit_edge,
    )