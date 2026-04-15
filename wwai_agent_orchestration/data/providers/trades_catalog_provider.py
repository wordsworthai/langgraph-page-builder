"""
Facade provider for trades catalog queries.
"""

from typing import Dict, Any, List, Optional

from wwai_agent_orchestration.core.database import DocumentNotFoundError
from wwai_agent_orchestration.data.repositories.trades_repository import TradesRepositoryService


class TradesCatalogProvider:
    """Provider facade over TradesRepositoryService."""

    def __init__(self):
        self._service = TradesRepositoryService()

    def fetch_trades(
        self,
        database_name: Optional[str] = None,
        collection_name: Optional[str] = None,
        query_filter: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, int]] = None,
    ) -> List[Dict[str, str]]:
        return self._service.fetch_trades(
            database_name=database_name,
            collection_name=collection_name,
            query_filter=query_filter,
            projection=projection,
        )

    def has_trades(self, **kwargs) -> bool:
        try:
            return len(self.fetch_trades(**kwargs)) > 0
        except DocumentNotFoundError:
            return False
