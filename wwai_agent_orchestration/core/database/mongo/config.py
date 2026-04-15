# core/database/config.py
"""Database configuration schema using Pydantic."""

from pydantic import BaseModel, Field, validator
from typing import Optional
import os


class DatabaseConfig(BaseModel):
    """
    Database configuration schema with support for:
    - Direct URI connection (local/testing)
    - GCP Secret Manager (production)
    - Multiple databases on same connection
    - Custom secret names for different VMs
    """
    
    # Connection settings
    db_name: str = Field(
        ..., 
        description="Default database name"
    )
    
    username: str = Field(
        default="backend",
        description="MongoDB username"
    )
    
    # Secret Manager settings (for production)
    password_secret: Optional[str] = Field(
        default="brands-data-mongo-pass",
        description="GCP Secret Manager secret name for MongoDB password"
    )
    
    ip_secret: Optional[str] = Field(
        default="brands-data-vm-ip",
        description="GCP Secret Manager secret name for MongoDB IP"
    )
    
    # Direct connection (overrides secrets)
    connection_uri: Optional[str] = Field(
        default=None,
        description="Direct MongoDB URI (mongodb://...). Takes precedence over secrets."
    )
    
    # Connection pool settings
    max_pool_size: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of connections in the pool"
    )
    
    min_pool_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Minimum number of connections in the pool"
    )
    
    # GCP settings
    gcp_project_id: str = Field(
        default=os.environ.get("GCP_PROJECT_ID", ""),
        description="GCP project ID for Secret Manager"
    )
    
    # Timeout settings
    server_selection_timeout_ms: int = Field(
        default=5000,
        ge=1000,
        description="Timeout for server selection (milliseconds)"
    )
    
    connect_timeout_ms: int = Field(
        default=10000,
        ge=1000,
        description="Timeout for initial connection (milliseconds)"
    )
    
    @validator('min_pool_size')
    def validate_pool_sizes(cls, v, values):
        """Ensure min_pool_size <= max_pool_size"""
        max_pool = values.get('max_pool_size', 50)
        if v > max_pool:
            raise ValueError(f"min_pool_size ({v}) cannot exceed max_pool_size ({max_pool})")
        return v
    
    class Config:
        """Pydantic config"""
        validate_assignment = True
        extra = "forbid"  # Prevent typos in config