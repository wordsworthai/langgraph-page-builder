# graph_materialize_node.py
from __future__ import annotations
import json
from datetime import datetime
from hashlib import sha256
from typing import Any, Dict, List, Optional, Tuple

from template_json_builder.autopopulation.autopopulators.graph_state import (
    AutopopulationLangGraphAgentsState,
    StageKey, SnapshotLabel,
)
from template_json_builder.autopopulation.autopopulators.template_autopopulator import TemplateAutopopulator
from template_json_builder.autopopulation.autopopulators.module_registry.types import RegistryProfile
from template_json_builder.build_langgraph_input import build_langgraph_input

from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.core.database import db_manager
from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils.autopop_input_utils import (
    get_palette_and_fonts_input,
    get_section_ids_from_resolved_template_recommendations,
    get_use_mock_autopopulation,
)
from wwai_agent_orchestration.utils.landing_page_builder.checkpoint_load_utils import (
    get_final_checkpoint_state,
)
from wwai_agent_orchestration.utils.landing_page_builder.template.db_service import template_db_service
from wwai_agent_orchestration.utils.landing_page_builder.template.template_json_sources import (
    get_template_json_from_generated_templates,
)

logger = get_logger(__name__)

def _utc_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

def _coerce_registry(value: Optional[object]) -> Optional[RegistryProfile]:
    """Accept RegistryProfile or str (name/value); return RegistryProfile or None."""
    if value is None:
        return None
    if isinstance(value, RegistryProfile):
        return value
    if isinstance(value, str):
        try:
            return RegistryProfile[value]  # e.g. "RECREATE_POPULATION"
        except Exception:
            try:
                return RegistryProfile(value)  # e.g. "recreate_population"
            except Exception:
                raise ValueError(f"Unknown registry profile: {value!r}")
    raise TypeError(f"registry_profile must be RegistryProfile | str | None, got {type(value)}")


def _resolve_stage_and_label(
    state: AutopopulationLangGraphAgentsState,
    config: Dict[str, Any],
) -> tuple[StageKey, SnapshotLabel]:
    meta = state.get("meta") or {}
    stage = config.get("stage") or meta.get("next_stage") or "START"
    label = config.get("label") or meta.get("next_label") or "T0_start"
    logger.info(f"Resolved stage and label: {stage} {label}")
    return stage, label  # type: ignore[return-value]


def _get_registry_override(
    state: AutopopulationLangGraphAgentsState, 
    config: Dict[str, Any]
) -> Optional[RegistryProfile]:
    # precedence: config override > state.meta override
    raw = config.get("registry_profile_override")
    if raw is None:
        raw = (state.get("meta") or {}).get("registry_profile_override")
    return _coerce_registry(raw) if raw is not None else None


def _resolve_section_ids_and_template_map(
    state: LandingPageWorkflowState,
    workflow_name: str,
    workflow_params: Dict[str, Any],
    run_id: str,
) -> Optional[Tuple[List[str], Dict[str, str]]]:
    """
    Resolve section_ids and template_map from state (same logic as autopopulation_input_builder).
    Returns (section_ids, template_map) or None on failure.
    """
    if workflow_name == "regenerate_section" and workflow_params.get("section_id"):
        section_id = workflow_params["section_id"]
        section_index = workflow_params.get("section_index", 0)
        full_map = state.template_unique_section_id_map or {}
        exact_key = f"{section_id}_{section_index}"
        template_json_stable_key = full_map.get(exact_key)
        if not template_json_stable_key:
            logger.warning(
                f"Build immutable from state: section_id not in template map, run_id={run_id}",
            )
            return None
        return ([section_id], {f"{section_id}_0": template_json_stable_key})
    section_ids = get_section_ids_from_resolved_template_recommendations(state)
    template_map = state.template_unique_section_id_map
    if not template_map:
        logger.warning(
            f"Build immutable from state: template_unique_section_id_map missing, run_id={run_id}",
        )
        return None
    return (section_ids, template_map)


