# data_providers/models/gemini.py
"""
Gemini data models.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


# =============================================================================
# INPUT / OUTPUT (page intent)
# =============================================================================

class GeminiInput(BaseModel):
    """Input for Gemini page intent extraction (URL only)."""
    url: str


class GeminiOutput(BaseModel):
    """Gemini page intent output."""
    url: str
    success: bool

    # Extracted intent
    page_intent: Optional[str] = None
    business_description: Optional[str] = None

    # Metadata
    processing_time_seconds: float = 0
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

    # Error handling
    error_message: Optional[str] = None


# =============================================================================
# GEMINI CONTEXT (custom query over URL)
# =============================================================================

class GeminiContext(BaseModel):
    """Result of Gemini URL context call with custom query."""
    query_used: str
    response_text: str
    url_context_metadata: Optional[Dict[str, Any]] = None
    extraction_timestamp: datetime = Field(default_factory=datetime.utcnow)
