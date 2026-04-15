# core/database/__init__.py
"""
Database utilities for Wordsworth AI.

Supports multiple database backends:
- MongoDB (current)
- Redis (future)

Usage:
    from core.database import db_manager, fetch_from_collection
    
    # Use in any node/workflow
    def my_node(state, config):
        db = db_manager.get_database()
        templates = fetch_from_collection("templates", {"type": "hero"}, db)
"""

# Import MongoDB utilities
from .mongo.config import DatabaseConfig
from .mongo.manager import DatabaseManager
from .mongo.operations import (
    fetch_from_collection,
    fetch_one_from_collection,
    upsert_document,
    insert_document,
    update_document,
    delete_document,
    count_documents,
    DocumentNotFoundError,
    OperationError
)
from .mongo.connection import ConnectionError

from wwai_agent_orchestration.core.observability.logger import get_logger
logger = get_logger(__name__)

class _DatabaseManagerProxy:
    """
    A thin proxy around DatabaseManager that allows reconfiguration
    without breaking existing import sites that do:
        from wwai_agent_orchestration.core.database import db_manager
    
    Any reconfiguration swaps the underlying manager while keeping the
    proxy object stable, so existing references continue to work.
    """
    
    def __init__(self):
        logger.info("Initializing DatabaseManagerProxy")
        self._manager: DatabaseManager = DatabaseManager.from_env()
    
    # --- configuration APIs ---
    def configure(
        self,
        config: DatabaseConfig | None = None,
        *,
        connection_uri: str | None = None,
        db_name: str | None = None,
        password_secret: str | None = None,
        ip_secret: str | None = None,
        username: str | None = None,
        instance_key: str | None = None,
        close_previous: bool = True,
        **kwargs
    ) -> None:
        """
        Replace the underlying DatabaseManager with a new configuration.
        
        You can either pass a DatabaseConfig instance, or pass the
        constructor parameters (e.g. connection_uri, db_name, ...).
        
        Args:
            config: Explicit DatabaseConfig to use.
            connection_uri: Direct Mongo URI (overrides secrets).
            db_name: Default database name (required if no config).
            password_secret: GCP Secret Manager password secret name.
            ip_secret: GCP Secret Manager IP/host secret name.
            username: MongoDB username.
            instance_key: Optional key if you prefer using manager's
                singleton registry. If provided, a cached instance
                under this key will be reused/created.
            close_previous: Whether to close the previous client.
            **kwargs: Pool/timeouts and other DatabaseConfig fields.
        """
        logger.info("Reconfiguring database")
        # Build or fetch the next manager
        if config is not None:
            next_manager = (
                DatabaseManager.from_config(config, instance_key=instance_key or "default")
                if instance_key
                else DatabaseManager(config=config)
            )
        else:
            # Validate required args when no config is provided
            if not db_name:
                raise ValueError("'db_name' is required when not providing 'config'")
            if instance_key:
                next_manager = DatabaseManager.from_config(
                    DatabaseConfig(
                        db_name=db_name,
                        connection_uri=connection_uri,
                        password_secret=password_secret,
                        ip_secret=ip_secret,
                        username=username or "backend",
                        **kwargs
                    ),
                    instance_key=instance_key,
                )
            else:
                next_manager = DatabaseManager(
                    config=DatabaseConfig(
                        db_name=db_name,
                        connection_uri=connection_uri,
                        password_secret=password_secret,
                        ip_secret=ip_secret,
                        username=username or "backend",
                        **kwargs
                    )
                )
        
        # Swap managers safely
        previous = self._manager
        self._manager = next_manager
        if close_previous and previous is not next_manager:
            try:
                previous.close()
            except Exception:
                # Swallow close errors to avoid masking configuration
                # failures in downstream callers.
                pass
    
    def reset_to_env(self, *, instance_key: str | None = None, close_previous: bool = True) -> None:
        """
        Reinitialize the underlying DatabaseManager from the current
        ``ENVIRONMENT`` (or legacy ``ENVIRONMENT_orchestration``) setting.
        """
        next_manager = (
            DatabaseManager.from_env(instance_key or "default")
            if instance_key
            else DatabaseManager.from_env()
        )
        previous = self._manager
        self._manager = next_manager
        if close_previous and previous is not next_manager:
            try:
                previous.close()
            except Exception:
                pass
    
    # --- delegated APIs used across the codebase ---
    @property
    def client(self):
        return self._manager.client
    
    @property
    def sync_client(self):
        """Get synchronous MongoDB client (for LangGraph checkpointer, etc.)."""
        return self._manager.sync_client
    
    def get_database(self, db_name: str | None = None):
        return self._manager.get_database(db_name)
    
    def close(self):
        return self._manager.close()
    
    def __enter__(self):
        return self._manager.__enter__()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._manager.__exit__(exc_type, exc_val, exc_tb)


# Stable proxy instance used across the application
db_manager = _DatabaseManagerProxy()


def configure_database(
    config: DatabaseConfig | None = None,
    *,
    connection_uri: str | None = None,
    db_name: str | None = None,
    password_secret: str | None = None,
    ip_secret: str | None = None,
    username: str | None = None,
    instance_key: str | None = None,
    close_previous: bool = True,
    **kwargs
) -> None:
    """
    Public function to programmatically configure the global database manager.
    
    Typical usage from a consuming repo:
        from wwai_agent_orchestration.core.database import configure_database, DatabaseConfig
        
        # Option A: pass a DatabaseConfig
        configure_database(DatabaseConfig(
            connection_uri="mongodb://user:pass@host:port/",
            db_name="my_db",
            username="user",
            max_pool_size=20,
            min_pool_size=5,
        ))
        
    Or:
        # Option B: pass parameters directly
        configure_database(
            connection_uri="mongodb://user:pass@host:port/",
            db_name="my_db",
            username="user",
            max_pool_size=20,
            min_pool_size=5,
        )
    """
    db_manager.configure(
        config,
        connection_uri=connection_uri,
        db_name=db_name,
        password_secret=password_secret,
        ip_secret=ip_secret,
        username=username,
        instance_key=instance_key,
        close_previous=close_previous,
        **kwargs,
    )

__all__ = [
    # Core classes
    "DatabaseConfig",
    "DatabaseManager",
    
    # Global instance (recommended for most use cases)
    "db_manager",
    "configure_database",
    
    # Operations
    "fetch_from_collection",
    "fetch_one_from_collection",
    "upsert_document",
    "insert_document",
    "update_document",
    "delete_document",
    "count_documents",
    
    # Exceptions
    "DocumentNotFoundError",
    "OperationError",
    "ConnectionError",
]