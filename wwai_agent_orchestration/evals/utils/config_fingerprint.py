"""Helpers to build stable config fingerprints for eval comparability."""

import hashlib
from typing import Any, Dict

from wwai_agent_orchestration.evals.utils.hashing import stable_json_dumps


def build_config_fingerprint(config_payload: Dict[str, Any]) -> str:
    """Create a short stable hash for model/prompt/runtime config payload."""
    digest = hashlib.sha256(stable_json_dumps(config_payload).encode("utf-8")).hexdigest()
    return f"cfg_{digest[:16]}"

