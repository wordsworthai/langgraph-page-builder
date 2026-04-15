# data_providers/utils/google_maps_parser.py
"""
Google Maps data parsing utilities.

Handles all heavy transformation from raw DB/API data to clean GoogleMapsOutput.
"""

from wwai_agent_orchestration.core.observability.logger import get_logger
from typing import Optional, List, Dict, Any

from wwai_agent_orchestration.data.providers.models.google_maps import (
    GoogleMapsOutput,
    ReviewSummary,
    Coordinates,
)

logger = get_logger(__name__)


# =============================================================================
# SECTOR MAPPING
# =============================================================================

GOOGLE_TYPE_TO_SECTOR: Dict[str, str] = {
    # Food & Beverage
    "restaurant": "food-beverage",
    "cafe": "food-beverage",
    "bar": "food-beverage",
    "bakery": "food-beverage",
    "meal_takeaway": "food-beverage",
    "meal_delivery": "food-beverage",
    "coffee_shop": "food-beverage",
    "ice_cream_shop": "food-beverage",
    
    # Retail
    "clothing_store": "retail",
    "electronics_store": "retail",
    "furniture_store": "retail",
    "shoe_store": "retail",
    "jewelry_store": "retail",
    "book_store": "retail",
    "store": "retail",
    "shopping_mall": "retail",
    "supermarket": "retail",
    "convenience_store": "retail",
    
    # Beauty & Wellness
    "hair_salon": "beauty-wellness",
    "beauty_salon": "beauty-wellness",
    "spa": "beauty-wellness",
    "gym": "beauty-wellness",
    "fitness_center": "beauty-wellness",
    "nail_salon": "beauty-wellness",
    "hair_care": "beauty-wellness",
    
    # Professional Services
    "lawyer": "professional-services",
    "accounting": "professional-services",
    "real_estate_agency": "professional-services",
    "insurance_agency": "professional-services",
    "financial_planner": "professional-services",
    "consultant": "professional-services",
    
    # Healthcare
    "dentist": "healthcare",
    "doctor": "healthcare",
    "hospital": "healthcare",
    "pharmacy": "healthcare",
    "physiotherapist": "healthcare",
    "veterinary_care": "healthcare",
    "medical_lab": "healthcare",
    
    # Home Services
    "plumber": "home-services",
    "electrician": "home-services",
    "locksmith": "home-services",
    "roofing_contractor": "home-services",
    "general_contractor": "home-services",
    "painter": "home-services",
    "moving_company": "home-services",
    "hvac_contractor": "home-services",
    
    # Automotive
    "car_repair": "automotive",
    "car_dealer": "automotive",
    "car_wash": "automotive",
    "gas_station": "automotive",
    "auto_parts_store": "automotive",
}


# =============================================================================
# PARSING FUNCTIONS
# =============================================================================

def derive_sector_from_google(
    primary_type: Optional[str],
    types: Optional[List[str]] = None
) -> Optional[str]:
    """
    Derive business sector from Google place type.
    
    Args:
        primary_type: Primary Google place type
        types: List of all Google place types (fallback)
        
    Returns:
        Sector string or None
    """
    # Try primary type first
    if primary_type:
        sector = GOOGLE_TYPE_TO_SECTOR.get(primary_type)
        if sector:
            return sector
    
    # Fallback to types list
    if types:
        for t in types:
            sector = GOOGLE_TYPE_TO_SECTOR.get(t)
            if sector:
                return sector
    
    return None


def extract_hours(raw_data: Dict[str, Any]) -> List[str]:
    """
    Extract and format business hours from raw Google data.
    
    Args:
        raw_data: Raw Google Places data
        
    Returns:
        List of formatted hour strings (e.g., ["Monday: 9:00 AM - 5:00 PM"])
    """
    try:
        regular_hours = raw_data.get("regularOpeningHours", {})
        weekday_descriptions = regular_hours.get("weekdayDescriptions", [])
        
        if weekday_descriptions:
            return weekday_descriptions
        
        return []
    except Exception as e:
        logger.warning(f"Failed to extract hours: {e}")
        return []


