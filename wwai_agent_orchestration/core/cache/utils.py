# core/cache/utils.py
"""
Shared cache utilities for LangGraph node caching.

Pure helpers with no workflow-specific assumptions.
"""

from typing import Dict, Any, Union
import hashlib
import json


def hash_dict(data: Dict[str, Any]) -> str:
    """Generate deterministic hash of dict."""
    json_str = json.dumps(data, sort_keys=True, default=str)
    return hashlib.md5(json_str.encode()).hexdigest()


def dict_to_cache_string(cache_dict: Dict[str, Any]) -> str:
    """
    Convert cache key dict to deterministic string.

    LangGraph needs string/bytes for hashing, not dict.

    Args:
        cache_dict: Dict with cache key components

    Returns:
        JSON string (deterministic with sorted keys)
    """
    return json.dumps(cache_dict, sort_keys=True, default=str)


def get_value_from_langgraph_state(state: Union[Dict, Any], key: str, default=None):
    """
    Get value from LangGraph state (works with both dict and Pydantic model).

    Args:
        state: State (dict or Pydantic model)
        key: Key to get
        default: Default value if not found

    Returns:
        Value from state
    """
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)
