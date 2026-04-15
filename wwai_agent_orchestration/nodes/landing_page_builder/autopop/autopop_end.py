# nodes/smb/autopop/autopop_end.py
"""
Autopop End Node - Exit node for autopopulation subgraph.

Dummy pass-through node that marks the end of the autopopulation subgraph.
Immutable store cleanup is done in final_snapshot (the last node that reads it).
"""

from typing import Dict, Any, Optional
from langgraph.types import RunnableConfig

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.utils.landing_page_builder.ui_logs import (
    autopop_end_html,
    make_ui_execution_log_entry_from_registry,
)

logger = get_logger(__name__)


@NodeRegistry.register(
    name="autopop_end",
    description="Exit node for autopopulation subgraph (dummy pass-through)",
    max_retries=0,
    timeout=1,
    tags=["autopopulation", "subgraph", "end"],
    display_name="Completing website",
    show_node=True,
    show_output=False,
)
async def autopop_end_node(
    state: LandingPageWorkflowState,
    config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """Exit node for autopopulation subgraph. Pass-through only."""
    logger.debug(
        "Autopopulation subgraph completed",
        node="autopop_end",
        business_name=state.input.business_name if state.input else None
    )
    ui_output_html = autopop_end_html()
    return {
        "ui_execution_log": [
            make_ui_execution_log_entry_from_registry("autopop_end", ui_output_html)
        ],
    }
