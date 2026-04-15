# agent_workflows/landing_page_builder/landing_page_builder_workflow.py
"""
Full Landing Page Builder Recommendation Workflow.

Complete end-to-end workflow with caching, autopopulation, and HTML compilation.
Agent-only path: for direct section IDs use PresetSectionsLandingPageWorkflow instead.

Graph Structure:
    START → planner → business_data_extractor
            ├─→ trade_classifier → END (fire-and-forget)
            └─→ cache_lookup → [bypass: save_template_sections | continue: template_gen → section_retrieval]
                  → autopop → post_process → END
"""

from langgraph.graph import StateGraph, START, END

from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState

from wwai_agent_orchestration.nodes.landing_page_builder.routing.planner_node import planner_node
from wwai_agent_orchestration.nodes.landing_page_builder.business_intelligence.business_data_extractor import business_data_extractor_node
from wwai_agent_orchestration.nodes.landing_page_builder.business_intelligence.trade_classifier_node import trade_classifier_node
from wwai_agent_orchestration.nodes.landing_page_builder.template_selection.cache_lookup_template_recommendations import cache_lookup_template_recommendations_node
from wwai_agent_orchestration.nodes.landing_page_builder.post_processing.save_generation_template_sections import save_generation_template_sections_node

from wwai_agent_orchestration.agent_workflows.landing_page_builder.cache import create_node_cache_policy
from wwai_agent_orchestration.agent_workflows.landing_page_builder.workflows.base_workflow import BaseLandingPageWorkflow
from wwai_agent_orchestration.nodes.landing_page_builder.routing import router_bypass_or_continue
from wwai_agent_orchestration.agent_workflows.landing_page_builder.subgraphs.template_generation_subgraph import build_template_generation_subgraph
from wwai_agent_orchestration.agent_workflows.landing_page_builder.subgraphs.section_retrieval_subgraph import build_section_retrieval_subgraph
from wwai_agent_orchestration.agent_workflows.landing_page_builder.subgraphs.autopop_subgraph import build_autopop_subgraph
from wwai_agent_orchestration.agent_workflows.landing_page_builder.subgraphs.post_processing_subgraph import build_post_processing_subgraph

from wwai_agent_orchestration.core.observability.logger import get_logger
logger = get_logger(__name__)


class LandingPageWorkflow(BaseLandingPageWorkflow):
    """
    Complete Landing Page Builder workflow with caching and optional reflection.
    Agent-only path; for direct section IDs use PresetSectionsLandingPageWorkflow.
    
    Graph Structure:
        START → planner → business_data_extractor
                ├─→ trade_classifier → END (fire-and-forget)
                └─→ cache_lookup → [bypass | continue] → autopop → post_process → END
    
    FEATURES:
    - Agent path: business data extraction, template generation, section retrieval
    - Redis caching with per-node policies
    - Modular subgraphs for maintainability
    - Full HTML compilation and optional screenshots
    """
    
    workflow_name = "landing_page_builder"
    
    def _build_graph(self) -> StateGraph:
        """
        Build full LangGraph workflow with routing, caching, and subgraphs.
        """
        
        graph = StateGraph(LandingPageWorkflowState)
        
        # ====================================================================
        # MAIN GRAPH NODES (not in subgraphs)
        # ====================================================================
        
        # Planner node (first node - no caching needed)
        graph.add_node("planner", planner_node)

        # Trade classifier (fire-and-forget background task)
        graph.add_node("trade_classifier", trade_classifier_node)
        
        # Business data extractor (cache plumbed but off by default via use_cache=False)
        graph.add_node(
            "business_data_extractor",
            business_data_extractor_node,
            cache_policy=create_node_cache_policy("business_data_extractor"),
        )
        
        # Template recommendations cache lookup (checks cache for section recommendations)
        graph.add_node("cache_lookup_template_recommendations", cache_lookup_template_recommendations_node)
        
        # START → Planner → Business Data Extractor
        graph.add_edge(START, "planner")
        graph.add_edge("planner", "business_data_extractor")

        # Trade Classifier (fire-and-forget, parallel)
        # Runs in background after business_data_extractor
        # Does NOT block main workflow - goes directly to END
        graph.add_edge("business_data_extractor", "trade_classifier")
        graph.add_edge("trade_classifier", END)
        
        # Agent Path: Template recommendations cache lookup
        # After business_data_extractor, check cache for section recommendations
        # If cache hit: bypass to save_template_sections → autopop_start
        # If cache miss: continue to campaign_intent_synthesizer (enters template generation subgraph)
        graph.add_edge("business_data_extractor", "cache_lookup_template_recommendations")

        # Extract and save section IDs (for cache bypass path)
        graph.add_node("save_template_sections", save_generation_template_sections_node)

        graph.add_conditional_edges(
            "cache_lookup_template_recommendations",
            router_bypass_or_continue,
            {
                "bypass": "save_template_sections",
                "continue": "campaign_intent_synthesizer"
            }
        )
        
        # ====================================================================
        # BUILD SUBGRAPHS
        # ====================================================================
        
        # Template Generation Subgraph
        # Entry: campaign_intent_synthesizer → Exit: section_retrieval_start
        # The cache checker routes to campaign_intent_synthesizer on cache miss
        build_template_generation_subgraph(
            graph,
            entry_node="campaign_intent_synthesizer",
            exit_node="section_retrieval_start"
        )
        
        # Section Retrieval Subgraph
        # Entry: section_retrieval_start → Exit: save_template_sections
        build_section_retrieval_subgraph(
            graph,
            entry_node="section_retrieval_start",
            exit_node="save_template_sections"
        )
        
        # Autopopulation Subgraph
        # Entry: autopop_start → Exit: autopop_end
        build_autopop_subgraph(graph)

        # Once the template is fetched and saved to db, we start autopopulation.
        # When bypassing (cache hit), save section IDs before autopopulation.
        # Also node is defined in autopop_subgraph, so we add the edge after.
        graph.add_edge("save_template_sections", "autopop_start")

        # Post-Processing Subgraph
        # Entry: autopop_end → Exit: END
        build_post_processing_subgraph(
            graph,
            entry_node="autopop_end"
        )
                
        

        logger.info("Built LandingPageWorkflow graph")

        return graph.compile(
            checkpointer=self.checkpointer,
            cache=self.cache
        )
