"""Shared DB and shape helpers for eval adapters."""

from __future__ import annotations

import os
from typing import Optional

from pymongo import MongoClient


def get_db(mongo_uri: Optional[str] = None, db_name: str = "eval"):
    """Get MongoDB database for eval collections."""
    uri = mongo_uri or os.getenv(
        "MONGO_CONNECTION_URI",
        "mongodb://localhost:27020/",
    )
    return MongoClient(uri)[db_name]


