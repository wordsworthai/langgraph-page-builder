# data_connections/section_repository.py
"""
Section Repository data access service.

Encapsulates MongoDB access for section repository documents, keeping
LangGraph nodes free from persistence concerns.

Delegates to template_json_builder's section_repository_queries for
aggregation logic (sections + metadata join).
"""

from typing import Dict, Any, List, Optional

from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.core.database import (
    db_manager as global_db_manager,
    fetch_from_collection,
    DocumentNotFoundError,
)
from template_json_builder.db.queries import SECTION_REPO_PROD_DB
from template_json_builder.db.section_repository import (
    fetch_sections_with_metadata_sync,
    get_unique_l0_categories_sync,
    get_sections_by_l0_sync,
    get_distinct_tags_sync,
    get_distinct_statuses_sync,
    get_distinct_semantic_tags_sync,
    update_section_status_sync,
    get_developer_section_by_id_sync,
    update_section_semantic_tags_sync,
)
from wwai_agent_orchestration.utils.checkpoint.checkpoint_utils import make_json_serializable


class SectionRepositoryService:
    """
    Service for fetching section repository documents from MongoDB.

    Delegates to template_json_builder for aggregation logic.
    Uses database and collection names from template_json_builder (SECTION_REPO_PROD_DB, sections, section_metadata).
    """

    DEFAULT_QUERY_FILTER: Dict[str, Any] = {"status": "ACTIVE"}

    def __init__(self, db_manager=None):
        self._logger = get_logger(__name__)
        self._db_manager = db_manager or global_db_manager

    def _get_db(self):
        """Get sync database from db_manager using template_json_builder's default."""
        return self._db_manager.get_database(SECTION_REPO_PROD_DB)

    def fetch_sections_with_metadata(
        self,
        query_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch sections with metadata using MongoDB aggregation pipeline.

        Uses database and collection names from template_json_builder.

        Args:
            query_filter: MongoDB query filter for sections (uses default if None)

        Returns:
            List of merged section documents (sections + metadata)

        Raises:
            DocumentNotFoundError: If no documents are found
            Exception: For other unexpected errors
        """
        filters = query_filter if query_filter is not None else self.DEFAULT_QUERY_FILTER

        self._logger.info(
            "Section Repository Service: Fetching sections with metadata via aggregation",
            database=SECTION_REPO_PROD_DB,
            query=filters,
        )

        try:
            db = self._get_db()
            documents = fetch_sections_with_metadata_sync(
                db=db,
                query_filter=filters,
                require_section_layout_description=True,
            )

            if not documents:
                self._logger.warning(
                    "No sections found matching query",
                    database=SECTION_REPO_PROD_DB,
                    query=filters,
                )
                raise DocumentNotFoundError(
                    f"No sections found matching filter: {filters}"
                )

            self._logger.info(
                "Fetched section repository documents (with metadata)",
                database=SECTION_REPO_PROD_DB,
                count=len(documents),
            )
            return documents

        except DocumentNotFoundError:
            raise
        except Exception as e:
            self._logger.error(
                f"Error fetching sections with metadata: {str(e)}",
                database=SECTION_REPO_PROD_DB,
            )
            raise

    def get_unique_l0_categories(
        self,
        query_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get unique L0 categories with counts.

        Args:
            query_filter: MongoDB query filter for sections (uses default if None)

        Returns:
            List of category objects with: l0_key, name, count, original_l0

        Raises:
            DocumentNotFoundError: If no documents are found
            Exception: For other unexpected errors
        """
        filters = query_filter if query_filter is not None else self.DEFAULT_QUERY_FILTER

        self._logger.info(
            "Section Repository Service: Fetching unique L0 categories",
            database=SECTION_REPO_PROD_DB,
            query=filters,
        )

        try:
            db = self._get_db()
            categories = get_unique_l0_categories_sync(
                db=db,
                query_filter=filters,
            )

            if not categories:
                self._logger.warning(
                    "No L0 categories found",
                    database=SECTION_REPO_PROD_DB,
                    query=filters,
                )
                raise DocumentNotFoundError(
                    f"No L0 categories found matching filter: {filters}"
                )

            self._logger.info(
                "Fetched unique L0 categories",
                database=SECTION_REPO_PROD_DB,
                count=len(categories),
            )
            return categories

        except DocumentNotFoundError:
            raise
        except Exception as e:
            self._logger.error(
                f"Error fetching unique L0 categories: {str(e)}",
                database=SECTION_REPO_PROD_DB,
            )
            raise

    def get_sections_by_l0(
        self,
        l0_category: str,
        query_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get sections filtered by L0 category with limited metadata.

        Args:
            l0_category: L0 category value to filter by (e.g., "banner", "footer")
            query_filter: Additional MongoDB query filter (merged with default)

        Returns:
            List of section documents with limited fields

        Raises:
            DocumentNotFoundError: If no documents are found
            Exception: For other unexpected errors
        """
        self._logger.info(
            "Section Repository Service: Fetching sections by L0 category",
            database=SECTION_REPO_PROD_DB,
            l0_category=l0_category,
        )

        try:
            db = self._get_db()
            documents = get_sections_by_l0_sync(
                db=db,
                l0_category=l0_category,
                query_filter=query_filter,
            )

            if not documents:
                self._logger.warning(
                    "No sections found for L0 category",
                    database=SECTION_REPO_PROD_DB,
                    l0_category=l0_category,
                )
                raise DocumentNotFoundError(
                    f"No sections found for L0 category: {l0_category}"
                )

            self._logger.info(
                "Fetched sections by L0 category (with limited metadata)",
                database=SECTION_REPO_PROD_DB,
                l0_category=l0_category,
                count=len(documents),
            )
            return documents

        except DocumentNotFoundError:
            raise
        except Exception as e:
            self._logger.error(
                f"Error fetching sections by L0 category: {str(e)}",
                database=SECTION_REPO_PROD_DB,
                l0_category=l0_category,
            )
            raise

    def get_distinct_tags(
        self,
        query_filter: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Get distinct tag values from the sections collection.
        Uses minimal query_filter (default {}) to return all tags.
        """
        filters = query_filter if query_filter is not None else {}
        db = self._get_db()
        return get_distinct_tags_sync(
            db=db,
            query_filter=filters,
        )

    def get_distinct_statuses(
        self,
        query_filter: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Get distinct status values from the sections collection.
        Uses minimal query_filter (default {}) to return all statuses.
        """
        filters = query_filter if query_filter is not None else {}
        db = self._get_db()
        return get_distinct_statuses_sync(
            db=db,
            query_filter=filters,
        )

    def get_distinct_semantic_tags(
        self,
        query_filter: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Get distinct semantic tag values from the sections collection.
        Uses minimal query_filter (default {}) to return all semantic tags.
        """
        filters = query_filter if query_filter is not None else {}
        db = self._get_db()
        return get_distinct_semantic_tags_sync(
            db=db,
            query_filter=filters,
        )

    def update_section_status(
        self,
        section_id: str,
        status: str,
    ) -> int:
        """
        Update a section's status by _id.
        Returns modified_count (0 if not found, 1 if updated).
        """
        db = self._get_db()
        return update_section_status_sync(
            db=db,
            section_id=section_id,
            status=status,
        )

    def get_developer_section_by_id(
        self,
        section_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a section by _id and return as DeveloperSection fields (JSON-serializable dict).
        Returns None if not found.
        """
        db = self._get_db()
        section = get_developer_section_by_id_sync(db=db, section_id=section_id)
        if not section:
            return None
        d = section.to_dict()
        d["section_id"] = str(d.get("_id", ""))
        return make_json_serializable(d)

    def update_section_semantic_tags(
        self,
        section_id: str,
        semantic_tags: List[str],
    ) -> int:
        """
        Update a section's semantic_tags by _id. Replaces the entire list.
        Returns modified_count (0 if not found, 1 if updated).
        """
        db = self._get_db()
        return update_section_semantic_tags_sync(
            db=db,
            section_id=section_id,
            semantic_tags=semantic_tags,
        )

    def fetch_sections(
        self,
        database_name: Optional[str],
        collection_name: Optional[str],
        query_filter: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Fetch section repository documents using the provided filter.

        LEGACY METHOD: Fetches from single collection.
        DEPRECATED: Use fetch_sections_with_metadata() for new code.
        Uses SECTION_REPO_PROD_DB and SECTION_REPO_SECTIONS_COLLECTION if database_name/collection_name are None.
        """
        from template_json_builder.db.queries import (
            SECTION_REPO_SECTIONS_COLLECTION,
        )

        db_name = database_name or SECTION_REPO_PROD_DB
        collection = collection_name or SECTION_REPO_SECTIONS_COLLECTION
        filters = query_filter

        self._logger.info(
            "Section Repository Service: Fetching section repository documents (LEGACY)",
            database=db_name,
            collection=collection,
            query=filters,
        )

        db = self._db_manager.get_database(db_name)
        documents = fetch_from_collection(
            collection_name=collection,
            query=filters,
            database=db,
        )

        self._logger.info(
            "Fetched section repository documents",
            database=db_name,
            collection=collection,
            count=len(documents),
        )
        return documents


__all__ = [
    "SectionRepositoryService",
    "DocumentNotFoundError",
]
