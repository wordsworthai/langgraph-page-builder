# nodes/smb/autopop/content_nodes/media/collect.py
"""
Content media collect node.

Collects results from all parallel section media content nodes.
"""

from typing import Any, Dict
from langgraph.types import RunnableConfig

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils import autopop_helpers


@NodeRegistry.register(
    name="content_media_collect",
    description="Collect results from all parallel section content media nodes",
    max_retries=1,
    timeout=90,
    tags=["autopopulation", "collect", "content", "media"],
    display_name="Combining media content",
    show_node=False,
    show_output=False,
)
def content_media_collect(state: LandingPageWorkflowState, config: RunnableConfig = None) -> Dict[str, Any]:
    """Collect results from all parallel section media content nodes."""
    # Results are automatically merged by LangGraph's state reducer
    delta = {
        "logs": [{"level": "info", "msg": "content_media: all sections completed"}],
        "meta": {"last_node": "content_media_collect"},
    }
    return autopop_helpers.update_autopop_state(state, delta)
