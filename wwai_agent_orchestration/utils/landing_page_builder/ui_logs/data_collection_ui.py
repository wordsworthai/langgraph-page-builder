"""
UI HTML builders for data collection nodes (business data, campaign intent).
"""

from typing import Any, List, Optional

from wwai_agent_orchestration.utils.landing_page_builder.ui_logs._common import wrap_content


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Get attribute or dict key from object."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _rating_stars(rating: float) -> str:
    """Build star display for rating with half-star support (e.g. 4.8 → ★★★★½)."""
    if rating is None:
        return ""
    full = int(rating)
    remainder = rating - full
    half = 0.5 <= remainder < 1.0
    empty = 5 - full - (1 if half else 0)
    stars = "★" * full + ("½" if half else "") + "☆" * empty
    return stars


def business_data_html(
    google_data: Optional[Any] = None,
    yelp_data: Optional[Any] = None,
    derived_sector: Optional[str] = None,
) -> str:
    """
    Build HTML for business data extraction (Google Maps, Yelp, industry).
    Accepts Pydantic models or dicts (duck typing).
    Returns fallback message when no cards.
    """
    html_parts = []

    html_parts.append(
        '<p style="font-size: 13px; color: #6b7280; margin: 0 0 14px 0; line-height: 1.5;">'
        "We gathered information about your business from:</p>"
    )

    if google_data:
        google_info = []
        # Single source label (no redundant icons)
        google_info.append(
            '<div style="color: #6b7280; font-size: 12px; margin-bottom: 10px;">From Google Maps</div>'
        )
        display_name = _get(google_data, "display_name")
        if display_name:
            google_info.append(
                f'<div style="font-weight: 600; color: #1f2937; font-size: 14px; margin-bottom: 8px;">{display_name}</div>'
            )
        # Rating inline with reviews
        rating = _get(google_data, "rating")
        if rating is not None:
            stars = _rating_stars(rating)
            review_count = _get(google_data, "review_count")
            review_str = f"({review_count:,} reviews)" if review_count is not None else ""
            google_info.append(
                f'<div style="color: #6b7280; font-size: 13px; margin-bottom: 8px;">'
                f'<span style="color: #f59e0b;">{stars}</span> {rating:.1f} {review_str}</div>'
            )
        # Address (no icon - cleaner)
        formatted_address = _get(google_data, "formatted_address")
        if formatted_address:
            google_info.append(
                f'<div style="color: #6b7280; font-size: 13px; margin-bottom: 6px;">{formatted_address}</div>'
            )
        # Optional: phone, website, type
        phone = _get(google_data, "phone")
        if phone:
            google_info.append(
                f'<div style="color: #6b7280; font-size: 13px; margin-bottom: 4px;">{phone}</div>'
            )
        website = _get(google_data, "website")
        if website:
            google_info.append(
                f'<a href="{website}" target="_blank" rel="noopener" '
                f'style="color: #3b82f6; font-size: 13px; text-decoration: none;">View website</a>'
            )
        primary_type = _get(google_data, "primary_type_display") or _get(google_data, "primary_type")
        if primary_type:
            google_info.append(
                f'<div style="margin-top: 8px;">'
                f'<span style="background: #f3f4f6; color: #4b5563; padding: 2px 8px; '
                f'border-radius: 4px; font-size: 12px;">{primary_type}</span></div>'
            )
        price_level = _get(google_data, "price_level")
        if price_level is not None:
            count = int(price_level) if isinstance(price_level, (int, float)) else len(str(price_level))
            price_symbols = "$" * max(0, count)
            if price_symbols:
                google_info.append(
                    f'<div style="color: #6b7280; font-size: 13px; margin-top: 4px;">{price_symbols}</div>'
                )
        html_parts.append(
            '<div style="background: #f9fafb; border: 1px solid #e5e7eb; padding: 14px 16px; '
            'border-radius: 6px; margin-bottom: 14px;">'
            f'{"".join(google_info)}</div>'
        )

    if yelp_data:
        yelp_info = []
        yelp_info.append(
            '<div style="display: flex; align-items: center; gap: 6px; margin-bottom: 12px;">'
            '<span style="font-size: 18px;">🍽️</span>'
            '<span style="font-weight: 600; color: #1f2937; font-size: 14px;">Yelp</span>'
            "</div>"
        )
        yelp_info.append('<div style="padding-left: 12px;">')
        business_name = _get(yelp_data, "business_name")
        if business_name:
            yelp_info.append(
                f'<div style="font-weight: 600; color: #111827; font-size: 15px; margin-bottom: 6px;">{business_name}</div>'
            )
        rating = _get(yelp_data, "rating")
        if rating is not None:
            stars = _rating_stars(rating)
            review_text = f'<span style="color: #f59e0b; letter-spacing: 1px;">{stars}</span>'
            review_count = _get(yelp_data, "review_count")
            if review_count is not None:
                review_text += f' <span style="color: #6b7280; font-size: 13px;">{rating:.1f} ({review_count:,} reviews)</span>'
            else:
                review_text += f' <span style="color: #6b7280; font-size: 13px;">{rating:.1f}</span>'
            yelp_info.append(f'<div style="margin-bottom: 8px;">{review_text}</div>')
        categories = _get(yelp_data, "categories") or []
        if categories:
            categories_text = ", ".join(categories[:3])
            if len(categories) > 3:
                categories_text += f" +{len(categories) - 3} more"
            yelp_info.append(
                '<div style="display: flex; align-items: center; gap: 6px; margin-bottom: 6px;">'
                '<span style="font-size: 14px;">🏷️</span>'
                f'<span style="color: #6b7280; font-size: 13px;">{categories_text}</span>'
                "</div>"
            )
        address = _get(yelp_data, "address")
        if address:
            yelp_info.append(
                '<div style="display: flex; align-items: flex-start; gap: 6px; margin-bottom: 6px;">'
                '<span style="font-size: 14px; flex-shrink: 0;">📍</span>'
                f'<address style="margin: 0; color: #6b7280; font-size: 13px; line-height: 1.5; font-style: normal;">{address}</address>'
                "</div>"
            )
        phone = _get(yelp_data, "phone")
        if phone:
            yelp_info.append(
                '<div style="display: flex; align-items: center; gap: 6px; margin-bottom: 6px;">'
                '<span style="font-size: 14px;">📞</span>'
                f'<span style="color: #6b7280; font-size: 13px;">{phone}</span>'
                "</div>"
            )
        yelp_info.append("</div>")
        html_parts.append(
            '<div style="background: #ffffff; border: 1px solid #e5e7eb; '
            'padding: 16px 18px; border-radius: 8px; margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.06);">'
            f'{"".join(yelp_info)}</div>'
        )

    if derived_sector:
        html_parts.append(
            f'<div style="margin-top: 12px;">'
            f'<span style="display: inline-block; background: #eff6ff; color: #1e40af; '
            f'padding: 6px 12px; border-radius: 12px; font-size: 12px; font-weight: 500;">'
            f'🏢 Industry: {derived_sector}</span></div>'
        )

    if len(html_parts) <= 1:
        return wrap_content('<p style="color: #6b7280; font-size: 13px;">Business data collected</p>')
    return wrap_content("".join(html_parts))


