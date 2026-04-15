# nodes/smb/autopop/content_nodes/text/collect.py
"""
Content text collect node.

Collects results from all parallel section content text nodes.
"""

from typing import Any, Dict
from langgraph.types import RunnableConfig

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils import autopop_helpers


@NodeRegistry.register(
    name="content_text_collect",
    description="Collect results from all parallel section content text nodes",
    max_retries=1,
    timeout=90,
    tags=["autopopulation", "collect", "content", "text"],
    display_name="Combining text content",
    show_node=False,
    show_output=False,
)
def content_text_collect(state: LandingPageWorkflowState, config: RunnableConfig = None) -> Dict[str, Any]:
    """Collect results from all parallel section content text nodes."""
    # Results are automatically merged by LangGraph's state reducer
    delta = {
        "logs": [{"level": "info", "msg": "content_text: all sections completed"}],
        "meta": {"last_node": "content_text_collect"},
    }
    return autopop_helpers.update_autopop_state(state, delta)