def extract_reviews(
    raw_data: Dict[str, Any],
    limit: int = 3,
    max_text_length: int = 200
) -> List[ReviewSummary]:
    """
    Extract and clean reviews from raw Google data.
    
    Args:
        raw_data: Raw Google Places data
        limit: Maximum number of reviews to extract
        max_text_length: Maximum length for review text (truncate if longer)
        
    Returns:
        List of ReviewSummary objects
    """
    reviews = []
    
    try:
        raw_reviews = raw_data.get("reviews", [])
        
        for review in raw_reviews[:limit]:
            author_attr = review.get("authorAttribution", {})
            author = author_attr.get("displayName", "Anonymous")
            rating = review.get("rating")
            text = review.get("text", "")
            relative_time = review.get("relativePublishTimeDescription")
            
            # Truncate long reviews
            if text and len(text) > max_text_length:
                text = text[:max_text_length] + "..."
            
            reviews.append(ReviewSummary(
                author=author,
                rating=rating,
                text=text,
                relative_time=relative_time
            ))
        
        return reviews
    except Exception as e:
        logger.warning(f"Failed to extract reviews: {e}")
        return []


def extract_coordinates(raw_data: Dict[str, Any]) -> Optional[Coordinates]:
    """
    Extract coordinates from raw Google data.
    
    Args:
        raw_data: Raw Google Places data
        
    Returns:
        Coordinates object or None
    """
    try:
        location = raw_data.get("location", {})
        lat = location.get("lat")
        lng = location.get("lng")
        
        if lat is not None and lng is not None:
            return Coordinates(lat=lat, lng=lng)
        
        return None
    except Exception as e:
        logger.warning(f"Failed to extract coordinates: {e}")
        return None


def parse_google_maps_data(raw_data: Dict[str, Any]) -> GoogleMapsOutput:
    """
    Parse raw Google Maps data into clean GoogleMapsOutput.
    
    This is the main transformation function that handles all the heavy lifting.
    
    Args:
        raw_data: Raw data from DB (the 'value' field from storage)
        
    Returns:
        GoogleMapsOutput with all fields properly extracted and transformed
    """
    # Extract basic identity
    place_id = raw_data.get("id")
    display_name = raw_data.get("displayName", "Unknown")
    
    # Extract classification
    primary_type = raw_data.get("primaryType")
    primary_type_display = raw_data.get("primaryTypeDisplayName")
    types = raw_data.get("types", [])
    
    # Derive sector
    derived_sector = derive_sector_from_google(primary_type, types)
    
    # Extract contact info
    phone = raw_data.get("nationalPhoneNumber")
    international_phone = raw_data.get("internationalPhoneNumber")
    website = raw_data.get("websiteURI")
    google_maps_url = raw_data.get("googleMapsURI")
    
    # Extract location
    formatted_address = raw_data.get("formattedAddress")
    coordinates = extract_coordinates(raw_data)
    
    # Extract ratings
    rating = raw_data.get("rating")
    review_count = raw_data.get("userRatingCount")
    price_level = raw_data.get("priceLevel")
    
    # Extract content
    editorial_summary = raw_data.get("editorialSummary")
    hours = extract_hours(raw_data)
    recent_reviews = extract_reviews(raw_data)
    
    # Extract status
    business_status = raw_data.get("businessStatus")
    is_operational = business_status == "OPERATIONAL" if business_status else True
    
    return GoogleMapsOutput(
        place_id=place_id,
        display_name=display_name,
        formatted_address=formatted_address,
        coordinates=coordinates,
        primary_type=primary_type,
        primary_type_display=primary_type_display,
        types=types,
        derived_sector=derived_sector,
        phone=phone,
        international_phone=international_phone,
        website=website,
        google_maps_url=google_maps_url,
        rating=rating,
        review_count=review_count,
        price_level=price_level,
        editorial_summary=editorial_summary,
        hours=hours,
        recent_reviews=recent_reviews,
        business_status=business_status,
        is_operational=is_operational,
    )