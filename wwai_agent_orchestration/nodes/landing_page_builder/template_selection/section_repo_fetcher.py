# nodes/smb/section_repo_fetcher.py

"""
Section Repository Fetcher Node (SMB-specific).

Fetches section repository from MongoDB with SMB-specific filtering.

UPDATED: Now fetches from TWO collections via aggregation pipeline:
- developer_hub_prod_sections (visual data, L0/L1, tags)
- developer_hub_prod_metadata (AI descriptions)

Query:
- tags: ["smb"] (SMB-specific sections only)
- status: ACTIVE
- section_ai_signals.section_layout_description: exists

Returns validated Pydantic models (stored as dicts in state).
"""

import time
from typing import Dict, Any, List

from langgraph.types import RunnableConfig

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.core.database import DocumentNotFoundError
from wwai_agent_orchestration.data.providers.section_catalog_provider import SectionCatalogProvider
from wwai_agent_orchestration.contracts.landing_page_builder.section_repo.section_repo import SectionRepositoryEntry
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import (
    LandingPageWorkflowState,
    SectionRepoResult,
    TemplateResult,
)
from wwai_agent_orchestration.nodes.landing_page_builder.template_selection.node_utils import (
    build_allowed_section_types_from_repo,
)

logger = get_logger(__name__)
section_catalog_provider = SectionCatalogProvider()


@NodeRegistry.register(
    name="section_repo_fetcher",
    description="Fetch SMB sections with metadata via aggregation (joins 2 collections)",
    max_retries=1,
    timeout=30,
    tags=["smb", "data", "mongodb", "aggregation"],
    display_name="Loading design library",
    show_node=False,
    show_output=False,
)
def section_repo_fetcher_node(
    state: LandingPageWorkflowState,
    config: RunnableConfig = None
) -> Dict[str, Any]:
    """
    Fetch section repository with SMB-specific filtering.
    
    UPDATED: Uses aggregation pipeline to join:
    - developer_hub_prod_sections (base section data)
    - developer_hub_prod_metadata (AI-generated descriptions)
    
    Query filters:
    - tags: ["smb"] (SMB sections only)
    - status: ACTIVE
    - section_layout_description: must exist in metadata
    
    All documents validated with Pydantic before storage.
    
    Args:
        state: LandingPageWorkflowState (not used, fetches all matching sections)
        config: Node configuration with database settings
        
    Returns:
        Dict with section_repo (List[Dict]) via .model_dump()
        
    Raises:
        Exception: If database fetch or validation fails
    """
    start_time = time.time()
    
    config = config or {}

    # Query filter (default: SMB sections with ACTIVE status)
    query_filter = config.get("configurable", {}).get("section_repo_query_filter")
    if query_filter is None:
        query_filter = {"status": "ACTIVE", "tag": "smb"}

    logger.info(
        "Fetching SMB section repository with metadata",
        node="section_repo_fetcher",
        query=query_filter
    )

    try:
        # ====================================================================
        # STEP 1: Query MongoDB via aggregation pipeline
        # ====================================================================
        try:
            documents = section_catalog_provider.fetch_sections_with_metadata(
                query_filter=query_filter
            )
        except DocumentNotFoundError:
            logger.warning(
                "No SMB sections found in repository",
                node="section_repo_fetcher",
                query=query_filter
            )
            
            # Return empty result (not an error - just no SMB sections yet)
            empty_result = SectionRepoResult(
                section_repo=[],
                section_repo_size=0,
                query_used=query_filter or {},
                allowed_section_types=[],
            )
            return {
                "template": TemplateResult(section_repo_result=empty_result),
            }
        
        logger.info(
            f"Fetched {len(documents)} documents from MongoDB (after join)",
            node="section_repo_fetcher"
        )
        
        # ====================================================================
        # STEP 2: Validate with Pydantic (FAIL FAST per document)
        # ====================================================================
        section_repo: List[Dict[str, Any]] = []
        parse_errors = []
        
        for idx, doc in enumerate(documents, 1):
            try:
                # Validate with Pydantic
                section_entry = SectionRepositoryEntry(**doc)
                
                # Convert to dict for state storage (JSON-serializable)
                # Pydantic field_serializers handle ObjectId → str conversion
                section_dict = section_entry.model_dump(by_alias=False)
                
                # Add string ID for easy access (since _id is ObjectId)
                section_dict['section_id'] = str(section_entry.id)
                
                section_repo.append(section_dict)
                
            except Exception as parse_error:
                # Log parse error but continue (some docs may be malformed)
                parse_errors.append({
                    'document_index': idx,
                    'error': str(parse_error),
                    'document_id': str(doc.get('_id', 'unknown'))
                })
                logger.warning(
                    f"Failed to parse document {idx} into SectionRepositoryEntry",
                    node="section_repo_fetcher",
                    error=str(parse_error),
                    document_id=str(doc.get('_id', 'unknown'))
                )
        
        # ====================================================================
        # STEP 3: Log Summary
        # ====================================================================
        if parse_errors:
            logger.warning(
                f"Failed to parse {len(parse_errors)}/{len(documents)} documents",
                node="section_repo_fetcher",
                parse_errors_count=len(parse_errors),
                first_5_errors=parse_errors[:5]
            )
        
        duration_ms = (time.time() - start_time) * 1000
        
        logger.info(
            "✅ SMB section repository fetched and validated (with metadata)",
            node="section_repo_fetcher",
            total_documents=len(documents),
            successfully_parsed=len(section_repo),
            parse_failures=len(parse_errors),
            duration_ms=round(duration_ms, 2)
        )
        
        # Warn if too few sections
        if len(section_repo) < 10:
            logger.warning(
                f"⚠️ Very few SMB sections in repository ({len(section_repo)}). "
                "Consider adding more SMB-tagged sections or check query filter.",
                node="section_repo_fetcher"
            )
        
        # ====================================================================
        # STEP 4: Build allowed_section_types from section_repo (L0/L1 type details)
        # ====================================================================
        configurable = config.get("configurable") or {}
        filter_type = configurable.get("filter_type") or config.get("filter_type", "ALL_TYPES")
        min_sections = configurable.get("min_sections_per_l0_l1") or config.get("min_sections_per_l0_l1", 1)
        data = getattr(state, "data", None)
        inp = getattr(state, "input", None)
        sector = (getattr(data, "derived_sector", None) if data else None) or (
            (inp.generic_context.sector if inp and inp.generic_context else None)
        )
        allowed_section_types = build_allowed_section_types_from_repo(
            section_repo,
            filter_type=filter_type,
            min_sections=min_sections,
            sector=sector,
        )
        
        # ====================================================================
        # STEP 5: Build Result with Pydantic Validation
        # ====================================================================
        result = SectionRepoResult(
            section_repo=section_repo,
            section_repo_size=len(section_repo),
            query_used=query_filter or {},
            allowed_section_types=allowed_section_types,
        )
        
        # ====================================================================
        # RETURN: nested template stage (SectionRepoResult for tracking) + ui_execution_log
        # ====================================================================
        return {
            "template": TemplateResult(section_repo_result=result),
        }
        
    except Exception as e:
        logger.error(
            f"❌ Failed to fetch SMB section repository: {str(e)}",
            node="section_repo_fetcher"
        )
        raise