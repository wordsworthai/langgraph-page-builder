"""Stable hashing and ID helpers for eval runs."""

import hashlib
import json
import uuid
from typing import Any, Dict


def stable_json_dumps(payload: Dict[str, Any]) -> str:
    """Serialize dict payload deterministically for hashing."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def build_case_id(
    *,
    eval_set_version: str,
    eval_type: str,
    workflow_mode: str,
    set_inputs: Dict[str, Any],
    workflow_inputs: Dict[str, Any],
) -> str:
    """Build deterministic case identifier from normalized case inputs."""
    canonical_payload = {
        "eval_set_version": eval_set_version,
        "eval_type": eval_type,
        "workflow_mode": workflow_mode,
        "set_inputs": set_inputs,
        "workflow_inputs": workflow_inputs,
    }
    digest = hashlib.sha256(stable_json_dumps(canonical_payload).encode("utf-8")).hexdigest()
    return f"case_{digest[:24]}"


def build_run_id() -> str:
    """Build unique run attempt identifier."""
    return f"run_{uuid.uuid4().hex}"


def build_thread_id(run_id: str) -> str:
    """Build thread identifier for checkpointing."""
    return run_id

