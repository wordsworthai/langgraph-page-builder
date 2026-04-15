# nodes/smb/autopop/content_nodes/content_data_context_fetcher.py
"""
Content Data Context Fetcher Node.

Fetches and builds all context data for content generation:
- Tone/voice context
- Page context (which page the content will appear on)
- Business context
- Business info + location context
- Reviews context
- Services context
- Social proof context

Stores the concatenated context in state for use by content text agents.
"""

from typing import Any, Dict
from langgraph.types import RunnableConfig

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils.text_instruction_builder import (
    build_tone_context,
    build_page_context,
    build_nav_context,
    build_business_context,
    build_business_info_and_location_context,
    build_reviews_context,
    build_services_context,
    build_social_proof_context
)

logger = get_logger(__name__)


@NodeRegistry.register(
    name="content_data_context_fetcher",
    description="Fetch and build all context data for content generation",
    max_retries=1,
    timeout=60,
    tags=["content", "context", "data-fetch"],
    show_node=False,
)
def content_data_context_fetcher_node(
    state: LandingPageWorkflowState,
    config: RunnableConfig = None
) -> Dict[str, Any]:
    """
    Fetch and build all context data for content generation.
    
    This node:
    1. Fetches all 7 context types (tone, page, business, info+location, reviews, services, social proof)
    2. Concatenates them into a single data_context string
    3. Stores it in autopopulation_langgraph_state.meta for use by content agents
    
    Args:
        state: LandingPageWorkflowState with state.input (business_id, website_tone, website_intention, page_type)
        config: Node configuration
        
    Returns:
        Dict with updated autopopulation_langgraph_state containing data_context
    """
    inp = state.input
    business_id = inp.business_id if inp else None
    website_tone = inp.website_context.website_tone if inp else None
    website_intention = inp.website_context.website_intention if inp else None
    page_type = (getattr(inp, "page_type", "homepage") or "homepage") if inp else "homepage"

    if not business_id:
        logger.warning("No business_id in state, skipping context fetch")
        return {}
    
    if not website_tone:
        logger.warning("No website_tone in state, using default 'professional'")
        website_tone = "professional"
    
    if not website_intention:
        logger.warning("No website_intention in state, using default 'generate_leads'")
        website_intention = "generate_leads"
    
    logger.info(
        "Fetching content data context",
        business_id=business_id,
        website_tone=website_tone,
        website_intention=website_intention,
        page_type=page_type
    )
    
    # Build all context types
    context_parts = []
    
    try:
        # 1. Tone/voice context
        tone_context = build_tone_context(website_tone, website_intention)
        context_parts.append(tone_context)
        logger.debug("Built tone context")
    except Exception as e:
        logger.error(f"Failed to build tone context: {e}")
    
    try:
        # 2. Page context (which page the content will appear on)
        page_context = build_page_context(page_type)
        context_parts.append(page_context)
        logger.debug("Built page context")
    except Exception as e:
        logger.error(f"Failed to build page context: {e}")
    
    try:
        # 3. Business context (for content generation)
        business_context = build_business_context(business_id)
        context_parts.append(business_context)
        logger.debug("Built business context")
    except Exception as e:
        logger.error(f"Failed to build business context: {e}")
    
    try:
        # 4. Business info + location context
        business_info_context = build_business_info_and_location_context(business_id)
        context_parts.append(business_info_context)
        logger.debug("Built business info and location context")
    except Exception as e:
        logger.error(f"Failed to build business info context: {e}")
    
    try:
        # 5. Reviews context
        reviews_context = build_reviews_context(business_id, max_reviews=10)
        context_parts.append(reviews_context)
        logger.debug("Built reviews context")
    except Exception as e:
        logger.warning(f"Failed to build reviews context (continuing): {e}")
    
    try:
        # 6. Services context
        services_context = build_services_context(business_id)
        context_parts.append(services_context)
        logger.debug("Built services context")
    except Exception as e:
        logger.warning(f"Failed to build services context (continuing): {e}")
    
    try:
        # 7. Social proof context
        social_proof_context = build_social_proof_context(business_id)
        context_parts.append(social_proof_context)
        logger.debug("Built social proof context")
    except Exception as e:
        logger.warning(f"Failed to build social proof context (continuing): {e}")
    
    # Concatenate all contexts
    data_context = "\n\n".join(context_parts)
    
    # Build nav context (for header/footer sections): curated pages, L0/L1, business info+location
    data_context_nav = ""
    resolved = state.resolved_template_recommendations or []
    section_mappings = resolved[0].get("section_mappings", []) if resolved else []
    try:
        data_context_nav = build_nav_context(
            section_mappings=section_mappings,
            page_type=page_type,
            business_id=business_id,
            website_tone=website_tone,
            website_intention=website_intention,
        )
        logger.debug("Built nav context for header/footer")
    except Exception as e:
        logger.warning(f"Failed to build nav context (continuing): {e}")
        data_context_nav = (
            "Navigation context (for header/footer):\n"
            "This content will appear in a navigation or footer section. "
            "Use for links, labels, and contact info."
        )
    
    logger.info(
        "Content data context built successfully",
        context_length=len(data_context),
        context_parts_count=len(context_parts)
    )
    
    # Store in autopopulation_langgraph_state.meta
    # Initialize if it doesn't exist
    current_autopop_state = state.autopopulation_langgraph_state or {}
    current_meta = current_autopop_state.get("meta", {})
    
    # Update meta with data_context and data_context_nav
    updated_meta = {
        **current_meta,
        "data_context": data_context,
        "data_context_nav": data_context_nav
    }
    
    # Return updated state
    return {
        "autopopulation_langgraph_state": {
            **current_autopop_state,
            "meta": updated_meta
        }
    }
