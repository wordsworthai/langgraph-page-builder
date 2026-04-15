# data/connectors/base_mongo_provider.py
"""
Base provider class with MongoDB connection handling.
"""

from wwai_agent_orchestration.core.observability.logger import get_logger
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
from pymongo.database import Database
from pymongo.collection import Collection

from wwai_agent_orchestration.core.database import db_manager

logger = get_logger(__name__)


class BaseProvider:
    """
    Base class for all data providers.

    Handles MongoDB connection management and common utilities.
    Uses the global db_manager for database connections.
    """

    def __init__(self):
        """Initialize base provider (no MongoDB client creation needed)."""
        pass

    # =========================================================================
    # CONNECTION MANAGEMENT
    # =========================================================================

    def get_database(self, database_name: str) -> Database:
        """Get database instance using global db_manager."""
        return db_manager.get_database(database_name)

    def get_collection(self, database_name: str, collection_name: str) -> Collection:
        """Get collection instance."""
        db = self.get_database(database_name)
        return db[collection_name]

    # =========================================================================
    # COMMON QUERIES
    # =========================================================================

    def find_one(
        self,
        database_name: str,
        collection_name: str,
        query: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Find single document."""
        try:
            collection = self.get_collection(database_name, collection_name)
            doc = collection.find_one(query)
            if doc and "_id" in doc:
                doc.pop("_id")
            return doc
        except Exception as e:
            logger.error(f"find_one failed: {e}")
            return None

    def find_many(
        self,
        database_name: str,
        collection_name: str,
        query: Dict[str, Any],
        limit: Optional[int] = None,
        sort: Optional[List[tuple]] = None
    ) -> List[Dict[str, Any]]:
        """Find multiple documents."""
        try:
            collection = self.get_collection(database_name, collection_name)
            cursor = collection.find(query)

            if sort:
                cursor = cursor.sort(sort)
            if limit:
                cursor = cursor.limit(limit)

            results = []
            for doc in cursor:
                if "_id" in doc:
                    doc.pop("_id")
                results.append(doc)

            return results
        except Exception as e:
            logger.error(f"find_many failed: {e}")
            return []

    def upsert_one(
        self,
        database_name: str,
        collection_name: str,
        query: Dict[str, Any],
        data: Dict[str, Any]
    ) -> bool:
        """Upsert single document."""
        try:
            collection = self.get_collection(database_name, collection_name)
            collection.replace_one(query, data, upsert=True)
            return True
        except Exception as e:
            logger.error(f"upsert_one failed: {e}")
            return False

    def update_one(
        self,
        database_name: str,
        collection_name: str,
        query: Dict[str, Any],
        update: Dict[str, Any]
    ) -> bool:
        """Update single document."""
        try:
            collection = self.get_collection(database_name, collection_name)
            collection.update_one(query, update, upsert=True)
            return True
        except Exception as e:
            logger.error(f"update_one failed: {e}")
            return False

    # =========================================================================
    # BUSINESS-SPECIFIC QUERIES
    # =========================================================================

    def get_business_trades(self, business_id: str) -> List[str]:
        """
        Get assigned trades for a business from business_types collection.
        """
        try:
            doc = self.find_one(
                "businesses",
                "business_types",
                {"business_id": business_id}
            )

            if not doc:
                logger.warning(f"No business_types document found for business_id: {business_id}")
                return []

            assigned_trades = doc.get("assigned_trades", [])
            if not assigned_trades:
                logger.warning(f"Empty assigned_trades for business_id: {business_id}")
                return []

            trades = [t.get("trade") for t in assigned_trades if t.get("trade")]

            logger.info(f"Found {len(trades)} trades for business_id {business_id}: {trades}")
            return trades

        except Exception as e:
            logger.error(f"Failed to get business trades for {business_id}: {e}")
            return []

    # =========================================================================
    # UTILITIES
    # =========================================================================

    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    @staticmethod
    def extract_domain(url: str) -> Optional[str]:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.replace("www.", "")
        except Exception:
            return None
