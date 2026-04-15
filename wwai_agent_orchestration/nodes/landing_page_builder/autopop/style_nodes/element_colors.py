# nodes/smb/autopop/style_nodes/element_colors.py
"""
Element colors collection and snapshot nodes.

Contains:
- element_colors_collect: Collects results from all parallel element color agents
- element_colors_snapshot: Creates snapshot after all element colors are collected
"""

from typing import Any, Dict
from langgraph.types import RunnableConfig

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils import autopop_helpers
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils.template_materialize_utils import materialize_node


@NodeRegistry.register(
    name="element_colors_collect",
    description="Collect results from all parallel element color agents (text, button, misc)",
    max_retries=1,
    timeout=90,
    tags=["autopopulation", "collect", "style"],
    display_name="Combining color choices",
    show_node=False,
    show_output=False,
)
def element_colors_collect(state: LandingPageWorkflowState, config: RunnableConfig = None) -> Dict[str, Any]:
    """Collect results from all parallel element color agents."""
    # Results are automatically merged by LangGraph's state reducer
    delta = {
        "logs": [{"level": "info", "msg": "element_colors: all color agents completed"}],
        "meta": {"last_node": "element_colors_collect"},
    }
    return autopop_helpers.update_autopop_state(state, delta)


@NodeRegistry.register(
    name="element_colors_snapshot",
    description="Create snapshot after all element colors are collected",
    max_retries=1,
    timeout=90,
    tags=["autopopulation", "snapshot", "style"],
    display_name="Saving element colors",
    show_node=False,
    show_output=False,
)
async def element_colors_snapshot(state: LandingPageWorkflowState, config: RunnableConfig = None) -> Dict[str, Any]:
    """Create snapshot after all element colors are collected."""
    autopop_state = autopop_helpers.get_autopop_state(state)
    materialize_config = autopop_helpers.build_materialize_config(
        state=state,
        config=config,
        autopop_state=autopop_state,
        label="element_colors"
    )
    delta = await materialize_node(
        autopop_state,
        config=materialize_config,
    )
    delta.setdefault("logs", []).append({"level": "info", "msg": "element_colors_snapshot: snapshot created"})
    delta.setdefault("meta", {}).update({"last_node": "element_colors_snapshot"})
    return autopop_helpers.update_autopop_state(state, delta)
