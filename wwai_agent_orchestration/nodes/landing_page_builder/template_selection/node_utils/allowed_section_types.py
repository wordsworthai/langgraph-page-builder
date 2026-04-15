"""
Build allowed (L0, L1) section types from section repo.

Pure functions used by section_repo_fetcher and downstream validation.
"""

from typing import Dict, Any, List, Optional, Set, Tuple
from collections import defaultdict

from wwai_agent_orchestration.core.observability.logger import get_logger

logger = get_logger(__name__)


def build_type_details_from_section_repo(
    section_repo: List[Dict[str, Any]],
    valid_l0_l1_pairs: Optional[Set[Tuple[str, str]]] = None,
) -> List[Dict[str, Any]]:
    """
    Build type-detail dicts from section_repo. One row per (section_l0, section_l1).
    If valid_l0_l1_pairs is None, include all unique pairs in section_repo;
    otherwise only include pairs in valid_l0_l1_pairs.
    """
    seen: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for entry in section_repo:
        l0 = entry.get("section_l0")
        l1 = entry.get("section_l1")
        if not l0 or not l1:
            continue
        key = (l0, l1)
        if valid_l0_l1_pairs is not None and key not in valid_l0_l1_pairs:
            continue
        if key not in seen:
            seen[key] = entry

    result = []
    for (l0, l1), entry in seen.items():
        description = (
            entry.get("section_layout_description")
            or entry.get("content_description")
            or ""
        )
        result.append({
            "section_type_l1": l0,
            "section_subtype_l2": l1,
            "Description": description,
            "section_category": l0,
            "Typical Section Index": "1",
        })
    return result


def build_allowed_section_types_from_repo(
    section_repo: List[Dict[str, Any]],
    filter_type: str = "ALL_TYPES",
    min_sections: int = 1,
    sector: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Build the list of allowed (L0, L1) section types from section_repo.

    Strategies:
    - ALL_TYPES: One type-detail row per unique (L0, L1) in section_repo.
    - GENERIC_FILTRATION: Only (L0, L1) with min_sections+ occurrences across all industries.
    - INDUSTRY_FILTRATION: Only (L0, L1) with min_sections+ in target sector (fallback to generic if < 10 pairs).

    Returns:
        List of type-detail dicts (section_type_l1, section_subtype_l2, Description, etc.).
    """
    if not section_repo:
        return []

    unique_pairs_count = len({
        (e.get("section_l0"), e.get("section_l1"))
        for e in section_repo
        if e.get("section_l0") and e.get("section_l1")
    })

    if filter_type == "ALL_TYPES":
        result = build_type_details_from_section_repo(section_repo, valid_l0_l1_pairs=None)
        logger.debug(
            "build_allowed_section_types_from_repo ALL_TYPES",
            original_count=unique_pairs_count,
            result_count=len(result),
        )
        return result

    # GENERIC or INDUSTRY FILTRATION: compute (L0, L1) counts
    l0_l1_distribution_all: Dict[Tuple[str, str], int] = defaultdict(int)
    l0_l1_distribution_industry: Dict[Tuple[str, str], int] = defaultdict(int)

    for entry in section_repo:
        section_l0 = entry.get("section_l0")
        section_l1 = entry.get("section_l1")
        entry_industry = entry.get("industry")
        if not section_l0 or not section_l1:
            continue
        l0_l1_key = (section_l0, section_l1)
        l0_l1_distribution_all[l0_l1_key] += 1
        if sector and entry_industry == sector:
            l0_l1_distribution_industry[l0_l1_key] += 1

    if filter_type == "INDUSTRY_FILTRATION" and sector:
        valid_l0_l1_pairs = {
            k for k, count in l0_l1_distribution_industry.items()
            if count >= min_sections
        }
        if len(valid_l0_l1_pairs) < 10:
            logger.debug(
                "build_allowed_section_types_from_repo INDUSTRY fallback to GENERIC",
                sector=sector,
                industry_pairs=len(valid_l0_l1_pairs),
            )
            valid_l0_l1_pairs = {
                k for k, count in l0_l1_distribution_all.items()
                if count >= min_sections
            }
    else:
        valid_l0_l1_pairs = {
            k for k, count in l0_l1_distribution_all.items()
            if count >= min_sections
        }

    result = build_type_details_from_section_repo(section_repo, valid_l0_l1_pairs=valid_l0_l1_pairs)
    logger.debug(
        "build_allowed_section_types_from_repo",
        filter_type=filter_type,
        original_count=unique_pairs_count,
        result_count=len(result),
    )
    return result
