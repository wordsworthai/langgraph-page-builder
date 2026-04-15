# agent_workflows/landing_page_builder/template_generation_subgraph/template_generation_subgraph.py
"""
Template Generation Subgraph Builder.

This module contains the function to build the template generation subgraph,
which handles:
- Campaign intent synthesis
- Section repo fetching
- Template L0/L1 generation
- Template evaluation (reflection loop)

FLOW:
    entry_node → campaign_intent_synthesizer → section_repo_fetcher →
    generate_template_structures →
    [CONDITIONAL: evaluation loop OR exit_node]
    
    Reflection loop:
    template_evaluator_smb → generate_template_structures (if iterations remaining)
"""

from typing import Dict, Any
from langgraph.graph import StateGraph

from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState

# Node imports
from wwai_agent_orchestration.nodes.landing_page_builder.business_intelligence.campaign_intent_synthesizer import campaign_intent_synthesizer_node
from wwai_agent_orchestration.nodes.landing_page_builder.template_selection.section_repo_fetcher import section_repo_fetcher_node
from wwai_agent_orchestration.nodes.landing_page_builder.template_selection.generate_template_structures import generate_template_structures_node
from wwai_agent_orchestration.nodes.landing_page_builder.template_selection.template_evaluator_smb import template_evaluator_smb_node

from wwai_agent_orchestration.agent_workflows.landing_page_builder.cache import create_node_cache_policy
from wwai_agent_orchestration.core.observability.logger import get_logger
logger = get_logger(__name__)


def router_select_section_retrieval_or_evaluation(state: LandingPageWorkflowState) -> str:
    """
    Route based on reflection settings and iteration count.
    
    Returns:
        "evaluation" → Run template evaluator (reflection loop)
        "exit" → Proceed to section retrieval
    """
    exec_config = state.execution_config
    if exec_config and hasattr(exec_config, "reflection"):
        enable_reflection = exec_config.reflection.enable_reflection
        max_iterations = exec_config.reflection.max_iterations
    elif exec_config and isinstance(exec_config, dict):
        reflection = exec_config.get("reflection") or {}
        enable_reflection = reflection.get("enable_reflection", False) if isinstance(reflection, dict) else False
        max_iterations = reflection.get("max_iterations", 1) if isinstance(reflection, dict) else 1
    else:
        enable_reflection = False
        max_iterations = 1
    iteration = state.template.iteration if state.template is not None else 0

    if not enable_reflection:
        return "exit"

    if iteration < max_iterations:
        return "evaluation"
    else:
        return "exit"


def build_template_generation_subgraph(
    graph: StateGraph,
    entry_node: str,
    exit_node: str
) -> None:
    """
    Build template generation subgraph.
    
    This subgraph handles the template generation workflow with reflection loop:
    
    Flow:
        entry_node → campaign_intent_synthesizer → section_repo_fetcher →
        generate_template_structures →
        [CONDITIONAL]
          ├─ "evaluation" → template_evaluator_smb → generate_template_structures (loop)
          └─ "exit" → exit_node
    
    Args:
        graph: StateGraph to add nodes to
        entry_node: Node that feeds into this subgraph
        exit_node: Node this subgraph feeds into when complete
    """
    # --------- Add all nodes to graph ---------
    graph.add_node(
        "campaign_intent_synthesizer",
        campaign_intent_synthesizer_node,
        cache_policy=create_node_cache_policy("campaign_intent_synthesizer"),
    )
    
    graph.add_node(
        "section_repo_fetcher",
        section_repo_fetcher_node,
        cache_policy=create_node_cache_policy("section_repo_fetcher"),
    )
    
    graph.add_node(
        "generate_template_structures",
        generate_template_structures_node,
        cache_policy=create_node_cache_policy("generate_template_structures"),
    )
    
    # Template evaluator - no caching (used in reflection loop)
    graph.add_node("template_evaluator_smb", template_evaluator_smb_node)
    
    # --------- Wire the subgraph ---------
    
    # Entry: entry_node → campaign_intent_synthesizer
    # Skip if entry_node is already campaign_intent_synthesizer (direct routing)
    if entry_node != "campaign_intent_synthesizer":
        graph.add_edge(entry_node, "campaign_intent_synthesizer")
    
    # Linear flow through template generation (section_repo_result includes allowed_section_types)
    graph.add_edge("campaign_intent_synthesizer", "section_repo_fetcher")
    graph.add_edge("section_repo_fetcher", "generate_template_structures")
    
    # Conditional routing: evaluation loop or exit
    graph.add_conditional_edges(
        "generate_template_structures",
        router_select_section_retrieval_or_evaluation,
        {
            "evaluation": "template_evaluator_smb",
            "exit": exit_node
        }
    )
    
    # Reflection loop: evaluator → back to generation
    graph.add_edge("template_evaluator_smb", "generate_template_structures")
    
    logger.info("Built template generation subgraph")