def _resolve_populated_override(
    workflow_name: str,
    workflow_params: Dict[str, Any],
    run_id: str,
) -> Tuple[bool, Optional[Tuple[Any, Any]]]:
    """
    For partial_autopop, fetch populated template from source thread.
    Returns (success, value): (True, None) = no override, (True, (json, mapping)) = override,
    (False, None) = failed (caller should abort).
    """
    source_thread_id = workflow_params.get("source_thread_id")
    if workflow_name != "partial_autopop" or not source_thread_id:
        return (True, None)
    populated_json, populated_mapping = get_template_json_from_generated_templates(
        source_thread_id
    )
    if populated_json is None or populated_mapping is None:
        logger.warning(
            f"Build immutable from state: partial_autopop missing template from source, run_id={run_id}",
        )
        return (False, None)
    return (True, (populated_json, populated_mapping))


async def _build_immutable_from_state(
    state: Any,
    run_id: str,
    store: Any,
    config: Dict[str, Any],
) -> Optional[Any]:
    """
    Build immutable from state (same logic as autopopulation_input_builder).
    Used when store is empty but the caller has full state (already restored by LangGraph).
    Returns the immutable or None if build fails.
    """
    try:
        if not isinstance(state, LandingPageWorkflowState):
            state = LandingPageWorkflowState.from_restored_state(
                state if isinstance(state, dict) else {},
                generation_version_id=run_id,
            )

        configurable = config.get("configurable") or {}
        workflow_name = configurable.get("workflow_name", "landing_page")
        workflow_params = configurable.get("workflow_params") or {}

        resolved = _resolve_section_ids_and_template_map(
            state, workflow_name, workflow_params, run_id
        )
        if resolved is None:
            return None
        section_ids, template_map = resolved

        use_mock = get_use_mock_autopopulation(state.execution_config)
        palette_and_fonts_input = get_palette_and_fonts_input(state)

        ok, populated_override = _resolve_populated_override(
            workflow_name, workflow_params, run_id
        )
        if not ok:
            return None

        await build_langgraph_input(
            section_id_list=section_ids,
            mongo_client=db_manager.client,
            store=store,
            run_id=run_id,
            bypass_prompt_cache=False,
            is_dev_mode=False,
            extra_meta={"use_mock": use_mock},
            palette_and_fonts_input=palette_and_fonts_input,
            template_unique_section_id_map=template_map,
            populated_template_json_override=populated_override,
        )

        imm = await store.get(run_id)
        if imm is not None:
            logger.info(
                f"Built immutable from state on demand (store was empty), run_id={run_id}",
            )
            return imm
    except Exception as e:
        logger.warning(
            f"Failed to build immutable from state, run_id={run_id}: {e}",
        )
    return None


async def _restore_immutable_from_checkpoint(
    run_id: str,
    store: Any,
    config: Dict[str, Any],
) -> Optional[Any]:
    """
    Fallback: restore from checkpoint when caller has no full state (e.g. section agents
    with only Send payload). Uses get_final_checkpoint_state then _build_immutable_from_state.
    """
    try:
        restored_state = get_final_checkpoint_state(
            thread_id=run_id,
            workflow_name=config.get("configurable", {}).get("workflow_name"),
        )
        return await _build_immutable_from_state(
            state=restored_state,
            run_id=run_id,
            store=store,
            config=config,
        )
    except Exception as e:
        logger.warning(
            f"Failed to restore immutable from checkpoint, run_id={run_id}: {e}",
        )
    return None


async def _load_immutable(
    state: AutopopulationLangGraphAgentsState,
    config: Dict[str, Any],
    full_state: Any = None,
):
    """
    Support both shapes:
      - embedded: state["immutable"] is a JSON dict → reconstruct via Pydantic
      - pointer:  state["immutable_ref"] + store (config["store"] or singleton)

    When store.get returns None (e.g. retry on different worker):
    - If full_state provided: builds from state (same as autopopulation_input_builder).
    - Else: restores from checkpoint (for section agents with only Send payload).
    """
    # Store is empty when: (1) Retry on a different worker—InProcImmutableStore is in-memory
    # per process, so the retry worker never saw the write from autopopulation_input_builder.
    # (2) Checkpoint resume—LangGraph skips autopopulation_input_builder (it already ran), so
    # the immutable was never written to this worker's store. We build/restore on demand instead
    # of raising, so retries and checkpoint resumes succeed.
    # cfg: store + configurable (workflow_name, workflow_params, thread_id). Needed for store
    # lookup and for build/restore logic when store is empty.
    # full_state: When store is empty, we prefer building from the node's already-restored state
    # (same as autopopulation_input_builder) instead of reading checkpoint. Pass full_state when
    # the caller has LandingPageWorkflowState (fanouts, style nodes, media_data_context_fetcher,
    # content_html_agent, template_level_image/video, materialize_node). Do NOT pass full_state
    # for section agents (content_text_section_agent, content_media_section_agent)—they only
    # receive the Send payload (section_id, immutable_ref, meta), so we fall back to checkpoint.

    # pointer path (preferred at scale)
    imm_ref = state.get("immutable_ref") or {}
    run_id = imm_ref.get("run_id") or (state.get("meta") or {}).get("run_id")
    if not run_id:
        raise RuntimeError("No run_id found in state. Provide state['immutable'] or state['immutable_ref']['run_id'].")

    store = config.get("store")
    if store is None:
        from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils import autopop_helpers
        store = autopop_helpers.get_store()
    imm = await store.get(run_id)
    if imm is None:
        if full_state is not None:
            imm = await _build_immutable_from_state(full_state, run_id, store, config)
        if imm is None:
            imm = await _restore_immutable_from_checkpoint(run_id, store, config)
    if imm is None:
        raise RuntimeError(f"Immutable not found in store for run_id={run_id}")
    return imm


