"""
Section DB utilities. Fetches section documents from section_repo_prod (sections + metadata)
and builds section mapping dicts for use in add_section_in_place, etc.
"""

from typing import Any, Dict, Tuple

from bson import ObjectId

from wwai_agent_orchestration.core.database import DocumentNotFoundError
from wwai_agent_orchestration.data.providers.section_catalog_provider import SectionCatalogProvider


def get_section_doc_and_mapping(section_id: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Fetch section from section_repo_prod (with metadata) and build section mapping dict.

    Returns:
        (section_doc, new_section_mapping) where:
        - section_doc: merged MongoDB document (sections + section_metadata)
        - new_section_mapping: dict with section_id, section_l0, section_l1,
          desktop_screenshot, mobile_screenshot (for use in apply_section_modification)

    Raises:
        ValueError: If section not found in repo.
    """
    section_catalog = SectionCatalogProvider()
    try:
        docs = section_catalog.fetch_sections_with_metadata(
            query_filter={"_id": ObjectId(section_id)}
        )
    except DocumentNotFoundError:
        raise ValueError(f"Section not found in repo: {section_id}")
    section_doc = docs[0]

    new_section_mapping = {
        "section_id": section_id,
        "section_l0": section_doc.get("section_l0"),
        "section_l1": section_doc.get("section_l1"),
        "desktop_screenshot": section_doc.get("desktop_image_url"),
        "mobile_screenshot": section_doc.get("mobile_image_url"),
    }
    return section_doc, new_section_mapping
