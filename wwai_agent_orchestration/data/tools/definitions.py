"""
Tool definitions for LLM function calling.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_business_profile",
            "description": "Get business profile including contact info, location, hours, services, and ratings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "Business UUID"}
                },
                "required": ["business_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_reviews",
            "description": "Get normalized reviews for a business from Google Maps and Yelp.",
            "parameters": {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "Business UUID"},
                    "min_length": {"type": "integer"},
                    "min_rating": {"type": "number"},
                    "max_results": {"type": "integer"},
                },
                "required": ["business_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_media_assets",
            "description": "Get stock/generated media assets for a business by assigned trades.",
            "parameters": {
                "type": "object",
                "properties": {
                    "business_id": {"type": "string", "description": "Business UUID"},
                    "media_type": {
                        "type": "string",
                        "enum": ["image", "video", "all"],
                        "description": "Type of media to retrieve.",
                    },
                    "max_results": {"type": "integer"},
                },
                "required": ["business_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scrape_website",
            "description": "Scrape a URL and extract structured page content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to scrape"},
                    "device": {
                        "type": "string",
                        "enum": ["desktop", "mobile"],
                        "description": "Device profile for scraping",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_page_intent",
            "description": "Analyze a webpage URL using Gemini to extract intent and business summary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to analyze"},
                },
                "required": ["url"],
            },
        },
    },
]


def get_tools() -> list:
    return TOOLS


def get_tool_names() -> list[str]:
    return [t["function"]["name"] for t in TOOLS]


def get_tool_by_name(name: str) -> dict | None:
    for tool in TOOLS:
        if tool["function"]["name"] == name:
            return tool
    return None