def _save_snapshots_to_database(
    state: AutopopulationLangGraphAgentsState,
    config: Dict[str, Any],
    delta: Dict[str, Any],
    stage: Optional[str] = None,
    label: Optional[str] = None,
    errors: Optional[list] = None
) -> None:
    """
    Save snapshots, meta, logs, and errors to database.
    
    Args:
        state: Current autopopulation state
        config: Configuration dict with database settings
        delta: Delta containing snapshots, meta, logs to merge
        stage: Optional stage name (for success case)
        label: Optional label name (for success case)
        errors: Optional errors list (for error case)
    
    Raises:
        ValueError: If generation_version_id not found
        Exception: If database save fails (logged but not re-raised)
    """
    if not config.get('enable_database_save', True):
        return
    
    try:
        # Extract generation_version_id from config (same pattern as other nodes)
        generation_version_id = (
            config.get("configurable", {}).get("thread_id") or 
            state.get("generation_version_id")
        )
        
        if not generation_version_id:
            raise ValueError("generation_version_id not found in config or state")
        
        # Build document based on whether this is success or error case
        if errors is not None:
            # Error case: save errors and logs
            current_errors = state.get("errors", [])
            current_logs = state.get("logs", [])
            
            document = {
                "generation_version_id": generation_version_id,
                "errors": current_errors + errors,
                "logs": current_logs + delta.get("logs", []),
                "timestamp": _utc_iso(),
            }
        else:
            # Success case: merge current state with delta to get accumulated state
            current_snapshots = state.get("snapshots", {})
            current_meta = state.get("meta", {})
            current_logs = state.get("logs", [])
            
            # Merge snapshots (delta adds new snapshot)
            accumulated_snapshots = {**current_snapshots, **delta.get("snapshots", {})}
            
            # Merge meta (delta updates materialize section)
            accumulated_meta = {**current_meta, **delta.get("meta", {})}
            
            # Append logs (delta adds new logs)
            accumulated_logs = current_logs + delta.get("logs", [])
            
            document = {
                "generation_version_id": generation_version_id,
                "snapshots": accumulated_snapshots,
                "meta": accumulated_meta,
                "logs": accumulated_logs,
                "timestamp": _utc_iso(),
            }
            
            if stage:
                document["last_stage"] = stage
            if label:
                document["last_label"] = label
        
        # Save to database (uses save_database_name from config, defaults to 'template_generation')
        template_db_service.save_snapshot(
            generation_version_id=generation_version_id,
            document=document,
        )
    except Exception as save_error:
        # Log error but don't fail the node
        error_msg = (
            f"materialize_node: {config.get('label', 'unknown')} failed to save to database: {str(save_error)}"
            if errors is None
            else f"materialize_node: {config.get('label', 'unknown')} failed to save errors to database: {str(save_error)}"
        )
        raise RuntimeError(error_msg) from save_error


