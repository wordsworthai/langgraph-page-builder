# nodes/smb/autopop/utils/text_instruction_builder.py
"""
Text Instruction Builder for Content Generation.

Provides 7 separate context builders for different use cases:
1. Tone/voice context - Style guidance for content generation
2. Page context - Which page the content will appear on (homepage or curated page)
3. Business context - Business info for headlines/descriptions
4. Business info + Location context - Factual details (phone, address, coordinates, etc.)
5. Reviews context - Individual reviews for carousels
6. Services context - List of services for service listings
7. Social proof context - Aggregated ratings and review counts
"""

from typing import Dict, Any, Optional, List
from wwai_agent_orchestration.data.providers.business_profile_provider import BusinessProfileProvider
from wwai_agent_orchestration.data.providers.reviews_provider import ReviewsProvider
from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.utils.landing_page_builder.constants import HOMEPAGE_DESCRIPTION
from wwai_agent_orchestration.utils.landing_page_builder.template.curated_options import (
    get_curated_page_by_path,
)
from wwai_agent_orchestration.utils.landing_page_builder.template_utils import get_curated_pages

logger = get_logger(__name__)


# Tone examples data structure
TONE_EXAMPLES = {
    "professional": {
        "headline": "Beautiful outdoor spaces, done right",
        "subheadline": "Professional landscaping services for homes and businesses",
        "cta": "Book a site visit",
        "description": "From precise lawn care to full-scale garden design, we create outdoor spaces that are functional, durable and easy to maintain. Our trained team follows structured processes, clear timelines and transparent pricing so you always know what to expect.",
    },
    "friendly": {
        "headline": "Let's make your yard the best on the block",
        "subheadline": "Down-to-earth landscaping, just around the corner",
        "cta": "Start your yard glow-up",
        "description": "We listen to how you use your outdoor space and turn it into a place you actually enjoy spending time in. No jargon, no drama - just a friendly crew that shows up on time and cleans up before we leave.",
    },
    "bold": {
        "headline": "Turn your lawn into the best investment on your street",
        "subheadline": "High-impact landscaping that boosts curb appeal and property value",
        "cta": "Get my instant Quote",
        "description": "Stop losing value to an average yard. Our landscape makeovers are designed to impress buyers, delight guests and reduce maintenance costs. From concept to completion, we move fast and deliver results you can see from the curb.",
    },
    "minimal": {
        "headline": "A quiet retreat, right outside your door",
        "subheadline": "Thoughtful landscaping for peaceful outdoor living",
        "cta": "Design my peaceful garden",
        "description": "We design soft, balanced landscapes that feel restful the moment you step outside. Gentle lines, low-maintenance plants and subtle lighting come together to create an outdoor space that invites you to slow down and breathe.",
    }
}


def _fetch_business_profile(business_id: str) -> Dict[str, Any]:
    """Helper to fetch and convert business profile to dict."""
    try:
        business_profile_provider = BusinessProfileProvider()
        business_profile = business_profile_provider.get_by_business_id(business_id)
        
        # Convert to dict if it's a Pydantic model
        if hasattr(business_profile, 'model_dump'):
            return business_profile.model_dump()
        elif hasattr(business_profile, 'dict'):
            return business_profile.dict()
        return business_profile
    except Exception as e:
        logger.error(f"Failed to fetch business profile: {e}")
        raise Exception(f"Failed to fetch business profile for business_id={business_id}: {e}")


def _fetch_reviews(business_id: str) -> Optional[Dict[str, Any]]:
    """Helper to fetch and convert reviews to dict."""
    try:
        reviews_provider = ReviewsProvider()
        reviews_data = reviews_provider.get_by_business_id(business_id)
        
        # Convert to dict if it's a Pydantic model
        if hasattr(reviews_data, 'model_dump'):
            return reviews_data.model_dump()
        elif hasattr(reviews_data, 'dict'):
            return reviews_data.dict()
        return reviews_data
    except Exception as e:
        logger.warning(f"Failed to fetch reviews (returning None): {e}")
        return None


