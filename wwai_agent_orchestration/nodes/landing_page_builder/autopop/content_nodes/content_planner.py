# nodes/smb/autopop/content_nodes/content_planner.py
"""
Content planner node.

Plans content generation strategy for both text and media pipelines.
"""

from typing import Any, Dict
from langgraph.types import RunnableConfig

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.utils.landing_page_builder.ui_logs import (
    content_planner_html,
    make_ui_execution_log_entry_from_registry,
)


@NodeRegistry.register(
    name="content_planner",
    description="Plan content generation strategy for both text and media pipelines",
    max_retries=1,
    timeout=90,
    tags=["autopopulation", "content", "planning"],
    display_name="Planning content",
    show_node=True,
    show_output=False,
)
def content_planner(state: LandingPageWorkflowState, config: RunnableConfig = None) -> Dict[str, Any]:
    """Content planner node that prepares content generation strategy.
    
    This node will later implement content planning logic that feeds into both
    text and media content pipelines. For now, it's a pass-through node.
    
    Args:
        state: LandingPageWorkflowState
        config: Optional configuration
        
    Returns:
        Empty dict (pass-through for now)
    """
    # TODO: Implement content planning logic
    # For now, just pass through
    return {
        "ui_execution_log": [
            make_ui_execution_log_entry_from_registry("content_planner", content_planner_html())
        ],
    }
