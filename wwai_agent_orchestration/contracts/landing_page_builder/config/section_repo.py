"""
Section repository configuration for Landing Page Builder Workflow.
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class SectionRepoConfig:
    """Section repo fetch and type-details filter."""

    section_repo_database: str = field(default_factory=lambda: os.environ.get("SECTION_REPO_DATABASE", ""))
    section_repo_collection: str = field(default_factory=lambda: os.environ.get("SECTION_REPO_COLLECTION", ""))
    metadata_collection: str = field(default_factory=lambda: os.environ.get("SECTION_REPO_METADATA_COLLECTION", ""))
    section_repo_query_filter: Dict[str, Any] = None
    max_sections_per_l0_l1: int = 3
    filter_type: str = "ALL_TYPES"
    min_sections_per_l0_l1: int = 0

    def __post_init__(self):
        if self.section_repo_query_filter is None:
            self.section_repo_query_filter = {"status": "ACTIVE", "tag": "smb"}