# ============================================================================
# 1. TONE/VOICE CONTEXT
# ============================================================================

# Tone-specific instructions
TONE_INSTRUCTIONS = {
    "professional": {
        "description": "Clear, confident, and polished language that builds trust and credibility.",
        "guidelines": [
            "Use formal, polished language with proper grammar and structure",
            "Focus on expertise, reliability, and proven results",
            "Emphasize professionalism, quality, and attention to detail",
            "Use confident statements without being overly casual",
            "Highlight credentials, experience, and structured processes",
            "Avoid slang, contractions, or overly casual expressions",
            "Use clear, direct language that conveys competence",
            "Include specific details about processes, timelines, and guarantees"
        ],
        "headline_style": "Clear, benefit-focused headlines that emphasize expertise and results",
        "cta_style": "Professional action words like 'Schedule', 'Request', 'Contact', 'Learn More'"
    },
    "friendly": {
        "description": "Warm, welcoming, and conversational tone that feels approachable.",
        "guidelines": [
            "Use warm, conversational language that feels personal and approachable",
            "Write as if speaking to a friend or neighbor",
            "Use contractions and natural, everyday language",
            "Show personality and genuine care for the customer",
            "Avoid jargon or overly technical terms",
            "Use inclusive language like 'we', 'us', 'together'",
            "Include friendly expressions and a welcoming attitude",
            "Focus on relationships, community, and making customers feel comfortable"
        ],
        "headline_style": "Warm, inviting headlines that feel personal and approachable",
        "cta_style": "Friendly, casual action words like 'Let's', 'Start', 'Get Started', 'Join Us'"
    },
    "bold": {
        "description": "Strong, energetic, and attention-grabbing statements that stand out.",
        "guidelines": [
            "Use powerful, assertive language that commands attention",
            "Create urgency and emphasize impact and results",
            "Use strong action verbs and dynamic language",
            "Make bold claims backed by confidence",
            "Use shorter, punchier sentences for impact",
            "Emphasize transformation, results, and value",
            "Use numbers, statistics, and concrete outcomes when possible",
            "Create a sense of opportunity and forward momentum"
        ],
        "headline_style": "Bold, impactful headlines that grab attention and create urgency",
        "cta_style": "Strong, action-oriented CTAs like 'Get Started Now', 'Claim Your Spot', 'Transform Today'"
    },
    "minimal": {
        "description": "Clean, concise, and to-the-point messaging with zero fluff.",
        "guidelines": [
            "Use simple, clear language with no unnecessary words",
            "Focus on essential information only",
            "Use short sentences and clean structure",
            "Avoid flowery language or excessive adjectives",
            "Let the message speak for itself without embellishment",
            "Use white space in thinking - one idea per sentence",
            "Focus on clarity and simplicity above all",
            "Emphasize peace, balance, and thoughtful design"
        ],
        "headline_style": "Simple, direct headlines that communicate clearly without excess",
        "cta_style": "Clean, simple CTAs like 'Begin', 'Explore', 'Discover', 'Start'"
    }
}


def build_tone_context(website_tone: str, website_intention: str) -> str:
    """
    Build tone/voice context for content generation.
    
    Provides concise style guidance for how content should be written.
    This guides what the page is about and what kind of content should be generated.
    
    Args:
        website_tone: One of: "professional", "friendly", "bold", "minimal"
        website_intention: Website goal (e.g., "generate_leads", "showcase_services")
        
    Returns:
        Formatted string with tone instructions and intention guidance
    """
    tone_lower = website_tone.lower()
    
    if tone_lower not in TONE_INSTRUCTIONS:
        logger.warning(f"Unknown tone '{website_tone}', defaulting to 'professional'")
        tone_lower = "professional"
    
    instructions = TONE_INSTRUCTIONS[tone_lower]
    examples = TONE_EXAMPLES.get(tone_lower, {})
    
    lines = []
    lines.append(f"Tone: {tone_lower.upper()} | Intention: {website_intention}")
    lines.append(f"Style: {instructions['description']}")
    lines.append("")
    lines.append("Guidelines:")
    # Keep only top 5 most important guidelines to save tokens
    for guideline in instructions['guidelines'][:5]:
        lines.append(f"- {guideline}")
    
    lines.append("")
    lines.append(f"Headlines: {instructions['headline_style']}")
    lines.append(f"CTAs: {instructions['cta_style']}")
    
    # Include one concise example
    if examples:
        lines.append("")
        lines.append("Example:")
        lines.append(f"Headline: {examples.get('headline', 'N/A')}")
        lines.append(f"CTA: {examples.get('cta', 'N/A')}")
    
    return "\n".join(lines)


