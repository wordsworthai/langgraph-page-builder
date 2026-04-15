# core/cache/policy.py
"""
Generic CachePolicy factory for LangGraph node caching.
"""

from typing import Callable

from langgraph.types import CachePolicy

DEFAULT_CACHE_TTL = 5184000  # 60 days


def create_cache_policy(key_func: Callable, ttl: int = DEFAULT_CACHE_TTL) -> CachePolicy:
    """Create a LangGraph CachePolicy from a key function and TTL."""
    return CachePolicy(key_func=key_func, ttl=ttl)
