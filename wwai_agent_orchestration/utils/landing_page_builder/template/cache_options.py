"""
Template options from template_cache (filtered by business trades).
"""

from typing import List, Optional

from wwai_agent_orchestration.contracts.landing_page_builder.curated_options import (
    TemplateOption,
)
from wwai_agent_orchestration.core.database import db_manager
from wwai_agent_orchestration.data.providers.trade_classification_provider import (
    TradeClassificationProvider,
)


def get_template_options_from_cache(
    business_id: str,
    current_section_ids: Optional[List[str]] = None,
    db_name: str = "template_generation",
    max_docs: int = 50,
) -> List[TemplateOption]:
    """
    Get template options from template_cache filtered by business trades.

    Uses TradeClassificationProvider.get_assigned_trade_names(business_id).
    Query: cache_key_input.trades overlaps with business trades.
    Flattens cache_key_output.resolved_template_recommendations into TemplateOption list.
    """
    if not business_id:
        raise ValueError("business_id is required")

    trades = TradeClassificationProvider().get_assigned_trade_names(str(business_id))
    if not trades:
        raise ValueError(
            "No trade classification found for this business. Setup business profile first."
        )

    db = db_manager.get_database(db_name)
    collection = db["template_cache"]
    cursor = collection.find(
        {"cache_key_input.trades": {"$in": trades}}
    )
    cached_docs = list(cursor)[:max_docs]

    if not cached_docs:
        raise ValueError(
            "No cached templates found for your trades. Run a full generation first."
        )

    options: List[TemplateOption] = []
    for doc in cached_docs:
        recs = doc.get("cache_key_output") or {}
        recs = recs.get("resolved_template_recommendations") or []
        intent = (
            doc.get("website_intention")
            or (doc.get("cache_key_input") or {}).get("website_intention")
            or "Unknown"
        )
        for idx, rec in enumerate(recs):
            mappings = rec.get("section_mappings") or []
            rec_section_ids = [
                m.get("section_id") for m in mappings if m.get("section_id")
            ]
            section_desktop_urls = [
                m.get("desktop_screenshot")
                for m in mappings
                if m.get("desktop_screenshot")
            ]
            is_current = bool(
                current_section_ids and rec_section_ids == current_section_ids
            )
            options.append(
                TemplateOption(
                    template_id=rec.get("template_id") or "",
                    template_name=rec.get("template_name")
                    or f"{intent.capitalize()} Layout {idx + 1}",
                    section_count=len(rec_section_ids),
                    index=len(options),
                    is_current=is_current,
                    section_ids=rec_section_ids,
                    section_desktop_urls=section_desktop_urls or None,
                    intent=intent,
                )
            )
    return options
