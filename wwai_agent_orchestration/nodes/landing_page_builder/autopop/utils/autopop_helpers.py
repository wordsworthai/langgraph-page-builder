# agent_workflows/landing_page_builder/autopop_helpers.py
"""
Helper functions for autopopulation subgraph nodes.

These helpers are shared across all pipeline nodes.

ASYNC PATTERN: Functions that call async operations are marked 'async'.
LangGraph natively supports async nodes - just use 'await' directly.
"""

from typing import Any, Dict
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.utils.landing_page_builder.immutable_store import immutable_store
from template_json_builder.autopopulation.autopopulators.graph_state import AutopopulationLangGraphAgentsState
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils.template_materialize_utils import _load_immutable as _load_immutable_for_agents
from template_json_builder.autopopulation.autopopulators.module_registry.types import RegistryProfile


def get_store():
    """Return the singleton immutable store used by all autopop nodes."""
    return immutable_store


def get_autopop_state(state: LandingPageWorkflowState) -> AutopopulationLangGraphAgentsState:
    """Extract autopopulation_langgraph_state from LandingPageWorkflowState."""
    if state.autopopulation_langgraph_state is None:
        raise ValueError("autopopulation_langgraph_state must be initialized by autopopulation_input_builder_node")
    return state.autopopulation_langgraph_state


def update_autopop_state(state: LandingPageWorkflowState, delta: Dict[str, Any]) -> Dict[str, Any]:
    """Merge delta into autopopulation_langgraph_state and return update dict."""
    current = get_autopop_state(state)
    # Merge delta into current state (deep merge handled by reducer)
    updated = {**current, **delta}
    return {"autopopulation_langgraph_state": updated}


async def resolve_imm(
    autopop_state: AutopopulationLangGraphAgentsState,
    config: Dict[str, Any] = None,
    full_state: LandingPageWorkflowState = None,
):
    """
    Resolve immutable state from autopopulation state (async). Uses singleton store.
    When immutable is missing (e.g. retry on different worker):
    - If full_state is provided: builds from state (same as autopopulation_input_builder).
    - Else: restores from checkpoint (for section agents with only Send payload).
    """
    cfg = {"store": get_store()}
    if config:
        cfg["configurable"] = config.get("configurable", {})
    return await _load_immutable_for_agents(autopop_state, cfg, full_state=full_state)


def use_mock(autopop_state: AutopopulationLangGraphAgentsState) -> bool:
    """Check if mock mode is enabled."""
    return bool(autopop_state.get("meta", {}).get("use_mock", False))


def brand_url(autopop_state: AutopopulationLangGraphAgentsState) -> str:
    """Get brand URL from autopop state."""
    return autopop_state.get("brand_url", "")


def entity_url(autopop_state: AutopopulationLangGraphAgentsState) -> str:
    """Get entity URL from autopop state."""
    return autopop_state.get("entity_url", "")


def build_materialize_config(
    state: LandingPageWorkflowState,
    config: Dict[str, Any],
    autopop_state: AutopopulationLangGraphAgentsState,
    label: str
) -> Dict[str, Any]:
    """
    Build config for materialize_node with generation_version_id and database settings.
    
    Args:
        state: LandingPageWorkflowState containing generation_version_id
        config: Parent config from LangGraph (may contain configurable.thread_id)
        autopop_state: AutopopulationLangGraphAgentsState
        label: Materialize label (e.g., "S1_container_color")
    
    Returns:
        Config dict for materialize_node
    """
    config = config or {}
    
    # Get generation_version_id from config or state.input (nested state)
    state_gen_id = None
    if getattr(state, "input", None):
        state_gen_id = getattr(state.input, "generation_version_id", None)
    generation_version_id = config.get("configurable", {}).get("thread_id") or state_gen_id
    
    # Build materialize config with all necessary fields (uses singleton store)
    return {
        "store": get_store(),
        "registry_profile_override": RegistryProfile.REAL_POPULATION,
        "stage": "FINAL_APPLY",
        "label": label,
        "agent_outputs_override": autopop_state.get("agent_outputs", {}),
        "is_dev_mode": autopop_state.get("is_dev_mode", False),
        # Pass full state for build-from-state on retry (when store is empty)
        "full_state": state,
        # Pass through configurable.thread_id for generation_version_id
        "configurable": {
            **config.get("configurable", {}),
            "thread_id": generation_version_id or config.get("configurable", {}).get("thread_id")
        },
        # Pass through database settings
        "enable_database_save": config.get("enable_database_save", True),
        "save_database_name": config.get("save_database_name", "template_generation"),
    }
