# agent_workflows/landing_page_builder/cache/__init__.py
"""
Landing Page Builder cache policy and keys.
"""

from wwai_agent_orchestration.core.cache import (
    DEFAULT_CACHE_TTL,
    create_cache_policy as _create_cache_policy,
)
from wwai_agent_orchestration.agent_workflows.landing_page_builder.cache.keys import (
    business_data_extractor_cache_key,
    campaign_intent_synthesizer_cache_key,
    section_repo_fetcher_cache_key,
    resolve_template_sections_from_repo_cache_key,
    generate_template_structures_cache_key,
)

KEY_FUNCS = {
    "business_data_extractor": business_data_extractor_cache_key,
    "campaign_intent_synthesizer": campaign_intent_synthesizer_cache_key,
    "section_repo_fetcher": section_repo_fetcher_cache_key,
    "generate_template_structures": generate_template_structures_cache_key,
    "resolve_template_sections_from_repo": resolve_template_sections_from_repo_cache_key,
}

CACHE_TTL = DEFAULT_CACHE_TTL


def create_node_cache_policy(node_name: str):
    """Create CachePolicy for a node by name. Returns None if node has no cache key."""
    key_func = KEY_FUNCS.get(node_name)
    if key_func is None:
        return None
    return _create_cache_policy(key_func, CACHE_TTL)


__all__ = [
    "create_node_cache_policy",
    "CACHE_TTL",
    "business_data_extractor_cache_key",
    "campaign_intent_cache_key",
    "section_repo_cache_key",
    "template_generation_cache_key",
    "section_retrieval_cache_key",
]
