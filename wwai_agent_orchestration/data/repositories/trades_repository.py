# data_connections/trades_repository.py
"""
Trades Catalog data access service.

Encapsulates MongoDB access for trades catalog, providing list of
available trade classifications.
"""

from typing import Dict, Any, List, Optional

from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.core.database import (
    db_manager as global_db_manager,
    fetch_from_collection,
    DocumentNotFoundError,
)


class TradesRepositoryService:
    """
    Service for fetching trades catalog from MongoDB.
    
    The service uses the global db_manager by default, but a different
    manager can be injected (useful for tests).
    """
    
    # Service-level defaults
    DEFAULT_DATABASE_NAME: str = "trades"
    DEFAULT_COLLECTION_NAME: str = "trades_catalog"
    DEFAULT_QUERY_FILTER: Dict[str, Any] = {}  # Fetch all trades
    DEFAULT_PROJECTION: Dict[str, int] = {
        "trade": 1,
        "description": 1,
        "parent_category": 1,
        "_id": 0  # Exclude MongoDB _id
    }
    
    def __init__(self, db_manager=None):
        self._logger = get_logger(__name__)
        self._db_manager = db_manager or global_db_manager
    
    def fetch_trades(
        self,
        database_name: Optional[str] = None,
        collection_name: Optional[str] = None,
        query_filter: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, int]] = None
    ) -> List[Dict[str, str]]:
        """
        Fetch trades catalog from MongoDB.
        
        Args:
            database_name: Name of the MongoDB database (uses default if None)
            collection_name: Name of the collection to query (uses default if None)
            query_filter: MongoDB query filter dict (uses default if None)
            projection: Fields to include in results (uses default if None)
        
        Returns:
            List of trade dicts with keys: trade, description, parent_category
        
        Raises:
            DocumentNotFoundError: If no documents are found
            Exception: For other unexpected errors
        """
        database = database_name or self.DEFAULT_DATABASE_NAME
        collection = collection_name or self.DEFAULT_COLLECTION_NAME
        filters = query_filter if query_filter is not None else self.DEFAULT_QUERY_FILTER
        proj = projection or self.DEFAULT_PROJECTION
        
        self._logger.info(
            "Trades Repository Service: Fetching trades catalog",
            database=database,
            collection=collection,
            query=filters
        )
        
        db = self._db_manager.get_database(database)
        
        # Fetch with projection
        col = db[collection]
        documents = list(col.find(filters, proj))
        
        if not documents:
            raise DocumentNotFoundError(f"No trades found in {database}.{collection}")
        
        self._logger.info(
            "Fetched trades catalog",
            database=database,
            collection=collection,
            count=len(documents)
        )
        
        return documents


__all__ = [
    "TradesRepositoryService",
]