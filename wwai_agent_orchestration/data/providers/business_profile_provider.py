# data_providers/providers/business_profile_provider.py
"""
Business Profile Provider.

Transforms raw Google Maps + Yelp data into unified BusinessProfile.
"""

from wwai_agent_orchestration.core.observability.logger import get_logger
from typing import Optional, Dict, Any, List
from datetime import datetime

from wwai_agent_orchestration.data.connectors.base_mongo_provider import BaseProvider
from wwai_agent_orchestration.data.providers.models.business_profile import (
    BusinessProfileInput,
    BusinessProfileOutput,
    Address,
    Coordinates,
    DayHours,
)

logger = get_logger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

DB_BUSINESSES = "businesses"
COLLECTION_SCRAPED = "business_scraped_data"

# Google type to industry mapping
GOOGLE_TYPE_TO_INDUSTRY = {
    "restaurant": "food-beverage",
    "cafe": "food-beverage",
    "bar": "food-beverage",
    "bakery": "food-beverage",
    "meal_takeaway": "food-beverage",
    "clothing_store": "retail",
    "electronics_store": "retail",
    "furniture_store": "retail",
    "hair_salon": "beauty-wellness",
    "beauty_salon": "beauty-wellness",
    "spa": "beauty-wellness",
    "gym": "beauty-wellness",
    "lawyer": "professional-services",
    "accounting": "professional-services",
    "real_estate_agency": "professional-services",
    "dentist": "healthcare",
    "doctor": "healthcare",
    "hospital": "healthcare",
    "plumber": "home-services",
    "electrician": "home-services",
    "locksmith": "home-services",
    "car_repair": "automotive",
    "car_dealer": "automotive",
}


# =============================================================================
# PROVIDER
# =============================================================================

