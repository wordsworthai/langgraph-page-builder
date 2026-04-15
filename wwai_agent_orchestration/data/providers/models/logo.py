# data_providers/models/logo.py
"""
Logo data models for provider input/output.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# =============================================================================
# INPUT / OUTPUT
# =============================================================================

class LogoInput(BaseModel):
    """Input for LogoProvider."""
    business_id: str


class LogoItem(BaseModel):
    """Single logo item."""
    logo_id: str
    url: str
    width: Optional[int] = None
    height: Optional[int] = None
    aspect_ratio: Optional[float] = None
    trade_type: str
    source: str = "generated"  # "generated" | "uploaded"


class LogoOutput(BaseModel):
    """
    Logo output for a business.
    
    Returns logo(s) based on business's assigned trades.
    Primary logo is the first match.
    """
    
    # Primary logo (first match)
    has_logo: bool = False
    primary_logo: Optional[LogoItem] = None
    
    # All matching logos (if business has multiple trades)
    all_logos: List[LogoItem] = Field(default_factory=list)
    total_count: int = 0
    
    # Context
    matched_trades: List[str] = Field(default_factory=list)
    
    # Metadata
    data_source: str = "media_management"
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)