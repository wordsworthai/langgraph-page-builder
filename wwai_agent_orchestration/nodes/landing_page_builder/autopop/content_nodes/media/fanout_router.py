# nodes/smb/autopop/content_nodes/media/fanout_router.py
"""
Content media fanout router node.

Dummy router node that passes through to fan-out conditional edge.
"""

from typing import Any, Dict
from langgraph.types import RunnableConfig

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState


@NodeRegistry.register(
    name="content_media_fanout_router",
    description="Router node that passes through to fan-out parallel content media section agents",
    max_retries=1,
    timeout=90,
    tags=["autopopulation", "content", "media", "routing"],
    display_name="Starting media generation",
    show_node=False,
    show_output=False,
)
def content_media_fanout_router(state: LandingPageWorkflowState, config: RunnableConfig = None) -> Dict[str, Any]:
    """Dummy router node that passes through to fan-out."""
    # Return empty dict - the conditional edge function will handle the fan-out
    return {}
