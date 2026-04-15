"""
Sections for replacement: fetch categories and sections from section repository (SMB filter).
"""

import logging
from typing import List, Literal, Optional

from wwai_agent_orchestration.contracts.landing_page_builder.section_options import (
    CategoryResponse,
    SectionMetadataResponse,
)
from wwai_agent_orchestration.core.database import DocumentNotFoundError
from wwai_agent_orchestration.data.providers.section_catalog_provider import SectionCatalogProvider
from wwai_agent_orchestration.utils.landing_page_builder.template.section_utils import (
    section_category,
)

logger = logging.getLogger(__name__)

SMB_QUERY_FILTER = {"status": "ACTIVE", "tag": "smb"}


def get_categories_for_replacement() -> List[CategoryResponse]:
    """
    Get L0 categories from the section repository (SMB filter).
    Filters out header and footer L0 categories; only body categories are returned.
    Returns empty list on DocumentNotFoundError.
    """
    try:
        provider = SectionCatalogProvider()
        categories = provider.get_unique_l0_categories(query_filter=SMB_QUERY_FILTER)
        result = []
        for doc in categories:
            l0_name = doc.get("name") or doc.get("original_l0", "")
            if section_category(l0_name) != "body":
                continue
            result.append(
                CategoryResponse(
                    key=doc.get("l0_key", ""),
                    name=l0_name,
                    description="",
                )
            )
        return result
    except DocumentNotFoundError:
        logger.warning("No L0 categories found in section repository")
        return []


def _section_to_metadata(section: dict) -> SectionMetadataResponse:
    """Map a raw section dict to SectionMetadataResponse."""
    section_id = str(section.get("section_id") or section.get("_id", ""))
    section_l0 = section.get("section_l0", "")
    section_l1 = section.get("section_l1", "")
    if section_l1:
        display_name = f"{section_l0} - {section_l1}"
    else:
        display_name = section_l0 or section_id
    category_key = (
        section_l0.lower().replace(" ", "_") if section_l0 else ""
    )
    preview_image_url = section.get("desktop_image_url")
    return SectionMetadataResponse(
        section_id=section_id,
        display_name=display_name,
        category_key=category_key,
        preview_image_url=preview_image_url,
        description=None,
    )


def get_sections_for_replacement(
    category_key: Optional[str] = None,
    section_type: Optional[Literal["header", "body", "footer"]] = None,
) -> List[SectionMetadataResponse]:
    """
    Get sections usable for replacement, optionally filtered by category and/or section type.
    Uses SMB filter. Returns empty list on DocumentNotFoundError.
    """
    try:
        provider = SectionCatalogProvider()
        if category_key:
            categories = provider.get_unique_l0_categories(query_filter=SMB_QUERY_FILTER)
            matching_l0 = None
            for cat in categories:
                if cat.get("l0_key") == category_key:
                    matching_l0 = cat.get("original_l0")
                    break
            if matching_l0 is None:
                matching_l0 = category_key.replace("_", " ").title()
                logger.warning(
                    "Category key '%s' not found in categories, using fallback: '%s'",
                    category_key,
                    matching_l0,
                )
            sections = provider.get_sections_by_l0(
                l0_category=matching_l0,
                query_filter=SMB_QUERY_FILTER,
            )
        else:
            sections = provider.fetch_sections_with_metadata(
                query_filter=SMB_QUERY_FILTER,
            )

        if section_type is not None:
            sections = [
                s for s in sections
                if section_category(s.get("section_l0", "")) == section_type
            ]
        return [_section_to_metadata(s) for s in sections]
    except DocumentNotFoundError:
        logger.warning(
            "No sections found in section repository (category_key=%s, section_type=%s)",
            category_key,
            section_type,
        )
        return []
