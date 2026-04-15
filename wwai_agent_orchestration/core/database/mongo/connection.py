# core/database/connection.py
"""MongoDB connection creation utilities."""

import os
import urllib.parse
from typing import Optional
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from google.cloud import secretmanager

from wwai_agent_orchestration.core.database.mongo.config import DatabaseConfig
from wwai_agent_orchestration.core.observability.logger import get_logger

logger = get_logger(__name__)


class ConnectionError(Exception):
    """Custom exception for database connection errors."""
    pass


def get_secret(secret_name: str, project_id: str) -> str:
    """
    Get secret from Google Cloud Secret Manager.
    
    Args:
        secret_name: Name of the secret in Secret Manager
        project_id: GCP project ID
        
    Returns:
        Secret value as string
        
    Raises:
        ConnectionError: If secret retrieval fails
    """
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        secret_value = response.payload.data.decode("UTF-8")
        logger.info(f"Successfully retrieved secret: {secret_name}")
        return secret_value
    except Exception as e:
        logger.error(f"Failed to retrieve secret '{secret_name}': {str(e)}")
        raise ConnectionError(f"Failed to retrieve secret '{secret_name}': {str(e)}")


def build_connection_string_from_secrets(config: DatabaseConfig) -> str:
    """
    Build MongoDB connection string using GCP Secret Manager.
    
    Args:
        config: DatabaseConfig with secret names
        
    Returns:
        MongoDB connection string
        
    Raises:
        ConnectionError: If secret retrieval fails
    """
    logger.info(
        f"Building connection string from secrets: "
        f"password_secret={config.password_secret}, "
        f"ip_secret={config.ip_secret}, "
        f"username={config.username}"
    )
    
    # Get secrets
    raw_password = get_secret(config.password_secret, config.gcp_project_id)
    mongo_ip = get_secret(config.ip_secret, config.gcp_project_id)
    
    # URL-encode password (handle special characters)
    encoded_password = urllib.parse.quote(raw_password, safe="")
    
    # Build connection string
    connection_string = f"mongodb://{config.username}:{encoded_password}@{mongo_ip}/admin"
    
    logger.info(f"Built connection string: mongodb://{config.username}:****@{mongo_ip}/admin")
    return connection_string


def create_mongo_client(config: DatabaseConfig) -> MongoClient:
    """
    Create synchronous MongoDB client based on configuration.
    
    Priority:
    1. Direct connection_uri (if provided)
    2. Build from Secret Manager (production)
    3. Fail if neither is available
    
    Args:
        config: DatabaseConfig instance
        
    Returns:
        MongoClient instance with connection pooling
        
    Raises:
        ConnectionError: If connection creation fails
    """
    try:
        connection_string = get_connection_string(config)
        
        logger.info("Creating synchronous MongoDB client")
        client = MongoClient(
            connection_string,
            maxPoolSize=config.max_pool_size,
            minPoolSize=config.min_pool_size,
            serverSelectionTimeoutMS=config.server_selection_timeout_ms,
            connectTimeoutMS=config.connect_timeout_ms
        )
        
        # Test connection
        client.admin.command('ping')
        logger.info(
            f"Successfully connected to MongoDB. "
            f"Pool size: {config.min_pool_size}-{config.max_pool_size}"
        )
        
        return client
        
    except Exception as e:
        logger.error(f"Failed to create MongoDB client: {str(e)}")
        raise ConnectionError(f"Failed to create MongoDB client: {str(e)}")


def get_connection_string(config: DatabaseConfig) -> str:
    """
    Get MongoDB connection string from config.
    
    Priority:
    1. Direct connection_uri (if provided)
    2. Build from Secret Manager (production)
    3. Fail if neither is available
    
    Args:
        config: DatabaseConfig instance
        
    Returns:
        MongoDB connection string
        
    Raises:
        ConnectionError: If connection string cannot be built
    """
    # Priority 1: Direct URI (local/testing)
    if config.connection_uri:
        return config.connection_uri
    
    # Priority 2: Build from Secret Manager (production)
    elif config.password_secret and config.ip_secret:
        return build_connection_string_from_secrets(config)
    
    else:
        raise ConnectionError(
            "Must provide either 'connection_uri' or both 'password_secret' and 'ip_secret'"
        )


def create_async_mongo_client(config: DatabaseConfig) -> AsyncIOMotorClient:
    """
    Create async Motor MongoDB client based on configuration.
    
    Priority:
    1. Direct connection_uri (if provided)
    2. Build from Secret Manager (production)
    3. Fail if neither is available
    
    Args:
        config: DatabaseConfig instance
        
    Returns:
        AsyncIOMotorClient instance with connection pooling
        
    Raises:
        ConnectionError: If connection creation fails
    """
    try:
        connection_string = get_connection_string(config)
        
        logger.info("Creating async Motor MongoDB client")
        client = AsyncIOMotorClient(
            connection_string,
            maxPoolSize=config.max_pool_size,
            minPoolSize=config.min_pool_size,
            serverSelectionTimeoutMS=config.server_selection_timeout_ms,
            connectTimeoutMS=config.connect_timeout_ms
        )
        
        # Test connection (async, but we'll do it synchronously for initialization)
        # Note: In async context, you'd use await client.admin.command('ping')
        logger.info(
            f"Successfully created async Motor MongoDB client. "
            f"Pool size: {config.min_pool_size}-{config.max_pool_size}"
        )
        
        return client
        
    except Exception as e:
        logger.error(f"Failed to create async Motor MongoDB client: {str(e)}")
        raise ConnectionError(f"Failed to create async Motor MongoDB client: {str(e)}")


# Raw ENVIRONMENT values -> canonical keys understood by DatabaseManager.from_env
_ENV_ALIASES: dict[str, str] = {
    # development (DevConfig)
    "local": "local",
    "development": "local",
    "dev": "local",
    # UAT / staging (StagingConfig)
    "uat": "uat",
    "staging": "uat",
    "test": "uat",
    # production (ProdConfig)
    "production": "prod",
    "prod": "prod",
}


def get_environment() -> str:
    """
    Resolve canonical environment for MongoDB config.

    Reads ``ENVIRONMENT`` first, then legacy ``ENVIRONMENT_orchestration``.

    Aliases (case-insensitive):
        - Development: local, development, dev -> local
        - UAT: uat, staging, test -> uat
        - Production: production, prod -> prod

    Returns:
        One of ``local``, ``uat``, ``prod`` (DatabaseManager also accepts ``dev``
        for dev config; we normalize dev-like values to ``local``).
    """
    raw = (os.getenv("ENVIRONMENT") or os.getenv("ENVIRONMENT_orchestration") or "local").strip()
    key = raw.lower()
    if key not in _ENV_ALIASES:
        valid = ", ".join(sorted(_ENV_ALIASES.keys()))
        raise ValueError(
            f"Unknown ENVIRONMENT={raw!r}. "
            f"Use one of: {valid}"
        )
    canonical = _ENV_ALIASES[key]
    logger.info(f"Detected environment: {raw!r} -> {canonical}")
    return canonical