# nodes/smb/autopop/content_nodes/media/snapshot.py
"""
Content media snapshot node.

Creates snapshot after all content media sections are collected.
"""

from typing import Any, Dict
from langgraph.types import RunnableConfig

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils import autopop_helpers
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils.template_materialize_utils import materialize_node
from wwai_agent_orchestration.utils.landing_page_builder.ui_logs import (
    content_media_finalized_html,
    make_ui_execution_log_entry_from_registry,
)


@NodeRegistry.register(
    name="content_media_snapshot",
    description="Create snapshot after all content media sections are collected",
    max_retries=1,
    timeout=90,
    tags=["autopopulation", "snapshot", "content", "media"],
    display_name="Finalizing media",
    show_node=True,
    show_output=False,
)
async def content_media_snapshot(state: LandingPageWorkflowState, config: RunnableConfig = None) -> Dict[str, Any]:
    """Create snapshot after all content media sections are collected."""
    autopop_state = autopop_helpers.get_autopop_state(state)
    materialize_config = autopop_helpers.build_materialize_config(
        state=state,
        config=config,
        autopop_state=autopop_state,
        label="content_media"
    )
    delta = await materialize_node(
        autopop_state,
        config=materialize_config,
    )
    delta.setdefault("logs", []).append({"level": "info", "msg": "content_media_snapshot: snapshot created"})
    delta.setdefault("meta", {}).update({"last_node": "content_media_snapshot"})
    result = autopop_helpers.update_autopop_state(state, delta)
    result["ui_execution_log"] = [
        make_ui_execution_log_entry_from_registry("content_media_snapshot", content_media_finalized_html())
    ]
    return result
