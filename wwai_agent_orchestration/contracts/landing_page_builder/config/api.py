"""
External API configuration for Landing Page Builder Workflow (e.g. Yelp).
"""

import os
from dataclasses import dataclass


@dataclass
class ExternalAPIConfig:
    """Yelp and any future external APIs."""

    rapidapi_key: str = ""
    rapidapi_host: str = "yelp-business-api.p.rapidapi.com"
    yelp_timeout: int = 60

    def __post_init__(self):
        if not self.rapidapi_key:
            self.rapidapi_key = os.getenv("RAPIDAPI_KEY", "")
