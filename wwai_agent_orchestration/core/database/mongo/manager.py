# core/database/manager.py
"""Database manager with singleton pattern for connection reuse."""

from wwai_agent_orchestration.core.observability.logger import get_logger
from typing import Optional, Dict
from pymongo import MongoClient
from pymongo.database import Database
from motor.motor_asyncio import AsyncIOMotorClient

from wwai_agent_orchestration.core.database.mongo.config import DatabaseConfig
from wwai_agent_orchestration.core.database.mongo.connection import (
    create_mongo_client,
    create_async_mongo_client,
    get_environment,
    ConnectionError
)

logger = get_logger(__name__)


class DatabaseManager:
    """
    Singleton database manager for MongoDB connections.
    
    Features:
    - Single connection reused across the application
    - Access multiple databases on same connection
    - Support for custom connections with different secrets
    - Lazy initialization
    
    Usage:
        # Initialize once at app startup
        db_manager = DatabaseManager.from_env()
        
        # Use anywhere
        db = db_manager.get_database()
        collection = db["templates"]
        
        # Access different database on same connection
        analytics_db = db_manager.get_database("analytics_db")
        
        # Create custom connection (different VM)
        custom_manager = DatabaseManager(
            password_secret="other-vm-pass",
            ip_secret="other-vm-ip",
            db_name="other_db"
        )
    """
    
    _instances: Dict[str, 'DatabaseManager'] = {}  # Track multiple instances
    
    def __init__(
        self,
        config: Optional[DatabaseConfig] = None,
        connection_uri: Optional[str] = None,
        db_name: Optional[str] = None,
        password_secret: Optional[str] = None,
        ip_secret: Optional[str] = None,
        username: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize DatabaseManager.
        
        Args:
            config: DatabaseConfig instance (takes precedence)
            connection_uri: Direct MongoDB URI (overrides secrets)
            db_name: Database name (required if no config)
            password_secret: GCP secret name for password
            ip_secret: GCP secret name for MongoDB IP
            username: MongoDB username
            **kwargs: Additional config parameters (max_pool_size, etc.)
        """
        if config:
            self.config = config
        else:
            # Build config from parameters
            if not db_name:
                raise ValueError("'db_name' is required when not providing config")
            
            self.config = DatabaseConfig(
                db_name=db_name,
                connection_uri=connection_uri,
                password_secret=password_secret,
                ip_secret=ip_secret,
                username=username or "backend",
                **kwargs
            )
        
        self._async_client: Optional[AsyncIOMotorClient] = None
        self._sync_client: Optional[MongoClient] = None
        self._default_db_name = self.config.db_name
        
        # Do not access sync_client here: it would create the client at init time
        # (e.g. during import) before the app can call configure_database(connection_uri=...).
        logger.info(
            f"DatabaseManager initialized with db_name='{self._default_db_name}' (client created lazily)"
        )
    
    @property
    def client(self) -> AsyncIOMotorClient:
        """
        Lazy initialization of async Motor MongoDB client.
        
        Returns:
            AsyncIOMotorClient instance
        """
        if self._async_client is None:
            logger.info("Initializing async Motor MongoDB client (lazy)")
            self._async_client = create_async_mongo_client(self.config)
        return self._async_client
    
    @property
    def sync_client(self) -> MongoClient:
        """
        Lazy initialization of synchronous MongoDB client (for backward compatibility).
        
        Returns:
            MongoClient instance
        """
        if self._sync_client is None:
            logger.info("Initializing synchronous MongoDB client (lazy)")
            self._sync_client = create_mongo_client(self.config)
            logger.info(f"MongoDB sync client connected: address={self._sync_client.address}")
        return self._sync_client
    
    def get_database(self, db_name: Optional[str] = None) -> Database:
        """
        Get synchronous database instance (for backward compatibility).
        
        Args:
            db_name: Database name (uses default if not provided)
            
        Returns:
            MongoDB Database instance (synchronous)
        """
        database_name = db_name or self._default_db_name
        logger.debug(f"Accessing synchronous database: {database_name}")
        return self.sync_client[database_name]
    
    def close(self):
        """Close the MongoDB connections."""
        if self._async_client:
            logger.info("Closing async MongoDB connection")
            self._async_client.close()
            self._async_client = None
        if self._sync_client:
            logger.info("Closing synchronous MongoDB connection")
            self._sync_client.close()
            self._sync_client = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes connection."""
        self.close()
    
    @classmethod
    def from_env(cls, instance_key: str = "default") -> 'DatabaseManager':
        """
        Create DatabaseManager from environment configuration.
        
        This method:
        1. Reads ENVIRONMENT variable
        2. Loads corresponding config from core/config/environments/{env}.py
        3. Creates singleton instance
        
        Args:
            instance_key: Key for tracking multiple instances (default: "default")
            
        Returns:
            DatabaseManager instance (singleton per key)
        """
        # Check if instance already exists
        if instance_key in cls._instances:
            logger.debug(f"Returning existing DatabaseManager instance: {instance_key}")
            return cls._instances[instance_key]
        
        # Load config based on environment
        env = get_environment()
        
        try:
            if env == 'local':
                from wwai_agent_orchestration.core.config.environments.dev import DevConfig
                config = DevConfig()
            elif env == 'dev':
                from wwai_agent_orchestration.core.config.environments.dev import DevConfig
                config = DevConfig()
            elif env == 'uat':
                from wwai_agent_orchestration.core.config.environments.staging import StagingConfig
                config = StagingConfig()
            elif env == 'prod':
                from wwai_agent_orchestration.core.config.environments.prod import ProdConfig
                config = ProdConfig()
            else:
                raise ValueError(f"Unknown environment: {env}")
            
            # Get database config
            if not hasattr(config, 'database'):
                raise AttributeError(
                    f"{env.capitalize()}Config must have 'database' attribute "
                    f"of type DatabaseConfig"
                )
            
            db_config = config.database
            logger.info(f"Loaded database config from {env} environment")
            
            # Create instance
            instance = cls(config=db_config)
            cls._instances[instance_key] = instance
            
            return instance
            
        except ImportError as e:
            logger.error(f"Failed to import {env} config: {e}")
            raise ConnectionError(
                f"Failed to load configuration for environment '{env}': {e}"
            )
    
    @classmethod
    def from_config(cls, config: DatabaseConfig, instance_key: str = "default") -> 'DatabaseManager':
        """
        Create DatabaseManager from explicit DatabaseConfig.
        
        Args:
            config: DatabaseConfig instance
            instance_key: Key for tracking multiple instances
            
        Returns:
            DatabaseManager instance
        """
        if instance_key in cls._instances:
            logger.debug(f"Returning existing DatabaseManager instance: {instance_key}")
            return cls._instances[instance_key]
        
        instance = cls(config=config)
        cls._instances[instance_key] = instance
        return instance
    
    @classmethod
    def reset_instances(cls):
        """
        Reset all singleton instances (useful for testing).
        Closes all connections before resetting.
        """
        logger.info("Resetting all DatabaseManager instances")
        for instance in cls._instances.values():
            instance.close()
        cls._instances.clear()