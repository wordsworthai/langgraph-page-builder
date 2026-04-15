# core/cache/config.py
"""
Cache config extraction from workflow state.

Expects state.execution_config.cache_strategy with {use_cache, version, node_overrides}.
Override in workflow if different config shape.
"""

from typing import Union

from wwai_agent_orchestration.core.cache.utils import get_value_from_langgraph_state


def should_use_cache(state: Union[dict, object], node_name: str) -> bool:
    """
    Check if caching is enabled for this node.

    Expects state.execution_config.cache_strategy with use_cache and node_overrides.
    Override in workflow if different config shape.

    Args:
        state: Workflow state (dict or Pydantic model)
        node_name: Name of the node

    Returns:
        True if cache should be used
    """
    exec_config = get_value_from_langgraph_state(state, "execution_config", None)

    if exec_config is None:
        return False

    if isinstance(exec_config, dict):
        cache_strategy = exec_config.get("cache_strategy", {})
    else:
        cache_strategy = getattr(exec_config, "cache_strategy", None)
        if cache_strategy and hasattr(cache_strategy, "model_dump"):
            cache_strategy = cache_strategy.model_dump()
        elif cache_strategy is None:
            cache_strategy = {}

    if isinstance(cache_strategy, dict):
        use_cache = cache_strategy.get("use_cache", False)
    else:
        use_cache = getattr(cache_strategy, "use_cache", False)

    if not use_cache:
        return False

    if isinstance(cache_strategy, dict):
        node_overrides = cache_strategy.get("node_overrides", {})
    else:
        node_overrides = getattr(cache_strategy, "node_overrides", {})

    if not node_overrides or not isinstance(node_overrides, dict):
        return True

    node_config = node_overrides.get(node_name)
    if node_config is None:
        return True
    if isinstance(node_config, bool):
        return node_config
    if isinstance(node_config, dict):
        return node_config.get("enabled", True)
    return getattr(node_config, "enabled", True)


def get_cache_version(state: Union[dict, object]) -> str:
    """Get cache version from execution_config. Expects state.execution_config.cache_strategy."""
    exec_config = get_value_from_langgraph_state(state, "execution_config", None)

    if exec_config is None:
        return "v1"

    if isinstance(exec_config, dict):
        cache_strategy = exec_config.get("cache_strategy", {})
    else:
        cache_strategy = getattr(exec_config, "cache_strategy", None)
        if cache_strategy and hasattr(cache_strategy, "model_dump"):
            cache_strategy = cache_strategy.model_dump()
        elif cache_strategy is None:
            cache_strategy = {}

    if isinstance(cache_strategy, dict):
        return cache_strategy.get("version", "v1")
    return getattr(cache_strategy, "version", "v1")
