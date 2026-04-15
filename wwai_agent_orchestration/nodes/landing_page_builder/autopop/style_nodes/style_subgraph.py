# nodes/smb/autopop/style_nodes/style_subgraph.py
"""
Style subgraph builder.

This module builds the style pipeline subgraph which handles:
- Container color autopopulation
- Element color autopopulation (text, button, misc - parallelized)
- Semantic names autopopulation

Flow:
container_color_agent → container_color_snapshot 
  → [text_color_agent, button_color_agent, misc_color_agent (parallel)] 
  → element_colors_collect → element_colors_snapshot 
  → semantic_names_agent → semantic_names_snapshot
"""

from langgraph.graph import StateGraph

# Import style nodes
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.style_nodes.container_color import (
    container_color_agent,
    container_color_snapshot
)
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.style_nodes.text_color import (
    text_color_agent
)
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.style_nodes.button_color import (
    button_color_agent
)
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.style_nodes.misc_color import (
    misc_color_agent
)
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.style_nodes.element_colors import (
    element_colors_collect,
    element_colors_snapshot
)
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.style_nodes.semantic_names import (
    semantic_names_agent,
    semantic_names_snapshot
)


def build_style_subgraph(
    graph: StateGraph,
    entry_node: str = "autopopulation_input_builder",
    exit_node: str = "final_snapshot",
    add_exit_edge: bool = True,
) -> None:
    """
    Build style pipeline subgraph.
    
    This subgraph handles the style autopopulation workflow:
    - Container color autopopulation
    - Element color autopopulation (text, button, misc - parallelized)
    - Semantic names autopopulation
    
    Flow:
    entry_node → container_color_agent → container_color_snapshot 
      → [text_color_agent, button_color_agent, misc_color_agent (parallel)] 
      → element_colors_collect → element_colors_snapshot 
      → semantic_names_agent → semantic_names_snapshot → exit_node
    
    Args:
        graph: StateGraph to add nodes to
        entry_node: Name of the node that feeds into the style pipeline (default: "autopopulation_input_builder")
        exit_node: Name of the node that the style pipeline feeds into (default: "final_snapshot")
    """
    # Add all style nodes to graph
    graph.add_node("container_color_agent", container_color_agent)
    graph.add_node("container_color_snapshot", container_color_snapshot)
    
    graph.add_node("text_color_agent", text_color_agent)
    graph.add_node("button_color_agent", button_color_agent)
    graph.add_node("misc_color_agent", misc_color_agent)
    graph.add_node("element_colors_collect", element_colors_collect)
    graph.add_node("element_colors_snapshot", element_colors_snapshot)
    
    graph.add_node("semantic_names_agent", semantic_names_agent)
    graph.add_node("semantic_names_snapshot", semantic_names_snapshot)
    
    # Wire the style pipeline
    # Entry point: from autopopulation_input_builder (or specified entry_node)
    graph.add_edge(entry_node, "container_color_agent")
    
    # Container color flow
    graph.add_edge("container_color_agent", "container_color_snapshot")
    
    # Element colors: three parallel agents after container_color_snapshot
    graph.add_edge("container_color_snapshot", "text_color_agent")
    graph.add_edge("container_color_snapshot", "button_color_agent")
    graph.add_edge("container_color_snapshot", "misc_color_agent")
    
    # All three converge to collect, then snapshot
    graph.add_edge("text_color_agent", "element_colors_collect")
    graph.add_edge("button_color_agent", "element_colors_collect")
    graph.add_edge("misc_color_agent", "element_colors_collect")
    graph.add_edge("element_colors_collect", "element_colors_snapshot")
    
    # Semantic names flow
    graph.add_edge("element_colors_snapshot", "semantic_names_agent")
    graph.add_edge("semantic_names_agent", "semantic_names_snapshot")

    # Exit point: to final_snapshot (or specified exit_node).
    # When add_exit_edge=False, parent uses AND join from all pipelines.
    if add_exit_edge:
        graph.add_edge("semantic_names_snapshot", exit_node)
