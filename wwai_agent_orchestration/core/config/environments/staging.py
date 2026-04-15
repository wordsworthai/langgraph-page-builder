# core/config/environments/staging.py
"""Staging environment configuration."""

import os

from wwai_agent_orchestration.core.config.base import BaseConfig
from wwai_agent_orchestration.core.database.mongo.config import DatabaseConfig


class StagingConfig(BaseConfig):
    """Staging environment settings."""
    
    # Existing settings...
    # ...
    
    # Database configuration
    database: DatabaseConfig = DatabaseConfig(
        # Use GCP Secret Manager for staging
        db_name=os.environ.get("MONGO_DB_NAME", ""),
        username=os.environ.get("MONGO_USERNAME", ""),
        password_secret=os.environ.get("MONGO_PASSWORD_SECRET", ""),
        ip_secret=os.environ.get("MONGO_IP_SECRET", ""),

        # Connection pool
        max_pool_size=50,
        min_pool_size=10,

        # GCP project
        gcp_project_id=os.environ.get("GCP_PROJECT_ID", "")
    )