# ============================================================================
# 2. PAGE CONTEXT (which page the content will appear on)
# ============================================================================

def _page_type_to_display_name(page_type: str) -> str:
    """Convert page_type to human-readable display name."""
    if not page_type or (page_type or "").strip().lower() in ("", "/", "homepage"):
        return "Homepage"
    s = (page_type or "").strip().lstrip("/").replace("-", " ").strip()
    return s.title() if s else "Page"


def build_page_context(page_type: str = "homepage") -> str:
    """
    Build page context for content generation.

    Tells content agents which page the generated content will appear on,
    with page-specific guidelines from constants (homepage) or DB (curated pages).

    Args:
        page_type: "homepage" or a path like "/services", "contact-us", "/about"

    Returns:
        Formatted string with page context and guidelines
    """
    page_type = (page_type or "").strip() or "homepage"
    page_type_lower = page_type.lower()

    # Homepage: use HOMEPAGE_DESCRIPTION from constants
    if page_type_lower in ("", "/", "homepage"):
        return f"Page context (Homepage):\n{HOMEPAGE_DESCRIPTION.strip()}"

    # Curated pages: lookup from DB
    curated_page = get_curated_page_by_path(page_type)
    if curated_page:
        page_title = curated_page.page_title or _page_type_to_display_name(page_type)
        if curated_page.page_description and curated_page.page_description.strip():
            return f"Page context ({page_title}):\n{curated_page.page_description.strip()}"
        return (
            f"Page context ({page_title}):\n"
            f"This content will be used on the {page_title} page. "
            "Tailor your copy to fit this page's purpose."
        )

    # Unknown path: derive display name and use fallback
    display_name = _page_type_to_display_name(page_type)
    return (
        f"Page context ({display_name}):\n"
        f"This content will be used on the {display_name} page. "
        "Tailor your copy to fit this page's purpose."
    )


# ============================================================================
# 2b. NAV CONTEXT (for header/footer sections)
# ============================================================================

def build_nav_context(
    section_mappings: List[Dict[str, Any]],
    page_type: str,
    business_id: str,
    website_tone: str,
    website_intention: str,
) -> str:
    """
    Build navigation context for header/footer sections.

    Lighter context than full data_context: curated pages, template sections (L0/L1),
    business info + location, and minimal tone. Used for nav links and footer contact info.

    Args:
        section_mappings: List of section mappings from resolved_template_recommendations
        page_type: "homepage" or curated page path
        business_id: Business ID for business info lookup
        website_tone: Tone for nav label style
        website_intention: Intention for context

    Returns:
        Formatted string for header/footer content generation
    """
    lines = []
    lines.append("Navigation context (for header/footer):")
    lines.append(
        "This content will appear in a navigation or footer section. "
        "Use for links, labels, and contact info."
    )
    lines.append("")

    # Minimal tone (first 2 lines from tone context)
    try:
        tone_context = build_tone_context(website_tone, website_intention)
        tone_lines = tone_context.strip().split("\n")[:2]
        if tone_lines:
            lines.extend(tone_lines)
            lines.append("")
    except Exception as e:
        logger.warning(f"Failed to build tone for nav context: {e}")

    # Curated pages (skip homepage)
    try:
        response = get_curated_pages()
        pages = [p for p in response.pages if (p.page_path or "").strip().lower() not in ("", "/", "homepage")]
        if pages:
            lines.append("Available pages (for nav links):")
            for p in pages:
                path = (p.page_path or "").strip() or "/"
                title = p.page_title or path.lstrip("/").replace("-", " ").title()
                lines.append(f"- {title}: {path}")
            lines.append("")
        else:
            lines.append("Available pages: No additional pages (homepage only).")
            lines.append("")
    except Exception as e:
        logger.warning(f"Failed to fetch curated pages for nav context: {e}")
        lines.append("Available pages: (unavailable)")
        lines.append("")

    # Template sections (L0/L1 for in-page anchor links)
    if section_mappings:
        lines.append("Sections in this page (for in-page anchor links):")
        for m in section_mappings:
            l0 = m.get("section_l0", "") or ""
            l1 = m.get("section_l1", "") or ""
            sid = m.get("section_id", "") or ""
            display = f"{l0} - {l1}" if l1 else (l0 or sid)
            lines.append(f"- {display}")
        lines.append("")
    else:
        lines.append("Sections in this page: (none)")
        lines.append("")

    # Business info + location (for footer)
    try:
        biz_loc = build_business_info_and_location_context(business_id)
        lines.append(biz_loc.strip())
    except Exception as e:
        logger.warning(f"Failed to build business info for nav context: {e}")
        lines.append("=== BUSINESS INFO & LOCATION ===")
        lines.append("(unavailable)")

    return "\n".join(lines)


