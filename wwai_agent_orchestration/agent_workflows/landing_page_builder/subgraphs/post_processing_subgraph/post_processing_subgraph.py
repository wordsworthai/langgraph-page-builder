# agent_workflows/landing_page_builder/post_processing_subgraph/post_processing_subgraph.py
"""
Post-Processing Subgraph Builder.

This module contains the function to build the post-processing subgraph,
which handles:
- Template compilation (ALWAYS RUNS - not conditional)
- HTML compilation (conditional based on execution_config.compilation.enable_html_compilation)
- Screenshot capture (conditional based on execution_config.compilation.enable_screenshot_compilation)

FLOW:
    entry_node → template_compilation (always) → [CONDITIONAL: enable_html_compilation]
      ├─ "html_compilation" → html_compilation → [CONDITIONAL: enable_screenshot_compilation]
      │     ├─ "screenshot_capture" → screenshot_capture → END
      │     └─ "end" → END
      └─ "end" → END (skip HTML compilation, but template compilation already ran)
"""

from typing import Dict, Any
from langgraph.graph import StateGraph, END

from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState

# Node imports
from wwai_agent_orchestration.nodes.landing_page_builder.post_processing.template_compilation_node import template_compilation_node
from wwai_agent_orchestration.nodes.landing_page_builder.post_processing.db_html_compilation_node import db_html_compilation_node
from wwai_agent_orchestration.nodes.landing_page_builder.post_processing.screenshot_capture_node import screenshot_capture_node

from wwai_agent_orchestration.core.observability.logger import get_logger
logger = get_logger(__name__)


def router_html_compilation_or_skip(state: LandingPageWorkflowState) -> str:
    """
    Route to HTML compilation if enabled, else skip to END.

    This router runs AFTER template_compilation (which always runs).
    Uses execution_config.compilation.enable_html_compilation (default True if missing).

    Returns:
        "html_compilation" → Run HTML compilation
        "end" → Skip directly to END (template compilation already completed)
    """
    exec_config = state.execution_config
    enable_html_compilation = True
    if exec_config:
        if hasattr(exec_config, "compilation"):
            enable_html_compilation = exec_config.compilation.enable_html_compilation
        elif isinstance(exec_config, dict):
            compilation = exec_config.get("compilation") or {}
            enable_html_compilation = compilation.get("enable_html_compilation", False) if isinstance(compilation, dict) else False
    logger.info(
        f"Routing HTML compilation: enable_html_compilation={enable_html_compilation}",
        enable_html_compilation=enable_html_compilation
    )
    
    if enable_html_compilation:
        return "html_compilation"
    else:
        return "end"  # Skip directly to END (template compilation already completed)


def router_screenshot_capture_or_skip(state: LandingPageWorkflowState) -> str:
    """
    Route to screenshot capture if enabled, else skip to END.
    
    This router runs AFTER html_compilation completes.
    
    Checks:
    1. execution_config.compilation.enable_screenshot_compilation (if exists)
    2. Falls back to False if not specified
    
    Returns:
        "screenshot_capture" → Run screenshot capture
        "end" → Skip directly to END
    """
    exec_config = state.execution_config

    enable_screenshot = False
    if exec_config:
        if hasattr(exec_config, "compilation"):
            enable_screenshot = exec_config.compilation.enable_screenshot_compilation
        elif isinstance(exec_config, dict):
            compilation = exec_config.get("compilation") or {}
            enable_screenshot = compilation.get("enable_screenshot_compilation", False) if isinstance(compilation, dict) else False
    
    logger.info(
        f"Routing from html_compilation: enable_screenshot_compilation={enable_screenshot}",
        enable_screenshot_compilation=enable_screenshot
    )
    
    if enable_screenshot:
        return "screenshot_capture"
    else:
        return "end"  # Skip to END


def build_post_processing_subgraph(
    graph: StateGraph,
    entry_node: str
) -> None:
    """
    Build post-processing subgraph.
    
    This subgraph handles the post-processing workflow:
    
    Flow:
        entry_node → template_compilation (always) → [CONDITIONAL: enable_html_compilation]
          ├─ "html_compilation" → html_compilation → [CONDITIONAL: enable_screenshot_compilation]
          │     ├─ "screenshot_capture" → screenshot_capture → END
          │     └─ "end" → END
          └─ "end" → END (skip HTML compilation, but template compilation already ran)
    
    Note: 
    - Template compilation ALWAYS RUNS (not conditional)
    - HTML compilation can be disabled via execution_config.compilation.enable_html_compilation=False
    - This subgraph routes to END directly, no exit_node needed.
    
    Args:
        graph: StateGraph to add nodes to
        entry_node: Node that feeds into this subgraph (typically autopop_end)
    """
    # --------- Add all nodes to graph ---------
    
    # Template compilation node (ALWAYS RUNS - not conditional)
    graph.add_node("template_compilation", template_compilation_node)
    
    graph.add_node("html_compilation", db_html_compilation_node)
    
    # Screenshot capture node (conditional - captures screenshots from HTML)
    graph.add_node("screenshot_capture", screenshot_capture_node)
    
    # --------- Wire the subgraph ---------
    
    # Template compilation always runs first (no conditional)
    graph.add_edge(entry_node, "template_compilation")
    
    # Conditional routing: HTML compilation or skip to END
    # This checks enable_html_compilation at runtime
    graph.add_conditional_edges(
        "template_compilation",
        router_html_compilation_or_skip,
        {
            "html_compilation": "html_compilation",
            "end": END  # Skip directly to END if HTML compilation disabled
        }
    )
    
    # Conditional routing: screenshot capture or skip to END
    # This runs AFTER html_compilation (if HTML compilation was enabled)
    graph.add_conditional_edges(
        "html_compilation",
        router_screenshot_capture_or_skip,
        {
            "screenshot_capture": "screenshot_capture",
            "end": END  # Skip directly to END if screenshots disabled
        }
    )
    
    # Screenshot capture always goes to END after completion
    graph.add_edge("screenshot_capture", END)
    
    logger.info("Built post-processing subgraph")
