# agent_workflows/landing_page_builder/trade_classification_workflow.py
"""
Trade Classification Workflow.

Lightweight workflow for quick industry/trade classification only.

Graph Structure:
    START → business_data_extractor → trade_classifier → END
"""

from langgraph.graph import StateGraph, START, END


from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState

from wwai_agent_orchestration.nodes.landing_page_builder.business_intelligence.business_data_extractor import business_data_extractor_node
from wwai_agent_orchestration.nodes.landing_page_builder.business_intelligence.trade_classifier_node import trade_classifier_node

from wwai_agent_orchestration.agent_workflows.landing_page_builder.cache import create_node_cache_policy
from wwai_agent_orchestration.agent_workflows.landing_page_builder.workflows.base_workflow import BaseLandingPageWorkflow

from wwai_agent_orchestration.core.observability.logger import get_logger
logger = get_logger(__name__)


class TradeClassificationWorkflow(BaseLandingPageWorkflow):
    """
    Lightweight workflow for trade classification only.
    
    Graph Structure:
        START → business_data_extractor → trade_classifier → END
    
    Use case: Quick industry/trade classification without template generation.
    Runs business data extraction (Google Places, Yelp) then trade classification.
    """
    
    workflow_name = "trade_classification"
    
    def _build_graph(self) -> StateGraph:
        """Build minimal graph for trade classification."""
        
        graph = StateGraph(LandingPageWorkflowState)
        
        # Add nodes
        graph.add_node(
            "business_data_extractor",
            business_data_extractor_node,
            cache_policy=create_node_cache_policy("business_data_extractor"),
        )
        graph.add_node("trade_classifier", trade_classifier_node)
        
        # Wire the graph
        graph.add_edge(START, "business_data_extractor")
        graph.add_edge("business_data_extractor", "trade_classifier")
        graph.add_edge("trade_classifier", END)
        
        logger.info("Built TradeClassificationWorkflow graph")
        
        return graph.compile(
            checkpointer=self.checkpointer,
            cache=self.cache
        )
