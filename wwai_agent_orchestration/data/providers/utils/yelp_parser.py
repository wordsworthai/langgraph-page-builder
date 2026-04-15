# data_providers/utils/yelp_parser.py
"""
Yelp data parsing utilities.

Handles all heavy transformation from raw API/DB data to clean YelpOutput.
"""

from wwai_agent_orchestration.core.observability.logger import get_logger
from typing import Optional, List, Dict, Any

from wwai_agent_orchestration.data.providers.models.yelp import YelpOutput

logger = get_logger(__name__)


# =============================================================================
# SECTOR MAPPING
# =============================================================================

YELP_CATEGORY_TO_SECTOR: Dict[str, str] = {
    # Food & Beverage
    "restaurants": "food-beverage",
    "food": "food-beverage",
    "bars": "food-beverage",
    "cafes": "food-beverage",
    "bakeries": "food-beverage",
    "coffee": "food-beverage",
    "breakfast": "food-beverage",
    "brunch": "food-beverage",
    
    # Retail
    "shopping": "retail",
    "fashion": "retail",
    "clothing": "retail",
    "electronics": "retail",
    "furniture": "retail",
    "jewelry": "retail",
    "books": "retail",
    
    # Beauty & Wellness
    "beauty": "beauty-wellness",
    "hair": "beauty-wellness",
    "salon": "beauty-wellness",
    "spa": "beauty-wellness",
    "fitness": "beauty-wellness",
    "gym": "beauty-wellness",
    "yoga": "beauty-wellness",
    "massage": "beauty-wellness",
    "nails": "beauty-wellness",
    
    # Professional Services
    "lawyers": "professional-services",
    "legal": "professional-services",
    "accountants": "professional-services",
    "financial": "professional-services",
    "realestate": "professional-services",
    "insurance": "professional-services",
    
    # Healthcare
    "health": "healthcare",
    "medical": "healthcare",
    "dentists": "healthcare",
    "doctors": "healthcare",
    "pharmacy": "healthcare",
    "hospitals": "healthcare",
    
    # Home Services
    "homeservices": "home-services",
    "plumbing": "home-services",
    "electricians": "home-services",
    "contractors": "home-services",
    "hvac": "home-services",
    "roofing": "home-services",
    "locksmiths": "home-services",
    "movers": "home-services",
    "cleaning": "home-services",
    
    # Automotive
    "auto": "automotive",
    "automotive": "automotive",
    "carwash": "automotive",
    "autodealers": "automotive",
    "autorepair": "automotive",
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def split_comma_separated(value: Optional[str]) -> List[str]:
    """
    Split comma-separated string into clean list.
    
    Args:
        value: Comma-separated string or None
        
    Returns:
        List of stripped strings
    """
    if not value:
        return []
    
    return [item.strip() for item in value.split(",") if item.strip()]


def safe_float(value: Any) -> Optional[float]:
    """
    Safely convert value to float.
    
    Args:
        value: Value to convert (could be string, int, float, or None)
        
    Returns:
        Float value or None
    """
    if value is None:
        return None
    
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def safe_int(value: Any) -> Optional[int]:
    """
    Safely convert value to int.
    
    Args:
        value: Value to convert (could be string, int, or None)
        
    Returns:
        Int value or None
    """
    if value is None:
        return None
    
    try:
        # Handle string that might be float (e.g., "4.5")
        return int(float(value))
    except (ValueError, TypeError):
        return None


def derive_sector_from_yelp(categories: List[str]) -> Optional[str]:
    """
    Derive business sector from Yelp categories.
    
    Args:
        categories: List of Yelp category strings
        
    Returns:
        Sector string or None
    """
    for category in categories:
        # Normalize category for matching
        cat_lower = category.lower().strip()
        cat_no_spaces = cat_lower.replace(" ", "")
        
        # Try exact match first
        if cat_lower in YELP_CATEGORY_TO_SECTOR:
            return YELP_CATEGORY_TO_SECTOR[cat_lower]
        
        if cat_no_spaces in YELP_CATEGORY_TO_SECTOR:
            return YELP_CATEGORY_TO_SECTOR[cat_no_spaces]
        
        # Try partial match (category contains key)
        for key, sector in YELP_CATEGORY_TO_SECTOR.items():
            if key in cat_lower or key in cat_no_spaces:
                return sector
    
    return None


# =============================================================================
# API RESPONSE PARSING
# =============================================================================

def parse_yelp_api_response(api_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse raw Yelp RapidAPI response into normalized dict.
    
    This handles the specific structure returned by the Yelp Business API.
    
    Args:
        api_response: Raw response from RapidAPI (business_details)
        
    Returns:
        Normalized dict ready for YelpOutput conversion
    """
    biz = api_response
    
    # Extract service offerings
    services = []
    service_offering = biz.get("service_offering", {})
    if service_offering:
        business_services = service_offering.get("business_services", [])
        services = [s.get("name", "") for s in business_services if s.get("name")]
    
    # Extract categories as list
    categories = []
    raw_categories = biz.get("categories", [])
    if raw_categories:
        categories = [cat.get("name", "") for cat in raw_categories if cat.get("name")]
    
    # Extract from_this_business section
    from_business = biz.get("from_this_business", {})
    
    return {
        # Basic Info
        "yelp_business_id": biz.get("id", ""),
        "business_name": biz.get("name", ""),
        "alias": biz.get("alias", ""),
        "is_closed": biz.get("is_closed", False),
        
        # Ratings & Reviews
        "rating": biz.get("avg_rating"),
        "review_count": biz.get("review_count", 0),
        
        # Contact Info
        "phone": biz.get("phone", ""),
        "localized_phone": biz.get("localized_phone", ""),
        
        # Address
        "address": biz.get("address1", ""),
        "city": biz.get("city", ""),
        "state": biz.get("state", ""),
        "zip": biz.get("zip", ""),
        "full_address": biz.get("localized_address", ""),
        
        # Categories & Services (as lists, not comma-separated)
        "categories": categories,
        "services": services,
        
        # Business Details
        "specialties": from_business.get("specialties", ""),
        "history": from_business.get("history", ""),
        "year_established": from_business.get("year_established"),
        
        # Pricing
        "price": biz.get("price", ""),
        
        # Hours
        "hours": ", ".join(biz.get("localized_hours", [])),
        
        # URLs
        "yelp_url": biz.get("share_url", ""),
        "website": biz.get("display_url", ""),
    }


# =============================================================================
# MAIN PARSING FUNCTION
# =============================================================================

def parse_yelp_data(
    raw_data: Dict[str, Any],
    from_api: bool = False
) -> YelpOutput:
    """
    Parse raw Yelp data into clean YelpOutput.
    
    This is the main transformation function that handles all the heavy lifting.
    Handles both DB format (with 'value' wrapper) and direct dict format.
    
    Args:
        raw_data: Raw data from DB or parsed API response
        from_api: Whether this data was freshly scraped from API
        
    Returns:
        YelpOutput with all fields properly extracted and transformed
    """
    # Handle categories - could be list or comma-separated string
    categories_raw = raw_data.get("categories", [])
    if isinstance(categories_raw, str):
        categories = split_comma_separated(categories_raw)
    elif isinstance(categories_raw, list):
        categories = categories_raw
    else:
        categories = []
    
    # Handle services - could be list or comma-separated string
    services_raw = raw_data.get("services", raw_data.get("services_offered", []))
    if isinstance(services_raw, str):
        services = split_comma_separated(services_raw)
    elif isinstance(services_raw, list):
        services = services_raw
    else:
        services = []
    
    # Derive sector from categories
    derived_sector = derive_sector_from_yelp(categories)
    
    # Convert rating to float
    rating = safe_float(raw_data.get("rating"))
    
    # Convert year_established to int
    year_established = safe_int(raw_data.get("year_established"))
    
    return YelpOutput(
        yelp_business_id=raw_data.get("yelp_business_id") or raw_data.get("business_id"),
        business_name=raw_data.get("business_name", "Unknown"),
        alias=raw_data.get("alias"),
        categories=categories,
        derived_sector=derived_sector,
        rating=rating,
        review_count=raw_data.get("review_count"),
        price=raw_data.get("price"),
        phone=raw_data.get("phone"),
        localized_phone=raw_data.get("localized_phone"),
        website=raw_data.get("website") or raw_data.get("business_website"),
        yelp_url=raw_data.get("yelp_url"),
        address=raw_data.get("address") or raw_data.get("address1"),
        city=raw_data.get("city"),
        state=raw_data.get("state"),
        zip=raw_data.get("zip"),
        full_address=raw_data.get("full_address"),
        specialties=raw_data.get("specialties"),
        history=raw_data.get("history"),
        services=services,
        year_established=year_established,
        hours=raw_data.get("hours") or raw_data.get("localized_hours"),
        is_closed=raw_data.get("is_closed", False),
        from_api=from_api,
    )