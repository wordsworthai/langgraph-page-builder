# nodes/smb/autopop/final_snapshot.py
"""
Final snapshot node.

Creates a complete snapshot after all autopopulation pipelines (styles, text, media) have completed.
"""

from typing import Any, Dict
from langgraph.types import RunnableConfig

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils import autopop_helpers
from wwai_agent_orchestration.utils.landing_page_builder.ui_logs import (
    final_snapshot_html,
    make_ui_execution_log_entry_from_registry,
)
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils.template_materialize_utils import materialize_node


@NodeRegistry.register(
    name="final_snapshot",
    description="Create complete snapshot after all autopopulation pipelines (styles, text, media) have completed",
    max_retries=1,
    timeout=90,
    tags=["autopopulation", "snapshot", "final"],
    display_name="Finalizing content",
    show_node=True,
    show_output=False,
)
async def final_snapshot(state: LandingPageWorkflowState, config: RunnableConfig = None) -> Dict[str, Any]:
    """Final snapshot node that runs after all pipelines (styles, text, media) have completed."""
    autopop_state = autopop_helpers.get_autopop_state(state)
    materialize_config = autopop_helpers.build_materialize_config(
        state=state,
        config=config,
        autopop_state=autopop_state,
        label="final_autopopulation"
    )
    delta = await materialize_node(
        autopop_state,
        config=materialize_config,
    )
    delta.setdefault("logs", []).append({"level": "info", "msg": "final_snapshot: complete autopopulation snapshot created"})
    delta.setdefault("meta", {}).update({"last_node": "final_snapshot"})

    # Clean up immutable store after use (final_snapshot is the last node that reads it)
    run_id = (
        (autopop_state.get("immutable_ref") or {}).get("run_id")
        or (autopop_state.get("meta") or {}).get("run_id")
    )
    if run_id:
        store = autopop_helpers.get_store()
        await store.delete(run_id)

    result = autopop_helpers.update_autopop_state(state, delta)
    result["ui_execution_log"] = [
        make_ui_execution_log_entry_from_registry("final_snapshot", final_snapshot_html())
    ]
    return result
