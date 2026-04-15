# nodes/smb/autopop/autopop_start.py
"""
Autopop Start Node - Dummy entry node for autopopulation subgraph.

This is a placeholder node that marks the start of the autopopulation subgraph.
It simply passes through the state unchanged.
"""

from typing import Dict, Any, Optional
from langgraph.types import RunnableConfig

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.utils.landing_page_builder.ui_logs import (
    autopop_start_html,
    make_ui_execution_log_entry_from_registry,
)

logger = get_logger(__name__)


@NodeRegistry.register(
    name="autopop_start",
    description="Entry node for autopopulation subgraph (dummy pass-through)",
    max_retries=0,
    timeout=1,
    tags=["autopopulation", "subgraph", "start"],
    display_name="Starting content population",
    show_node=True,
    show_output=False,
)
def autopop_start_node(
    state: LandingPageWorkflowState,
    config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """
    Dummy start node for autopopulation subgraph.
    
    Simply passes through the state unchanged.
    
    Args:
        state: LandingPageWorkflowState
        config: Node configuration
        
    Returns:
        Empty dict (no state changes)
    """
    logger.debug(
        "Autopopulation subgraph started",
        node="autopop_start",
        business_name=state.input.business_name if state.input else None,
    )
    
    ui_output_html = autopop_start_html()
    return {
        "ui_execution_log": [
            make_ui_execution_log_entry_from_registry("autopop_start", ui_output_html)
        ],
    }
