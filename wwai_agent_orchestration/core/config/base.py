# core/config/base.py
"""Base configuration class for all environments."""

from pydantic import BaseModel


class BaseConfig(BaseModel):
    """
    Base configuration class that all environment configs inherit from.
    
    Add any common configuration fields here that should be shared
    across all environments (dev, staging, prod).
    """
    
    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True
        validate_assignment = True