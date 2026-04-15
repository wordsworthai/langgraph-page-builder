# nodes/smb/autopop/content_nodes/html/content_html_snapshot.py
"""
Content HTML snapshot node.

Creates snapshot after content HTML agent has completed.
"""

from typing import Any, Dict
from langgraph.types import RunnableConfig

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils import autopop_helpers
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils.template_materialize_utils import materialize_node


@NodeRegistry.register(
    name="content_html_snapshot",
    description="Create snapshot after content HTML agent has completed",
    max_retries=1,
    timeout=90,
    tags=["autopopulation", "snapshot", "content", "html"],
    display_name="Saving HTML content",
    show_node=False,
    show_output=False,
)
async def content_html_snapshot(
    state: LandingPageWorkflowState, config: RunnableConfig = None
) -> Dict[str, Any]:
    """Create snapshot after content HTML agent has completed."""
    autopop_state = autopop_helpers.get_autopop_state(state)
    materialize_config = autopop_helpers.build_materialize_config(
        state=state,
        config=config,
        autopop_state=autopop_state,
        label="content_html",
    )
    delta = await materialize_node(
        autopop_state,
        config=materialize_config,
    )
    delta.setdefault("logs", []).append(
        {"level": "info", "msg": "content_html_snapshot: snapshot created"}
    )
    delta.setdefault("meta", {}).update({"last_node": "content_html_snapshot"})
    return autopop_helpers.update_autopop_state(state, delta)
