# nodes/smb/planner_node.py
"""
Planner Node - First node in the workflow (pass-through).

This is the FIRST node in the full workflow.
Logs the start and passes through to business_data_extractor.
"""

from typing import Dict, Any, Optional
from langgraph.types import RunnableConfig

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState


logger = get_logger(__name__)


@NodeRegistry.register(
    name="planner_node",
    description="First node - pass-through to business_data_extractor",
    max_retries=0,
    tags=["routing", "planner"],
    display_name="Planning workflow",
    show_node=False,
    show_output=False,
)
def planner_node(state: LandingPageWorkflowState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """
    Pass-through node. Logs workflow start and returns empty dict.

    Args:
        state: LandingPageWorkflowState
        config: Node configuration (unused)

    Returns:
        Empty dict
    """
    logger.info(
        "Planner pass-through",
        node="planner_node",
        business_name=state.input.business_name if state.input else None,
    )
    return {}
