"""
Google Maps embed utility.

Builds map embed iframe HTML from business profile data, using the same format
as the frontend MapPickerField (maps.google.com/maps?q=...&output=embed).
No API key required.
"""

import urllib.parse
from typing import Optional, Any

from template_json_builder.ipsum_lorem_agents.default_content_provider import (
    html_content_generator,
)


def build_map_embed_html(
    formatted_address: Optional[str] = None,
    business_name: Optional[str] = None,
    address: Optional[Any] = None,
) -> str:
    """
    Build Google Maps embed iframe HTML from business profile data.

    Uses the same format as frontend MapPickerField's placeToIframeHtml:
    https://maps.google.com/maps?q={query}&t=m&z=15&output=embed&iwloc=near
    No API key required.

    Args:
        formatted_address: Pre-formatted full address string (preferred).
        business_name: Business name for title and fallback query.
        address: Address model with street, city, state, zip (or dict).

    Returns:
        iframe HTML string. Falls back to DEFAULT_MAP_EMBED if no query can be built.
    """
    query = _build_query(formatted_address, business_name, address)
    if not query:
        return html_content_generator.DEFAULT_MAP_EMBED

    encoded_query = urllib.parse.quote(query)
    embed_url = (
        f"https://maps.google.com/maps?q={encoded_query}&t=m&z=15&output=embed&iwloc=near"
    )
    title = business_name or "Map"
    return (
        f'<iframe src="{embed_url}" width="100%" height="650px" style="border:0;" '
        f'allowfullscreen="" loading="lazy" referrerpolicy="no-referrer-when-downgrade" '
        f'title="{_escape_attr(title)}"></iframe>'
    )


def _build_query(
    formatted_address: Optional[str],
    business_name: Optional[str],
    address: Optional[Any],
) -> Optional[str]:
    """Build search query from address data. Prefer formatted_address, then address parts."""
    if formatted_address and formatted_address.strip():
        return formatted_address.strip()

    if address:
        parts = []
        if business_name and business_name.strip():
            parts.append(business_name.strip())
        if hasattr(address, "street") and address.street:
            parts.append(str(address.street))
        elif isinstance(address, dict) and address.get("street"):
            parts.append(str(address["street"]))

        if hasattr(address, "city") and address.city:
            parts.append(str(address.city))
        elif isinstance(address, dict) and address.get("city"):
            parts.append(str(address["city"]))

        if hasattr(address, "state") and address.state:
            parts.append(str(address.state))
        elif isinstance(address, dict) and address.get("state"):
            parts.append(str(address["state"]))

        if hasattr(address, "zip") and address.zip:
            parts.append(str(address.zip))
        elif isinstance(address, dict) and address.get("zip"):
            parts.append(str(address["zip"]))

        if parts:
            return ", ".join(parts)

    if business_name and business_name.strip():
        return business_name.strip()

    return None


def _escape_attr(value: str) -> str:
    """Escape HTML attribute value (quotes)."""
    return value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