def campaign_intent_html(
    full_query: str,
    intro_text: str = "Based on the information gathered, I think we would be creating a page where",
) -> str:
    """Build HTML for campaign intent (intro + full query in styled box)."""
    inner = (
        f'<div style="margin-bottom: 10px;">'
        f'<p style="color: #6b7280; margin: 0 0 8px 0; font-size: 13px;">{intro_text}:</p>'
        "</div>"
        '<div style="background: #f9fafb; padding: 12px 14px; border-radius: 4px;">'
        f'<p style="color: #1f2937; margin: 0; font-size: 13px; line-height: 1.6; white-space: pre-wrap;">'
        f'{full_query}</p>'
        "</div>"
    )
    return wrap_content(inner, line_height="1.6")


def trade_picked_html(trades: List[str]) -> str:
    """Build HTML for trade classification milestone."""
    if trades:
        trades_text = ", ".join(trades)
        inner = (
            '<div style="background: #f9fafb; padding: 10px 12px; border-radius: 4px;">'
            f'<p style="color: #1f2937; margin: 0; font-size: 13px;">Your business type: {trades_text}</p>'
            "</div>"
        )
    else:
        inner = (
            '<div style="background: #f9fafb; padding: 10px 12px; border-radius: 4px;">'
            '<p style="color: #1f2937; margin: 0; font-size: 13px;">Business type classified.</p>'
            "</div>"
        )
    return wrap_content(inner)
