"""
Curated pages: fetch and save to curated_pages collection in section_repo_prod.

Supports simplified schema (page_path, page_title, page_description, section_ids)
with section repo lookup for desktop screenshot URLs.
"""

from typing import List, Optional

from bson import ObjectId
from template_json_builder.db.queries import SECTION_REPO_PROD_DB

from wwai_agent_orchestration.contracts.landing_page_builder.curated_options import (
    CuratedPageOption,
)
from wwai_agent_orchestration.core.database import DocumentNotFoundError, db_manager
from wwai_agent_orchestration.data.providers.section_catalog_provider import (
    SectionCatalogProvider,
)


def _get_section_desktop_urls_for_ids(section_ids: List[str]) -> List[str]:
    """Fetch desktop_image_url for each section_id from section repo. Preserves order."""
    if not section_ids:
        return []
    try:
        provider = SectionCatalogProvider()
        docs = provider.fetch_sections_with_metadata(
            query_filter={"_id": {"$in": [ObjectId(sid) for sid in section_ids]}}
        )
    except DocumentNotFoundError:
        return []
    id_to_url = {str(d.get("_id", "")): d.get("desktop_image_url") for d in docs}
    return [
        id_to_url.get(sid) or ""
        for sid in section_ids
    ]


def _section_ids_from_doc(doc: dict) -> List[str]:
    """Extract section_ids from doc (new schema or legacy section_mappings)."""
    assert "section_ids" in doc, "section_ids not found in doc"
    return [str(sid) for sid in doc["section_ids"]]


def get_curated_pages(
    db_name: str = SECTION_REPO_PROD_DB,
    collection_name: str = "curated_pages",
) -> List[CuratedPageOption]:
    """
    Fetch all curated pages from DB.

    Supports simplified schema (page_path, page_title, page_description, section_ids)
    and legacy schema (section_mappings). Desktop screenshot URLs are looked up
    from the section repo.
    """
    db = db_manager.get_database(db_name)
    collection = db[collection_name]
    docs = list(collection.find({}))

    pages: List[CuratedPageOption] = []
    for doc in docs:
        section_ids = _section_ids_from_doc(doc)
        section_desktop_urls = _get_section_desktop_urls_for_ids(section_ids)
        page_title = doc.get("page_title") or doc.get("page_path") or "Untitled Page"
        page_path = doc.get("page_path") or ""
        page_description = doc.get("page_description") or None
        pages.append(
            CuratedPageOption(
                page_path=page_path,
                page_title=page_title,
                page_description=page_description,
                section_ids=section_ids,
                section_desktop_urls=section_desktop_urls,
            )
        )
    return pages


def get_curated_page_by_path(
    page_path: str,
    db_name: str = SECTION_REPO_PROD_DB,
    collection_name: str = "curated_pages",
) -> Optional[CuratedPageOption]:
    """
    Fetch a single curated page by page_path from DB.

    Handles path variations: tries exact match, then without leading slash,
    then with leading slash. Returns None if not found.
    """
    page_path = (page_path or "").strip()
    if not page_path:
        return None

    db = db_manager.get_database(db_name)
    collection = db[collection_name]

    # Try exact match first, then normalized variations
    paths_to_try = [
        page_path,
        page_path.lstrip("/"),
        f"/{page_path.lstrip('/')}" if page_path != "/" else page_path,
    ]
    doc = None
    for path in paths_to_try:
        doc = collection.find_one({"page_path": path})
        if doc:
            break

    if not doc:
        return None

    section_ids = _section_ids_from_doc(doc)
    section_desktop_urls = _get_section_desktop_urls_for_ids(section_ids)
    page_title = doc.get("page_title") or doc.get("page_path") or "Untitled Page"
    doc_page_path = doc.get("page_path") or ""
    page_description = doc.get("page_description") or None

    return CuratedPageOption(
        page_path=doc_page_path,
        page_title=page_title,
        page_description=page_description,
        section_ids=section_ids,
        section_desktop_urls=section_desktop_urls,
    )


def save_curated_page(
    page_path: str,
    page_title: str,
    section_ids: List[str],
    page_description: Optional[str] = None,
    db_name: str = SECTION_REPO_PROD_DB,
    collection_name: str = "curated_pages",
) -> None:
    """
    Upsert a curated page by page_path.
    Creates or updates the document with page_path, page_title, page_description, section_ids.
    """
    page_path = (page_path or "").strip()
    page_title = (page_title or "").strip() or page_path or "Untitled Page"
    if not page_path:
        raise ValueError("page_path is required")
    db = db_manager.get_database(db_name)
    collection = db[collection_name]
    doc = {
        "page_path": page_path,
        "page_title": page_title,
        "page_description": (page_description or "").strip() or None,
        "section_ids": [str(sid) for sid in section_ids],
    }
    collection.update_one(
        {"page_path": page_path},
        {"$set": doc},
        upsert=True,
    )
