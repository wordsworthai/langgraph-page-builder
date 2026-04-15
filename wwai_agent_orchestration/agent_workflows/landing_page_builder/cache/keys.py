# agent_workflows/landing_page_builder/cache/keys.py
"""
Landing Page Builder cache key functions for LangGraph node caching.

Each function returns a STRING that LangGraph hashes to create the cache key.
Only include fields that matter for determining if cached result is valid.
"""

import uuid
from typing import Dict, Any, Union

from wwai_agent_orchestration.core.cache import (
    dict_to_cache_string,
    get_cache_version,
    get_value_from_langgraph_state,
    hash_dict,
    should_use_cache,
)


def _get_google_places_data_from_state(state: Union[Dict, Any]):
    """
    Get google_places_data from state.
    Prefer state.input.external_data_context.google_places_data; fallback to top-level for legacy checkpoints.
    """
    inp = get_value_from_langgraph_state(state, "input", None)
    if inp is not None:
        if isinstance(inp, dict):
            ed = inp.get("external_data_context")
            if ed is not None:
                if isinstance(ed, dict):
                    val = ed.get("google_places_data")
                else:
                    val = getattr(ed, "google_places_data", None)
                if val is not None:
                    return val
        else:
            if getattr(inp, "external_data_context", None) is not None:
                val = getattr(inp.external_data_context, "google_places_data", None)
                if val is not None:
                    return val
    return get_value_from_langgraph_state(state, "google_places_data", None)


def _nocache_key() -> str:
    """Return unique key when cache is disabled so we never hit."""
    return f"_nocache_{uuid.uuid4()}"


def business_data_extractor_cache_key(state: Union[Dict, Any]) -> str:
    """
    Cache key for business data extraction.

    Depends on: business_name, google_places_id, yelp_url, cache version
    """
    if not should_use_cache(state, "business_data_extractor"):
        return _nocache_key()

    google_places_data = _get_google_places_data_from_state(state)
    google_id = None
    if google_places_data:
        if isinstance(google_places_data, dict):
            google_id = google_places_data.get("id")
        else:
            google_id = getattr(google_places_data, "id", None)

    inp = get_value_from_langgraph_state(state, "input", None)
    if inp is None:
        business_name = yelp_url = None
    elif isinstance(inp, dict):
        business_name = inp.get("business_name")
        ed = inp.get("external_data_context")
        yelp_url = ed.get("yelp_url") if isinstance(ed, dict) else (getattr(ed, "yelp_url", None) if ed else inp.get("yelp_url"))
    else:
        business_name = inp.business_name
        yelp_url = inp.external_data_context.yelp_url if inp.external_data_context else None

    cache_dict = {
        "node": "business_data_extractor",
        "business_name": business_name,
        "google_places_id": google_id,
        "yelp_url": yelp_url,
        "cache_version": get_cache_version(state),
    }
    return dict_to_cache_string(cache_dict)


def campaign_intent_synthesizer_cache_key(state: Union[Dict, Any]) -> str:
    """
    Cache key for campaign intent synthesis.

    Depends on: business_name, website_intention, website_tone, query,
    google_data_hash, yelp_data_hash, cache version
    """
    if not should_use_cache(state, "campaign_intent_synthesizer"):
        return _nocache_key()

    google_data = _get_google_places_data_from_state(state)
    google_hash = None
    if google_data:
        if hasattr(google_data, "model_dump"):
            google_data = google_data.model_dump()
        google_hash = hash_dict(google_data)

    yelp_data = get_value_from_langgraph_state(state, "yelp_data", None)
    yelp_hash = None
    if yelp_data:
        if hasattr(yelp_data, "model_dump"):
            yelp_data = yelp_data.model_dump()
        yelp_hash = hash_dict(yelp_data)

    inp = get_value_from_langgraph_state(state, "input", None)
    if inp is None:
        business_name = website_intention = website_tone = query = None
    elif isinstance(inp, dict):
        business_name = inp.get("business_name")
        wc = inp.get("website_context")
        if wc is not None:
            wc = wc if isinstance(wc, dict) else (wc.model_dump() if hasattr(wc, "model_dump") else {})
            website_intention = wc.get("website_intention")
            website_tone = wc.get("website_tone")
        else:
            website_intention = inp.get("website_intention")
            website_tone = inp.get("website_tone")
        gc = inp.get("generic_context")
        if gc is not None:
            gc = gc if isinstance(gc, dict) else (gc.model_dump() if hasattr(gc, "model_dump") else {})
            query = gc.get("query")
        else:
            query = inp.get("query")
    else:
        business_name = inp.business_name
        wc = getattr(inp, "website_context", None)
        website_intention = getattr(wc, "website_intention", None) if wc else None
        website_tone = getattr(wc, "website_tone", None) if wc else None
        gc = getattr(inp, "generic_context", None)
        query = getattr(gc, "query", None) if gc else None

    cache_dict = {
        "node": "campaign_intent_synthesizer",
        "business_name": business_name,
        "website_intention": website_intention,
        "website_tone": website_tone,
        "query": query,
        "google_data_hash": google_hash,
        "yelp_data_hash": yelp_hash,
        "cache_version": get_cache_version(state),
    }
    return dict_to_cache_string(cache_dict)


