# agent_workflows/landing_page_builder/autopop_subgraph.py
"""
Autopopulation Subgraph Builder.

This module contains the function to build the autopopulation subgraph,
which handles the autopopulation workflow within the Landing Page Builder graph.

ASYNC PATTERN: Nodes that call async operations (materialize_node, resolve_imm, etc.)
are defined as 'async def'. LangGraph natively supports async nodes.
"""

from langgraph.graph import StateGraph
# Import autopopulation subgraph nodes
from wwai_agent_orchestration.nodes.landing_page_builder.autopop import (
    autopop_start_node,
    autopopulation_input_builder_node,
    autopop_end_node,
    final_snapshot,
)
# Import subgraph builders
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.style_nodes import build_style_subgraph
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.content_nodes import build_content_subgraph

def build_autopop_subgraph(graph: StateGraph) -> None:
    """
    Build autopopulation subgraph.
    
    This subgraph handles the autopopulation workflow:
    - autopop_start: Entry node (dummy pass-through)
    - autopopulation_input_builder: Builds LangGraph input state
    - S1-S6: Autopopulation agent nodes and materialize nodes
    - autopop_end: Exit node (dummy pass-through)
    
    Flow (with parallelization):
    autopop_start → autopopulation_input_builder
      ├─→ [Styles Pipeline] container_color_agent → container_color_snapshot → [text_color_agent, button_color_agent, misc_color_agent (parallel)] → element_colors_collect → element_colors_snapshot → semantic_names_agent → semantic_names_snapshot → final_snapshot
      └─→ [Content Planning] content_planner
            ├─→ [Content Text Pipeline] content_text_fanout_router → [FAN-OUT: parallel content_text_section_agent nodes] → content_text_collect → content_text_snapshot → final_snapshot
            └─→ [Content Media Pipeline] content_media_fanout_router → [FAN-OUT: parallel content_media_section_agent nodes] → content_media_collect → content_media_snapshot → final_snapshot
      → final_snapshot → autopop_end
    
    Styles pipeline and content planner run in parallel after autopopulation_input_builder.
    Content text and media pipelines run in parallel after content_planner.
    All pipelines converge at final_snapshot, which creates a complete snapshot before autopop_end.
    
    Args:
        graph: StateGraph to add nodes to
    """    
    # --------- Add all nodes to graph ---------
    graph.add_node("autopop_start", autopop_start_node)
    graph.add_node("autopopulation_input_builder", autopopulation_input_builder_node)
    
    # Build style subgraph (adds all style nodes and wires them)
    build_style_subgraph(
        graph,
        entry_node="autopopulation_input_builder",
        exit_node="final_snapshot",
        add_exit_edge=False,
    )

    # Build content subgraph (adds all content nodes and wires them)
    build_content_subgraph(
        graph,
        entry_node="autopopulation_input_builder",
        exit_node="final_snapshot",
        add_exit_edge=False,
    )

    graph.add_node("final_snapshot", final_snapshot)
    graph.add_node("autopop_end", autopop_end_node)

    # --------- Wire the subgraph ---------
    graph.add_edge("autopop_start", "autopopulation_input_builder")

    # AND join: final_snapshot runs only after ALL four pipelines complete.
    # (Separate add_edge calls would trigger on first completion and clear store too early.)
    graph.add_edge(
        [
            "semantic_names_snapshot",
            "content_text_snapshot",
            "content_media_snapshot",
            "content_html_snapshot",
        ],
        "final_snapshot",
    )

    # After autopopulation_input_builder, three parallel paths:
    # 1. Styles pipeline: container_color → [text_color, button_color, misc_color (parallel)] → semantic_names
    #    (wired by build_style_subgraph)
    # 2. Content planner → Content text: (parallel sections)
    #    (wired by build_content_subgraph)
    # 3. Content planner → Content media: (parallel sections)
    #    (wired by build_content_subgraph)
    
    graph.add_edge("final_snapshot", "autopop_end")