"""Human feedback adapter."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ._common import get_db


def get_human_feedback_for_eval_set(
    eval_set_id: str,
    mongo_uri: Optional[str] = None,
    db_name: str = "checkpointing_db",
) -> List[Dict[str, Any]]:
    """Get all human feedback docs for an eval set (for metrics)."""
    db = get_db(mongo_uri, db_name)
    return list(db["human_feedback"].find({"eval_set_id": eval_set_id}))
