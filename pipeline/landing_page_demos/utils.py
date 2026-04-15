"""
Shared utilities for workflow demo scripts.

This module provides common functions and constants used across all demo scripts.
"""

import os
from typing import Dict, Any, Optional

from absl import flags

from wwai_agent_orchestration.utils.landing_page_builder.execution_config_utils import (
    create_execution_config,
)

FLAGS = flags.FLAGS

# =============================================================================
# CLI FLAGS (shared across all demo scripts)
# =============================================================================

flags.DEFINE_string("business_id", None, "Business ID to use for the demo")
flags.DEFINE_string("business_name", None, "Business name to use for the demo")
flags.DEFINE_string("website_intention", "generate_leads", "Website intention (e.g. generate_leads, showcase)")
flags.DEFINE_string("website_tone", "professional", "Website tone (e.g. professional, friendly)")

# =============================================================================
# CONSTANTS
# =============================================================================

DEFAULT_WEBSITE_INTENTION = "generate_leads"
DEFAULT_WEBSITE_TONE = "professional"

# Default MongoDB configuration (overridden by MONGO_CONNECTION_URI when set)
DEFAULT_MONGO_URI = "mongodb://localhost:27017/"
DEFAULT_DB_NAME = "checkpointing_db"
# Env var for checkpoint DB (partial_autopop loads checkpoints from here)
ENV_MONGO_URI = "MONGO_CONNECTION_URI"
ENV_CHECKPOINT_DB_NAME = "CHECKPOINT_DB_NAME"


# =============================================================================
# ENVIRONMENT SETUP
# =============================================================================

def setup_environment():
    """Setup environment variables for local development."""
    if not os.environ.get('ENVIRONMENT'):
        os.environ['ENVIRONMENT'] = 'local'
    if not os.environ.get('NODE_SERVER_URL'):
        os.environ['NODE_SERVER_URL'] = 'http://localhost:3002'


# =============================================================================
# CONFIGURATION HELPERS
# =============================================================================

def get_default_business_config() -> Dict[str, Any]:
    """Get business configuration from CLI flags (with fallbacks)."""
    return {
        "business_name": FLAGS.business_name or "Your Business Name",
        "business_id": FLAGS.business_id or "your-business-id-here",
        "website_intention": FLAGS.website_intention or DEFAULT_WEBSITE_INTENTION,
        "website_tone": FLAGS.website_tone or DEFAULT_WEBSITE_TONE,
    }


def get_default_mongo_config() -> Dict[str, str]:
    """
    Get MongoDB configuration for demos.
    Uses MONGO_CONNECTION_URI if set (so partial_autopop uses the same DB as your full workflow);
    otherwise falls back to DEFAULT_MONGO_URI. Use CHECKPOINT_DB_NAME to override db_name.
    """
    mongo_uri = os.environ.get(ENV_MONGO_URI, DEFAULT_MONGO_URI)
    db_name = os.environ.get(ENV_CHECKPOINT_DB_NAME, DEFAULT_DB_NAME)
    return {
        "mongo_uri": mongo_uri,
        "db_name": db_name,
    }


def setup_workflow_config() -> Dict[str, Any]:
    """Create workflow configuration with required parameters."""
    return {
        "rapidapi_key": os.environ.get("RAPIDAPI_KEY"),
        "rapidapi_host": os.environ.get("RAPIDAPI_HOST"),
        "section_repo_query_filter": {"status": "ACTIVE", "tag": "smb"},
        "filter_type": "ALL_TYPES",
        "min_sections_per_l0_l1": 1,
    }


def create_default_execution_config(
    section_ids: list = None,
    enable_screenshot_compilation: bool = False,
    use_mock_autopopulation: bool = True,
) -> Any:
    """Create default execution config using execution_config_utils."""
    return create_execution_config(
        section_ids=section_ids,
        enable_screenshot_compilation=enable_screenshot_compilation,
        enable_html_compilation=True,
        use_mock_autopopulation=use_mock_autopopulation,
    )


# =============================================================================
# WORKFLOW STATE HELPERS
# =============================================================================