# ============================================================================
# 3. BUSINESS CONTEXT (for content generation)
# ============================================================================

def build_business_context(business_id: str) -> str:
    """
    Build business context for content generation (headlines, descriptions).
    
    Provides information about what the business does, their specialties,
    and their value proposition. Used to generate compelling headlines and descriptions.
    
    Args:
        business_id: Business ID to fetch data for
        
    Returns:
        Formatted string with business context for content generation
    """
    business_profile = _fetch_business_profile(business_id)
    
    lines = []
    lines.append("=== BUSINESS CONTEXT ===")
    
    if business_profile.get("business_name"):
        lines.append(f"Business Name: {business_profile['business_name']}")
    
    if business_profile.get("display_name"):
        lines.append(f"Display Name: {business_profile['display_name']}")
    
    if business_profile.get("tagline"):
        lines.append(f"Tagline: {business_profile['tagline']}")
    
    if business_profile.get("description"):
        lines.append(f"\nDescription:\n{business_profile['description']}")
    
    if business_profile.get("specialties"):
        lines.append(f"\nSpecialties:\n{business_profile['specialties']}")
    
    if business_profile.get("categories"):
        categories = business_profile["categories"]
        if isinstance(categories, list):
            lines.append(f"\nCategories: {', '.join(categories)}")
        else:
            lines.append(f"Categories: {categories}")
    
    if business_profile.get("industry"):
        lines.append(f"Industry: {business_profile['industry']}")
    
    if business_profile.get("primary_category"):
        lines.append(f"Primary Category: {business_profile['primary_category']}")
    
    if business_profile.get("year_established"):
        lines.append(f"\nYear Established: {business_profile['year_established']}")
    
    lines.append("\nUse this information to generate compelling headlines, subheadlines, and descriptions that accurately represent the business.")
    
    return "\n".join(lines)


# ============================================================================
# 4. BUSINESS INFO + LOCATION CONTEXT (combined)
# ============================================================================