class BusinessProfileProvider(BaseProvider):
    """
    Provider for business profile data.
    
    Reads from raw Google Maps + Yelp data and transforms to unified profile.
    """
    
    def get(self, input_data: BusinessProfileInput) -> BusinessProfileOutput:
        """
        Get business profile by ID.
        
        Args:
            input_data: BusinessProfileInput with business_id
            
        Returns:
            BusinessProfileOutput with transformed data
        """
        business_id = input_data.business_id
        logger.info(f"Getting business profile for: {business_id}")
        
        # Query raw data
        raw_data = self.find_one(
            DB_BUSINESSES,
            COLLECTION_SCRAPED,
            {"business_id": business_id}
        )

        # print(raw_data)
        # print(business_id)
        
        if not raw_data:
            logger.warning(f"No data found for business_id: {business_id}")
            return BusinessProfileOutput(
                business_id=business_id,
                business_name="Unknown",
                data_sources=[],
            )
        
        # Transform
        return self._transform(business_id, raw_data)

    def get_by_business_id(self, business_id: str) -> BusinessProfileOutput:
        """
        Convenience wrapper to fetch profile without constructing input model.

        Args:
            business_id: Business UUID

        Returns:
            BusinessProfileOutput
        """
        return self.get(BusinessProfileInput(business_id=business_id))
    
    def _transform(
        self, 
        business_id: str, 
        raw_data: Dict[str, Any]
    ) -> BusinessProfileOutput:
        """Transform raw data to BusinessProfileOutput."""
        
        google_data = raw_data.get("google_maps_data", {})
        yelp_data = raw_data.get("yelp_data", {})
        
        data_sources = []
        if google_data:
            data_sources.append("google_maps")
        if yelp_data:
            data_sources.append("yelp")
        
        google_data = google_data.get("value", {})
        yelp_data = yelp_data.get("value", {})
        
        # === Identity ===
        business_name = (
            google_data.get("displayName") or 
            yelp_data.get("business_name") or 
            "Unknown"
        )
        
        display_name = google_data.get("displayName") or yelp_data.get("business_name")
        
        description = None
        if yelp_data:
            parts = []
            if yelp_data.get("specialties"):
                parts.append(yelp_data["specialties"])
            if yelp_data.get("history"):
                parts.append(yelp_data["history"])
            if parts:
                description = " ".join(parts)
        
        # === Classification ===
        primary_category = google_data.get("primaryType")
        
        categories = []
        if google_data.get("types"):
            categories.extend(google_data["types"])
        if yelp_data.get("categories"):
            yelp_cats = yelp_data["categories"]
            if isinstance(yelp_cats, str):
                yelp_cats = [c.strip() for c in yelp_cats.split(",")]
            for cat in yelp_cats:
                if cat not in categories:
                    categories.append(cat)
        
        industry = self._derive_industry(primary_category, categories)
        
        # === Contact ===
        phone = (
            google_data.get("nationalPhoneNumber") or
            google_data.get("internationalPhoneNumber") or
            yelp_data.get("localized_phone") or
            yelp_data.get("phone")
        )
        
        website_url = (
            google_data.get("websiteURI") or
            yelp_data.get("business_website")
        )
        
        # === Location ===
        address = self._build_address(google_data, yelp_data)
        formatted_address = (
            google_data.get("formattedAddress") or
            yelp_data.get("full_address")
        )
        
        coordinates = None
        if google_data.get("location"):
            loc = google_data["location"]
            if loc.get("lat") and loc.get("lng"):
                coordinates = Coordinates(lat=loc["lat"], lng=loc["lng"])
        
        google_maps_url = google_data.get("googleMapsURI")
        yelp_url = yelp_data.get("yelp_url") or yelp_data.get("share_url")
        
        # === Hours ===
        hours = self._build_hours(google_data, yelp_data)
        
        # === Services ===
        services = []
        if yelp_data.get("services_offered"):
            svc = yelp_data["services_offered"]
            if isinstance(svc, str):
                services = [s.strip() for s in svc.split(",")]
            elif isinstance(svc, list):
                services = svc
        
        specialties = yelp_data.get("specialties")
        
        price_level = (
            google_data.get("priceLevel") or
            yelp_data.get("price")
        )
        
        # === Status ===
        is_operational = True
        if google_data.get("businessStatus"):
            is_operational = google_data["businessStatus"] == "OPERATIONAL"
        if yelp_data.get("is_closed"):
            is_operational = False
        
        year_established = None
        if yelp_data.get("year_established"):
            try:
                year_established = int(yelp_data["year_established"])
            except (ValueError, TypeError):
                pass
        
        # === Ratings ===
        google_rating = google_data.get("rating")
        google_review_count = google_data.get("userRatingCount")
        
        yelp_rating = None
        if yelp_data.get("rating"):
            try:
                yelp_rating = float(yelp_data["rating"])
            except (ValueError, TypeError):
                pass
        yelp_review_count = yelp_data.get("review_count")
        
        return BusinessProfileOutput(
            business_id=business_id,
            business_name=business_name,
            display_name=display_name,
            description=description,
            industry=industry,
            primary_category=primary_category,
            categories=categories,
            phone=phone,
            website_url=website_url,
            address=address,
            formatted_address=formatted_address,
            coordinates=coordinates,
            google_maps_url=google_maps_url,
            yelp_url=yelp_url,
            hours=hours,
            services=services,
            specialties=specialties,
            price_level=price_level,
            is_operational=is_operational,
            year_established=year_established,
            google_rating=google_rating,
            google_review_count=google_review_count,
            yelp_rating=yelp_rating,
            yelp_review_count=yelp_review_count,
            data_sources=data_sources,
            last_updated=datetime.utcnow(),
        )
    
    def _derive_industry(
        self, 
        primary_category: Optional[str], 
        categories: List[str]
    ) -> Optional[str]:
        """Derive industry from categories."""
        if primary_category and primary_category in GOOGLE_TYPE_TO_INDUSTRY:
            return GOOGLE_TYPE_TO_INDUSTRY[primary_category]
        
        for cat in categories:
            cat_lower = cat.lower().replace(" ", "_")
            if cat_lower in GOOGLE_TYPE_TO_INDUSTRY:
                return GOOGLE_TYPE_TO_INDUSTRY[cat_lower]
        
        return None
    
    def _build_address(
        self, 
        google_data: Dict, 
        yelp_data: Dict
    ) -> Optional[Address]:
        """Build Address from raw data."""
        if yelp_data:
            if any([
                yelp_data.get("address1"),
                yelp_data.get("city"),
                yelp_data.get("state"),
                yelp_data.get("zip")
            ]):
                return Address(
                    street=yelp_data.get("address1"),
                    city=yelp_data.get("city"),
                    state=yelp_data.get("state"),
                    zip=yelp_data.get("zip"),
                )
        
        # Try parsing from Google's formatted address
        if google_data.get("addressComponents"):
            addr = Address()
            for component in google_data["addressComponents"]:
                types = component.get("types", [])
                text = component.get("longText") or component.get("shortText")
                
                if "street_number" in types or "route" in types:
                    if addr.street:
                        addr.street = f"{addr.street} {text}"
                    else:
                        addr.street = text
                elif "locality" in types:
                    addr.city = text
                elif "administrative_area_level_1" in types:
                    addr.state = component.get("shortText")
                elif "postal_code" in types:
                    addr.zip = text
            
            return addr
        
        return None
    
    def _build_hours(
        self, 
        google_data: Dict, 
        yelp_data: Dict
    ) -> Optional[List[DayHours]]:
        """Build hours list from raw data."""
        
        # Try Google first
        if google_data.get("regularOpeningHours"):
            weekday_desc = google_data["regularOpeningHours"]
            if weekday_desc:
                hours = []
                for desc in weekday_desc:
                    # Format: "Monday: 9:00 AM – 5:00 PM"
                    if ":" in desc:
                        parts = desc.split(":", 1)
                        day = parts[0].strip().lower()
                        time_str = parts[1].strip() if len(parts) > 1 else "Closed"
                        hours.append(DayHours(day=day, hours=time_str))
                return hours if hours else None
        
        # Try Yelp
        if yelp_data.get("localized_hours"):
            loc_hours = yelp_data["localized_hours"]
            if isinstance(loc_hours, list):
                hours = []
                for entry in loc_hours:
                    if ":" in entry:
                        parts = entry.split(":", 1)
                        day = parts[0].strip().lower()
                        time_str = parts[1].strip()
                        hours.append(DayHours(day=day, hours=time_str))
                return hours if hours else None
        
        return None