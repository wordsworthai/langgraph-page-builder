# core/config/environments/prod.py
"""Production environment configuration."""

import os

from wwai_agent_orchestration.core.config.base import BaseConfig
from wwai_agent_orchestration.core.database.mongo.config import DatabaseConfig


class ProdConfig(BaseConfig):
    """Production environment settings."""
    
    # Existing settings...
    # ...
    
    # Database configuration
    database: DatabaseConfig = DatabaseConfig(
        # Use GCP Secret Manager for production
        db_name=os.environ.get("MONGO_DB_NAME", ""),
        username=os.environ.get("MONGO_USERNAME", ""),
        password_secret=os.environ.get("MONGO_PASSWORD_SECRET", ""),
        ip_secret=os.environ.get("MONGO_IP_SECRET", ""),

        # Connection pool (larger for production)
        max_pool_size=100,
        min_pool_size=20,

        # Production timeouts
        server_selection_timeout_ms=5000,
        connect_timeout_ms=10000,

        # GCP project
        gcp_project_id=os.environ.get("GCP_PROJECT_ID", "")
    )