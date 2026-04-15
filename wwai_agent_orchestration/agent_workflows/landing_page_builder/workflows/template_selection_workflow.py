# agent_workflows/landing_page_builder/template_selection_workflow.py
"""
Template Selection Workflow.

Workflow for template generation and section retrieval with ipsum_lorem HTML compilation.
Skips autopopulation but includes HTML preview with placeholder content.

Graph Structure:
    START → planner → business_data_extractor → cache_lookup →
    [bypass: save_template_sections | continue: template_gen → section_retrieval] →
    post_processing_subgraph → END

"""

from langgraph.graph import StateGraph, START, END

from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState

from wwai_agent_orchestration.nodes.landing_page_builder.routing.planner_node import planner_node
from wwai_agent_orchestration.nodes.landing_page_builder.business_intelligence.business_data_extractor import business_data_extractor_node
from wwai_agent_orchestration.nodes.landing_page_builder.template_selection.cache_lookup_template_recommendations import cache_lookup_template_recommendations_node
from wwai_agent_orchestration.nodes.landing_page_builder.post_processing.save_generation_template_sections import save_generation_template_sections_node

from wwai_agent_orchestration.agent_workflows.landing_page_builder.cache import create_node_cache_policy
from wwai_agent_orchestration.agent_workflows.landing_page_builder.workflows.base_workflow import BaseLandingPageWorkflow
from wwai_agent_orchestration.nodes.landing_page_builder.routing import router_bypass_or_continue
from wwai_agent_orchestration.agent_workflows.landing_page_builder.subgraphs.template_generation_subgraph import build_template_generation_subgraph
from wwai_agent_orchestration.agent_workflows.landing_page_builder.subgraphs.section_retrieval_subgraph import build_section_retrieval_subgraph
from wwai_agent_orchestration.agent_workflows.landing_page_builder.subgraphs.post_processing_subgraph import build_post_processing_subgraph

from wwai_agent_orchestration.core.observability.logger import get_logger
logger = get_logger(__name__)


class TemplateSelectionWorkflow(BaseLandingPageWorkflow):
    """
    Workflow for template selection with ipsum_lorem HTML preview.
    
    Graph Structure:
        START → planner → business_data_extractor → cache_lookup →
        [bypass: save_template_sections | continue: template_gen → section_retrieval] →
        post_processing_subgraph → END
    
    Use case: Generate and select templates + retrieve sections, then compile
    HTML with placeholder (ipsum_lorem) content. Skips autopopulation.
    Useful for template exploration and preview before actual content population.
    """
    
    workflow_name = "template_selection"
    
    def _build_graph(self) -> StateGraph:
        """Build graph with section retrieval and ipsum_lorem HTML compilation."""
        
        graph = StateGraph(LandingPageWorkflowState)
        
        # Add main entry nodes
        graph.add_node("planner", planner_node)
        graph.add_node(
            "business_data_extractor",
            business_data_extractor_node,
            cache_policy=create_node_cache_policy("business_data_extractor"),
        )
        graph.add_node("cache_lookup_template_recommendations", cache_lookup_template_recommendations_node)
        
        # Wire main graph routing
        graph.add_edge(START, "planner")
        graph.add_edge("planner", "business_data_extractor")

        # Cache lookup: bypass to save_template_sections on hit, continue to template_gen on miss
        # save_template_sections → template_compilation is wired by post_processing subgraph
        graph.add_edge("business_data_extractor", "cache_lookup_template_recommendations")
        graph.add_conditional_edges(
            "cache_lookup_template_recommendations",
            router_bypass_or_continue,
            {
                "bypass": "save_template_sections",
                "continue": "campaign_intent_synthesizer",
            }
        )

        # Build subgraphs
        # Template Generation: campaign_intent_synthesizer → ... → section_retrieval_start
        # Entry is campaign_intent_synthesizer (on cache miss only)
        # The last node of this subgraph is section_retrieval_start.
        build_template_generation_subgraph(
            graph,
            entry_node="campaign_intent_synthesizer",
            exit_node="section_retrieval_start"
        )

        # Section Retrieval: ... → cache_template_recommendations → save_template_sections
        # In this case, the edge is defined twice, template_generation_subgraph and section_retrieval_subgraph 
        # define the edge from generate_template_structures to section_retrieval_start, one at the entry and one 
        # at the exit. The section retrieval start node is defined in build_section_retrieval_subgraph.
        build_section_retrieval_subgraph(
            graph,
            entry_node="section_retrieval_start",
            exit_node="save_template_sections",
        )

        # save_template_sections: section retrieval exits here; post_processing starts here.
        graph.add_node("save_template_sections", save_generation_template_sections_node)

        # Post-Processing: save_template_sections → template_compilation → ... → END
        # This implicity defines the end of the graph.
        build_post_processing_subgraph(
            graph,
            entry_node="save_template_sections"
        )
        
        logger.info("Built TemplateSelectionWorkflow graph")
        
        return graph.compile(
            checkpointer=self.checkpointer,
            cache=self.cache
        )
