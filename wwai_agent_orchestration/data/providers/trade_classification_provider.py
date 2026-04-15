"""
Facade provider for trade classification persistence.

Keeps repository/storage internals inside the data layer boundary.
"""

from typing import Dict, Any, Optional, List

from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.data.repositories.business_data_storage import (
    get_trade_classification_by_cache_key_sync,
    get_trade_classification_by_business_id_sync,
    store_trade_classification_by_cache_key_sync,
)

logger = get_logger(__name__)


class TradeClassificationProvider:
    """Provider facade for trade classification reads/writes."""

    def get_by_cache_key(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get stored classification by cache_key (business_id:location_id)."""
        if not cache_key:
            return None
        return get_trade_classification_by_cache_key_sync(str(cache_key))

    def save_for_cache_key(
        self, cache_key: str, trade_assignments: Dict[str, Any]
    ) -> bool:
        """Save classification payload by cache_key."""
        if not cache_key or not trade_assignments:
            logger.warning(
                "Invalid input for save_for_cache_key",
                has_cache_key=bool(cache_key),
                has_trade_assignments=bool(trade_assignments),
            )
            return False
        return store_trade_classification_by_cache_key_sync(
            cache_key=str(cache_key),
            trade_assignments=trade_assignments,
        )

    def get_by_business_id(self, business_id: str) -> Optional[Dict[str, Any]]:
        """Get most recent classification for a business (callers without location context)."""
        if not business_id:
            return None
        return get_trade_classification_by_business_id_sync(str(business_id))

    def get_assigned_trade_names(self, business_id: str) -> List[str]:
        """Extract assigned trade names from stored classification."""
        classification = self.get_by_business_id(business_id) or {}
        assigned = classification.get("assigned_trades") or []
        trades = []
        for entry in assigned:
            if isinstance(entry, dict):
                trade = entry.get("trade")
                if trade:
                    trades.append(trade)
        return sorted(trades)