def build_business_info_and_location_context(business_id: str) -> str:
    """
    Build business info and location context for factual details.
    
    Provides contact information, address, coordinates, and operational details.
    Used to populate forms, contact sections, and map components.
    
    Args:
        business_id: Business ID to fetch data for
        
    Returns:
        Formatted string with business info and location data
    """
    business_profile = _fetch_business_profile(business_id)
    
    lines = []
    lines.append("=== BUSINESS INFO & LOCATION ===")
    
    # Contact Information
    contact_info = []
    if business_profile.get("phone"):
        contact_info.append(f"Phone: {business_profile['phone']}")
    if business_profile.get("email"):
        contact_info.append(f"Email: {business_profile['email']}")
    if business_profile.get("website_url"):
        contact_info.append(f"Website: {business_profile['website_url']}")
    if contact_info:
        lines.append("Contact Information:")
        lines.extend(contact_info)
        lines.append("")
    
    # Address
    address = business_profile.get("address")
    if address:
        address_parts = []
        if isinstance(address, dict):
            if address.get("street"):
                address_parts.append(address["street"])
            if address.get("city"):
                address_parts.append(address["city"])
            if address.get("state"):
                address_parts.append(address["state"])
            if address.get("zip"):
                address_parts.append(address["zip"])
        if address_parts:
            lines.append(f"Address: {', '.join(address_parts)}")
    
    if business_profile.get("formatted_address"):
        lines.append(f"Formatted Address: {business_profile['formatted_address']}")
    
    # Coordinates (for map embedding)
    coordinates = business_profile.get("coordinates")
    if coordinates:
        if isinstance(coordinates, dict):
            lat = coordinates.get("lat")
            lng = coordinates.get("lng")
            if lat is not None and lng is not None:
                lines.append(f"\nCoordinates (for map embedding):")
                lines.append(f"  Latitude: {lat}")
                lines.append(f"  Longitude: {lng}")
        else:
            lines.append(f"Coordinates: {coordinates}")
    
    # Map URLs
    if business_profile.get("google_maps_url"):
        lines.append(f"\nGoogle Maps URL: {business_profile['google_maps_url']}")
    if business_profile.get("yelp_url"):
        lines.append(f"Yelp URL: {business_profile['yelp_url']}")
    
    # Hours
    hours = business_profile.get("hours")
    if hours:
        if isinstance(hours, list):
            lines.append("\nOperating Hours:")
            for day_hours in hours:
                if isinstance(day_hours, dict):
                    day = day_hours.get("day", "")
                    hours_str = day_hours.get("hours", "")
                    lines.append(f"  {day}: {hours_str}")
                else:
                    lines.append(f"  {day_hours}")
        else:
            lines.append(f"\nHours: {hours}")
    
    # Operational Status
    if business_profile.get("is_operational") is not None:
        lines.append(f"\nOperational Status: {'Open' if business_profile['is_operational'] else 'Closed'}")
    
    # Price Level
    if business_profile.get("price_level"):
        lines.append(f"Price Level: {business_profile['price_level']}")
    
    lines.append("\nUse this information to populate contact forms, address fields, and map components.")
    
    return "\n".join(lines)


# ============================================================================
# 5. REVIEWS CONTEXT (for review carousels)
# ============================================================================

def build_reviews_context(business_id: str, max_reviews: int = 20) -> str:
    """
    Build reviews context for review carousels.
    
    Provides individual customer reviews with ratings, text, and author information.
    Used to populate review carousel components.
    
    Args:
        business_id: Business ID to fetch reviews for
        max_reviews: Maximum number of reviews to include (default: 20)
        
    Returns:
        Formatted string with reviews data
    """
    reviews_data = _fetch_reviews(business_id)
    
    lines = []
    lines.append("=== CUSTOMER REVIEWS ===")
    
    if not reviews_data:
        lines.append("No reviews available.")
        return "\n".join(lines)
    
    reviews_list = reviews_data.get("reviews", [])
    if not reviews_list:
        lines.append("No reviews available.")
        return "\n".join(lines)
    
    lines.append(f"Total Reviews: {len(reviews_list)}")
    lines.append("")
    
    # Include reviews (limit to avoid overwhelming)
    for i, review in enumerate(reviews_list[:max_reviews], 1):
        lines.append(f"Review {i}:")
        
        # Rating
        if review.get("rating"):
            lines.append(f"  Rating: {review['rating']}/5.0")
        
        # Review text (body) - this is the main content
        review_text = review.get("body") or review.get("text")  # Support both field names
        if review_text:
            lines.append(f"  Review Text: {review_text}")
        
        # Author name
        author = review.get("author") or review.get("author_name")  # Support both field names
        if author:
            lines.append(f"  Author: {author}")
        
        # Title (if available)
        if review.get("title"):
            lines.append(f"  Title: {review['title']}")
        
        # Source/provider
        source = review.get("review_provider") or review.get("source")  # Support both field names
        if source:
            lines.append(f"  Source: {source}")
        
        # Location (if available)
        if review.get("location"):
            lines.append(f"  Location: {review['location']}")
        
        # Date/timestamp
        if review.get("review_timestamp"):
            lines.append(f"  Date: {review['review_timestamp']}")
        elif review.get("date"):
            lines.append(f"  Date: {review['date']}")
        
        lines.append("")
    
    if len(reviews_list) > max_reviews:
        lines.append(f"... and {len(reviews_list) - max_reviews} more reviews")
    
    lines.append("\nUse these reviews to populate review carousel components.")
    
    return "\n".join(lines)