def _display_dict_from_nested(state_values: Any) -> Dict[str, Any]:
    """
    Build a display dict from nested workflow state only.
    Reads from input, data, template, post_process, meta, and top-level keys.
    """
    if state_values is None:
        return {}
    if hasattr(state_values, "model_dump"):
        d = state_values.model_dump()
    elif isinstance(state_values, dict):
        d = dict(state_values)
    else:
        return {}
    inp = d.get("input") or {}
    dat = d.get("data") or {}
    t = d.get("template") or {}
    meta = d.get("meta") or {}
    post = d.get("post_process") or {}
    ec = d.get("execution_config")

    def _get(obj: Any, key: str, default: Any = None) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    result = {
        **d,
        "business_name": _get(inp, "business_name"),
        "business_id": _get(inp, "business_id"),
        "website_intention": _get(inp, "website_intention"),
        "website_tone": _get(inp, "website_tone"),
        "sector": _get(dat, "derived_sector") or _get(inp, "sector"),
        "palette": _get(inp, "palette"),
        "font_family": _get(inp, "font_family"),
        "campaign_intent": _get(dat, "campaign_intent"),
        "business_info": _get(dat, "business_info"),
        "trade_classification_result": _get(dat, "trade_classification_result"),
        "templates": _get(t, "templates"),
        "refined_templates": _get(t, "refined_templates"),
        "template_evaluations": _get(t, "template_evaluations"),
        "html_compilation_results": _get(post, "html_compilation_results"),
        "template_compilation_results": _get(post, "template_compilation_results"),
        "screenshot_capture_results": _get(post, "screenshot_capture_results"),
        "query_hash": _get(meta, "query_hash"),
        "model_used": _get(meta, "model_used"),
    }
    if ec is not None:
        reflection = _get(ec, "reflection")
        result["enable_reflection"] = _get(reflection, "enable_reflection", False) if reflection is not None else False
    return result


def get_html_url_from_state(workflow, request_id: str, workflow_config: Dict[str, Any]) -> Optional[str]:
    """Extract HTML URL from workflow state (nested state only)."""
    config = {"configurable": {"thread_id": request_id, **workflow_config}}
    state = workflow.graph.get_state(config)
    if not state or not state.values:
        return None
    display = _display_dict_from_nested(state.values)
    html_results = display.get("html_compilation_results") or {}
    return html_results.get("compiled_html_s3_url") if isinstance(html_results, dict) else None


def get_workflow_state(workflow, request_id: str, workflow_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Get workflow state from checkpoint as a display dict (from nested state only)."""
    config = {"configurable": {"thread_id": request_id, **workflow_config}}
    state = workflow.graph.get_state(config)
    if not state or not state.values:
        return None
    return _display_dict_from_nested(state.values)


# =============================================================================
# PRINTING HELPERS
# =============================================================================

def print_workflow_header(title: str, request_id: str = None, **kwargs):
    """Print a consistent workflow header."""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)
    
    if request_id:
        print(f"📋 Request ID: {request_id}")
    
    for key, value in kwargs.items():
        if value is not None:
            print(f"   {key.replace('_', ' ').title()}: {value}")


def print_workflow_results(workflow, request_id: str, workflow_config: Dict[str, Any], show_details: bool = True):
    """Display workflow results in a consistent format."""
    state = get_workflow_state(workflow, request_id, workflow_config)
    
    if not state:
        print("❌ No state found for this request_id")
        return None
    
    if show_details:
        print("\n📊 WORKFLOW RESULTS")
        print("=" * 60)
        
        # Business data
        if state.get('business_name'):
            print(f"\n🏢 Business: {state.get('business_name')}")
        if state.get('business_id'):
            print(f"   Business ID: {state.get('business_id')}")
        
        # Palette and Font
        palette = state.get('palette', {})
        if palette:
            print(f"\n🎨 Palette: {palette.get('palette_id', 'N/A')}")
        if state.get('font_family'):
            print(f"🔤 Font: {state.get('font_family', 'N/A')}")
        
        # Templates
        templates = state.get('templates') or state.get('refined_templates') or []
        if templates:
            print(f"\n📋 Templates Generated: {len(templates)}")
        
        # Sections
        section_recs = state.get('resolved_template_recommendations', [])
        if section_recs:
            first_rec = section_recs[0]
            sections = first_rec.get('section_mappings', [])
            if sections:
                print(f"📦 Sections Retrieved: {len(sections)}")
    
    # HTML compilation results
    html_results = state.get('html_compilation_results', {})
    if html_results:
        if show_details:
            print(f"\n" + "=" * 60)
            print("🌐 HTML COMPILATION:")
            print("=" * 60)
        print(f"   S3 URL: {html_results.get('compiled_html_s3_url', 'N/A')}")
        if html_results.get('compiled_html_path'):
            print(f"   Local Path: {html_results.get('compiled_html_path', 'N/A')}")
        return html_results.get('compiled_html_s3_url')
    else:
        if show_details:
            print("\n⚠️ No HTML compilation results found")
        return None


# =============================================================================
# WORKFLOW EXECUTION HELPERS
# =============================================================================

async def run_workflow_stream(workflow, stream_kwargs: Dict[str, Any], show_progress: bool = True):
    """Run workflow stream with consistent progress display."""
    if show_progress:
        print("\n🚀 Starting Workflow...")
        print("-" * 50)
    
    async for stream_type, chunk in workflow.stream(**stream_kwargs):
        if stream_type == "updates" and show_progress:
            for node_name, node_output in chunk.items():
                print(f"✅ {node_name}")
    
    if show_progress:
        print("-" * 50)
        print("🎉 Workflow completed!")