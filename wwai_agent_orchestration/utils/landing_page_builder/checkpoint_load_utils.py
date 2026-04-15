"""
Utilities for loading checkpoint state from LangGraph workflows.

This module provides functions to find and load checkpoint states
from the checkpoint history, useful for debugging and testing nodes.
"""
import os
from typing import Dict, Any, List, Literal, Optional

from wwai_agent_orchestration.core.database import db_manager
from wwai_agent_orchestration.utils.checkpoint.checkpoint_utils import fetch_full_checkpoint_history

WorkflowType = Literal[
    "trade_classification",
    "template_selection",
    "landing_page",
    "partial_autopop",
    "preset_sections",
    "regenerate_section",
]


def _get_checkpoint_db():
    return db_manager.get_database("checkpointing_db")


def find_checkpoint_id_before_node(history: List[Dict[str, Any]], target_node: str) -> str:
    """Find the checkpoint ID just before a target node in the checkpoint history."""
    if not history:
        raise ValueError("No checkpoints in history")
    target_checkpoint_id = None
    for i, entry in enumerate(history):
        node_name = entry.get("node_name")
        if node_name == target_node:
            if i > 0:
                target_checkpoint_id = history[i - 1]["checkpoint_id"]
            else:
                target_checkpoint_id = history[0]["checkpoint_id"]
            print(f"   Found {target_node} at step {i}, using checkpoint before it")
            break
    if not target_checkpoint_id:
        print(f"   Warning: Node '{target_node}' not found. Using last checkpoint.")
        for entry in reversed(history):
            if entry.get("node_name") != target_node:
                target_checkpoint_id = entry["checkpoint_id"]
                break
    if not target_checkpoint_id:
        target_checkpoint_id = history[-1]["checkpoint_id"]
    print(f"   Using checkpoint: {target_checkpoint_id[:16]}...")
    return target_checkpoint_id


def _workflow_type_to_factory_mode(workflow_type: str) -> str:
    """Map workflow_name from config to factory mode."""
    mapping = {
        "landing_page": "full",
        "landing_page_recommendation": "full",
        "landing_page_builder": "full",
        "partial_autopop": "partial_autopop",
        "preset_sections": "preset_sections",
        "use-section-ids": "preset_sections",
        "regenerate_section": "regenerate_section",
    }
    return mapping.get(workflow_type, "full")


def get_final_checkpoint_state(
    thread_id: str,
    workflow_type: WorkflowType = "landing_page",
    workflow_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Get the final checkpoint state from a completed workflow."""
    history = fetch_full_checkpoint_history(db=_get_checkpoint_db(), thread_id=thread_id)
    if not history:
        raise ValueError(f"No checkpoints found for thread_id: {thread_id}")
    final_checkpoint_id = history[-1]["checkpoint_id"]
    from wwai_agent_orchestration.agent_workflows.landing_page_builder.workflows.workflow_factory import (
        LandingPageWorkflowFactory,
    )

    factory_mode = _workflow_type_to_factory_mode(workflow_name or workflow_type)
    workflow_config = {
        "rapidapi_key": os.getenv("RAPIDAPI_KEY"),
        "rapidapi_host": os.getenv("RAPIDAPI_HOST"),
        "section_repo_query_filter": {"status": "ACTIVE", "tag": "smb"},
    }
    workflow = LandingPageWorkflowFactory.create(
        factory_mode,
        config=workflow_config,
        regenerate_mode="all" if factory_mode == "partial_autopop" else None,
    )
    config = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_id": final_checkpoint_id,
            **workflow.config,
        }
    }
    state_obj = workflow.graph.get_state(config)
    if state_obj and state_obj.values:
        return state_obj.values
    raise ValueError(f"Could not retrieve state from final checkpoint {final_checkpoint_id}")


def get_checkpoint_state_before_node(
    thread_id: str,
    target_node: str,
    workflow_type: WorkflowType = "landing_page",
    workflow_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Get the checkpoint state just before a specific node executes."""
    history = fetch_full_checkpoint_history(db=_get_checkpoint_db(), thread_id=thread_id)
    if not history:
        raise ValueError(f"No checkpoints found for thread_id: {thread_id}")
    target_checkpoint_id = find_checkpoint_id_before_node(history, target_node)
    from wwai_agent_orchestration.agent_workflows.landing_page_builder.workflows.workflow_factory import (
        LandingPageWorkflowFactory,
    )

    factory_mode = _workflow_type_to_factory_mode(workflow_name or workflow_type)
    workflow_config = {
        "rapidapi_key": os.getenv("RAPIDAPI_KEY"),
        "rapidapi_host": os.getenv("RAPIDAPI_HOST"),
        "section_repo_query_filter": {"status": "ACTIVE", "tag": "smb"},
    }
    workflow = LandingPageWorkflowFactory.create(
        factory_mode,
        config=workflow_config,
        regenerate_mode="all" if factory_mode == "partial_autopop" else None,
    )
    config = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_id": target_checkpoint_id,
            **workflow.config,
        }
    }
    state_obj = workflow.graph.get_state(config)
    if state_obj and state_obj.values:
        return state_obj.values
    raise ValueError(f"Could not retrieve state from checkpoint {target_checkpoint_id}")