# ============================================================================
# 6. SERVICES CONTEXT (for service listings)
# ============================================================================

def build_services_context(business_id: str) -> str:
    """
    Build services context for service listings/sections.
    
    Provides a list of services offered by the business.
    Uses services list if available, otherwise falls back to categories.
    Used to populate service listing sections and service cards.
    
    Args:
        business_id: Business ID to fetch data for
        
    Returns:
        Formatted string with services list
    """
    business_profile = _fetch_business_profile(business_id)
    
    lines = []
    lines.append("=== SERVICES ===")
    
    services = business_profile.get("services", [])
    categories = business_profile.get("categories", [])
    
    # Use services if available, otherwise use categories
    if services and isinstance(services, list) and len(services) > 0:
        service_list = services
        source = "services"
    elif categories and isinstance(categories, list) and len(categories) > 0:
        service_list = categories
        source = "categories"
    else:
        lines.append("No services or categories listed.")
        return "\n".join(lines)
    
    lines.append(f"Total {source.capitalize()}: {len(service_list)}")
    lines.append("")
    for i, service in enumerate(service_list, 1):
        lines.append(f"{i}. {service}")
    
    lines.append("\nUse this list to populate service listing sections and service cards.")
    
    return "\n".join(lines)


# ============================================================================
# 7. SOCIAL PROOF CONTEXT (aggregated ratings)
# ============================================================================

def build_social_proof_context(business_id: str) -> str:
    """
    Build social proof context with aggregated ratings and review counts.
    
    Provides overall ratings and review counts from Google and Yelp.
    Used to display trust indicators, badges, and aggregated social proof.
    
    Args:
        business_id: Business ID to fetch data for
        
    Returns:
        Formatted string with aggregated ratings and review counts
    """
    business_profile = _fetch_business_profile(business_id)
    
    lines = []
    lines.append("=== SOCIAL PROOF ===")
    
    # Google Ratings
    google_rating = business_profile.get("google_rating")
    google_review_count = business_profile.get("google_review_count", 0)
    if google_rating is not None:
        lines.append(f"Google Rating: {google_rating}/5.0")
        lines.append(f"Google Review Count: {google_review_count}")
        lines.append("")
    
    # Yelp Ratings
    yelp_rating = business_profile.get("yelp_rating")
    yelp_review_count = business_profile.get("yelp_review_count", 0)
    if yelp_rating is not None:
        lines.append(f"Yelp Rating: {yelp_rating}/5.0")
        lines.append(f"Yelp Review Count: {yelp_review_count}")
        lines.append("")
    
    # Calculate average if both exist
    ratings = []
    if google_rating is not None:
        ratings.append(google_rating)
    if yelp_rating is not None:
        ratings.append(yelp_rating)
    
    if ratings:
        avg_rating = sum(ratings) / len(ratings)
        total_reviews = google_review_count + yelp_review_count
        lines.append(f"Average Rating: {avg_rating:.1f}/5.0")
        lines.append(f"Total Reviews: {total_reviews}")
    
    if not google_rating and not yelp_rating:
        lines.append("No ratings available.")
    
    lines.append("\nUse this information to display trust indicators, rating badges, and social proof elements.")
    
    return "\n".join(lines)