def section_repo_fetcher_cache_key(state: Union[Dict, Any]) -> str:
    """
    Cache key for section repo fetch.

    Depends on: repo filter (static), cache version
    """
    if not should_use_cache(state, "section_repo_fetcher"):
        return _nocache_key()

    cache_dict = {
        "node": "section_repo_fetcher",
        "repo_filter": "smb_active",
        "cache_version": get_cache_version(state),
    }
    return dict_to_cache_string(cache_dict)


def generate_template_structures_cache_key(state: Union[Dict, Any]) -> str:
    """
    Cache key for template L0/L1 generation.

    Depends on: campaign_query, type_details_count, iteration, cache version
    """
    if not should_use_cache(state, "generate_template_structures"):
        return _nocache_key()

    campaign_intent = get_value_from_langgraph_state(state, "campaign_intent", None)
    campaign_query = None
    if campaign_intent:
        if isinstance(campaign_intent, dict):
            campaign_query = campaign_intent.get("campaign_query")
        else:
            campaign_query = getattr(campaign_intent, "campaign_query", None)

    template = get_value_from_langgraph_state(state, "template", None)
    section_repo_result = None
    if template is not None:
        section_repo_result = (
            template.get("section_repo_result")
            if isinstance(template, dict)
            else getattr(template, "section_repo_result", None)
        )
    allowed_section_types = []
    if section_repo_result is not None:
        allowed_section_types = (
            section_repo_result.get("allowed_section_types")
            if isinstance(section_repo_result, dict)
            else getattr(section_repo_result, "allowed_section_types", None)
        ) or []

    cache_dict = {
        "node": "generate_template_structures",
        "campaign_query": campaign_query,
        "type_details_count": len(allowed_section_types),
        "iteration": get_value_from_langgraph_state(state, "iteration", 0),
        "cache_version": get_cache_version(state),
    }
    return dict_to_cache_string(cache_dict)


def resolve_template_sections_from_repo_cache_key(state: Union[Dict, Any]) -> str:
    """
    Cache key for section retrieval (per template).

    Depends on: template_id, campaign_query, section_repo_size, cache version.

    Note: When called from Send() fan-out, state has template.section_retrieval_payload
    with template, section_repo, campaign_intent (not at top level).
    """
    if not should_use_cache(state, "resolve_template_sections_from_repo"):
        return _nocache_key()

    template = get_value_from_langgraph_state(state, "template", None)
    template_id = None
    payload = None
    if template:
        if isinstance(template, dict):
            template_id = template.get("template_id")
            payload = template.get("section_retrieval_payload")
        else:
            template_id = getattr(template, "template_id", None)
            payload = getattr(template, "section_retrieval_payload", None)

    # campaign_intent and section_repo may be at top level or in payload (from Send)
    campaign_intent = get_value_from_langgraph_state(state, "campaign_intent", None)
    section_repo = get_value_from_langgraph_state(state, "section_repo", None)
    if payload is not None:
        if campaign_intent is None and isinstance(payload, dict):
            campaign_intent = payload.get("campaign_intent")
        elif campaign_intent is None:
            campaign_intent = getattr(payload, "campaign_intent", None)
        if section_repo is None and isinstance(payload, dict):
            section_repo = payload.get("section_repo")
        elif section_repo is None:
            section_repo = getattr(payload, "section_repo", None)
        if template_id is None and isinstance(payload, dict):
            tpl = payload.get("template")
            if tpl is not None:
                template_id = tpl.get("template_id") if isinstance(tpl, dict) else getattr(tpl, "template_id", None)
        elif template_id is None:
            tpl = getattr(payload, "template", None)
            if tpl is not None:
                template_id = getattr(tpl, "template_id", None)

    campaign_query = None
    if campaign_intent:
        if isinstance(campaign_intent, dict):
            campaign_query = campaign_intent.get("campaign_query")
        else:
            campaign_query = getattr(campaign_intent, "campaign_query", None)

    if section_repo is None:
        section_repo = []

    cache_dict = {
        "node": "resolve_template_sections_from_repo",
        "template_id": template_id,
        "campaign_query": campaign_query,
        "section_repo_size": len(section_repo) if section_repo else 0,
        "cache_version": get_cache_version(state),
    }
    return dict_to_cache_string(cache_dict)