async def materialize_node(
    state: AutopopulationLangGraphAgentsState,
    config: Dict[str, Any] = {},
) -> Dict[str, Any]:
    """
    LangGraph node:
      - Loads immutable (embedded JSON or via store pointer)
      - Builds TemplateAutopopulator with current agent_outputs
      - Produces full artifact and writes a snapshot delta
      - Appends logs; records registry used in meta
    Returns a *delta* that LangGraph merges via your reducers.
    """
    logs: list[dict] = []
    errors: list[dict] = []

    try:
        # 1) Inputs
        stage, label = _resolve_stage_and_label(state, config = config)
        rp_override = _get_registry_override(state, config)

        # 2) Immutable
        imm = await _load_immutable(state, config)
        registry_used = rp_override or imm.registry_profile

        # Use section.id (schema_section_id) as lookup_key: template_version_builder expects
        # lookup_key to startswith MongoDB ObjectId and to match template_json keys.
        # section.section_type (e.g. "section_28nov_navigation_bar_510f") does NOT startswith
        # section_id and would cause AssertionError in _extract_sections_and_base_template_jsons.
        section_id_and_index_mapping = [
            (section.id, idx)
            for idx, section in enumerate(imm.code_dependencies.parsed_sections)
        ]

        # 3) Agent outputs (state)
        agent_outputs = state.get("agent_outputs", {})
                
        # 3) Build materializer with *current* agent_outputs
        
        # We dont enforce that all metadata deps exists in case running in dev mode.
        template_autopopulator = TemplateAutopopulator(
            code_dependencies=imm.code_dependencies,
            data_dependencies=imm.data_dependencies,
            registry_profile=registry_used,
            agent_outputs=agent_outputs,
            enforce_data_exists = True
        )

        # 4) Generate artifact
        result = template_autopopulator.process_and_generate(use_expanded_format=True)
        template_json = result["template_json"]
        custom_css = result.get("custom_css")

        # 5) Snapshot payload (stats in summary)
        payload_str = json.dumps(template_json, separators=(",", ":"), ensure_ascii=False)
        snapshot = {
            "label": label,
            "stage": stage,
            "template_json": template_json,
            "custom_css": custom_css,
            "summary": {
                "ts": _utc_iso(),
                "size_bytes": len(payload_str),
                "sha256": sha256(payload_str.encode("utf-8")).hexdigest(),
                "section_id_and_index_mapping": section_id_and_index_mapping,
            },
        }

        logs.append({
            "ts": _utc_iso(),
            "level": "info",
            "msg": f"Snapshot {label} created for stage {stage}.",
        })

        # 6) Build initial delta (before database save)
        delta = {
            "snapshots": {label: snapshot},  # deep_merge on snapshots
            "meta": {
                "materialize": {
                    "last_stage": stage,
                    "last_label": label,
                    "registry_profile_used": getattr(registry_used, "value", str(registry_used)),
                }
            },
            "logs": logs,                     # add on logs
        }
        
        # 7) Save to database if enabled
        try:
            _save_snapshots_to_database(
                state=state,
                config=config,
                delta=delta,
                stage=stage,
                label=label
            )
            logs.append({
                "ts": _utc_iso(),
                "level": "info",
                "msg": f"materialize_node: {config.get('label')} saved snapshots to database.",
            })
        except Exception as save_error:
            # Log error but don't fail the node
            errors.append({
                "ts": _utc_iso(),
                "level": "error",
                "msg": f"materialize_node: {config.get('label')} failed to save snapshots to database: {str(save_error)}",
            })

        # 8) Update delta with database save logs/errors before returning
        delta["logs"] = logs
        if errors:
            delta["errors"] = errors
        
        return delta

    except Exception as e:
        agent_outputs = state.get("agent_outputs", {})
        errors.append({
            "ts": _utc_iso(),
            "level": "error",
            "msg": f"materialize_node: {config.get('label')} failed, found nodes: {agent_outputs.keys()}",
            "detail": str(e),
        })
        
        # Try to save error state to database if enabled
        try:
            _save_snapshots_to_database(
                state=state,
                config=config,
                delta={"logs": logs},
                errors=errors
            )
            logs.append({
                "ts": _utc_iso(),
                "level": "info",
                "msg": f"materialize_node: {config.get('label')} saved errors to database.",
            })
        except Exception as save_error:
            errors.append({
                "ts": _utc_iso(),
                "level": "error",
                "msg": f"materialize_node: {config.get('label')} failed to save errors to database: {str(save_error)}",
            })
        
        # Return delta with updated logs and errors
        return {"errors": errors, "logs": logs}