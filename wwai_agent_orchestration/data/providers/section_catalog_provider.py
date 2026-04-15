"""
Facade provider for section catalog queries.
"""

from typing import Dict, Any, List, Optional

from wwai_agent_orchestration.data.repositories.section_repository import SectionRepositoryService


class SectionCatalogProvider:
    """Provider facade over SectionRepositoryService."""

    def __init__(self):
        self._service = SectionRepositoryService()

    def fetch_sections_with_metadata(
        self,
        query_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        return self._service.fetch_sections_with_metadata(
            query_filter=query_filter,
        )

    def get_unique_l0_categories(
        self,
        query_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        return self._service.get_unique_l0_categories(
            query_filter=query_filter,
        )

    def get_sections_by_l0(
        self,
        l0_category: str,
        query_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        return self._service.get_sections_by_l0(
            l0_category=l0_category,
            query_filter=query_filter,
        )
