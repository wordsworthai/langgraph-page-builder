# core/config/environments/dev.py
"""Development environment configuration."""

import os

from wwai_agent_orchestration.core.config.base import BaseConfig
from wwai_agent_orchestration.core.database.mongo.config import DatabaseConfig


class DevConfig(BaseConfig):
    """Development environment settings."""
    
    # Existing settings...
    # ...
    
    # Database configuration
    database: DatabaseConfig = DatabaseConfig(
        # Use direct URI for local development
        connection_uri=os.environ.get("MONGO_CONNECTION_URI", "mongodb://localhost:27017/"),
        db_name=os.environ.get("MONGO_DB_NAME", "myapp_dev"),
        username=os.environ.get("MONGO_USERNAME", ""),
        
        # Connection pool (smaller for dev)
        max_pool_size=20,
        min_pool_size=5,
        
        # Shorter timeouts for dev
        server_selection_timeout_ms=3000,
        connect_timeout_ms=5000
    )