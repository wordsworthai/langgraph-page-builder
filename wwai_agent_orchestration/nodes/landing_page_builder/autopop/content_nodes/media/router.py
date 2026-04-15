# nodes/smb/autopop/content_nodes/media/router.py
"""
Content media router node and conditional edge function.

Routes to either:
- Parallel path: fan-out to section-level agents (one section per node)
- Template-level path: single node processing all sections together (enables deduplication)
"""

from typing import Literal, Dict, Any
from langgraph.types import RunnableConfig

from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils import autopop_helpers


def content_media_router_node(
    state: LandingPageWorkflowState, 
    config: RunnableConfig = None
) -> Dict[str, Any]:
    """
    Router node that passes through state (used for observability/logging).
    
    The actual routing decision is made by content_media_router_condition.
    
    Args:
        state: LandingPageWorkflowState
        config: Optional configuration
        
    Returns:
        Empty dict (pass-through node)
    """
    return {}


def content_media_router_condition(
    state: LandingPageWorkflowState, 
    config: RunnableConfig = None
) -> Literal["parallel", "template_level"]:
    """
    Conditional edge function that routes to either parallel or template-level processing.
    
    Args:
        state: LandingPageWorkflowState
        config: Optional configuration
        
    Returns:
        "parallel" or "template_level"
    """
    autopop_state = autopop_helpers.get_autopop_state(state)
    
    # Check for routing configuration in state
    # Default to template_level for deduplication benefits
    use_template_level = autopop_state.get("config", {}).get(
        "use_template_level_media_processing", 
        True  # Default to template-level for deduplication
    )
    
    if use_template_level:
        return "template_level"
    else:
        return "parallel"


# Alias for backward compatibility / convenience
content_media_router = content_media_router_condition


def content_media_template_level_router(
    state: LandingPageWorkflowState, 
    config: RunnableConfig = None
) -> Dict[str, Any]:
    """Dummy router node that passes through to enable parallel execution of image and video nodes."""
    # Return empty dict - just a pass-through node
    return {}
