# contracts/smb_workflow.py
"""
Pydantic schemas for SMB Recommendation Workflow.

State uses nested stage models (UserInput, DataCollectionResult, TemplateResult, etc.)
with reducers for LangGraph. External data uses google_maps_data and yelp_data dicts.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, Annotated
import operator

from wwai_agent_orchestration.contracts.landing_page_builder.execution_config import ExecutionConfig
from wwai_agent_orchestration.contracts.landing_page_builder.user_input import (
    UserInput,
    user_input_from_restored,
    BrandContext,
    GenericContext,
    WebsiteContext,
    ExternalDataContext
)


# Type alias for Pydantic compatibility (Pydantic v2 doesn't support TypedDict in model fields on Python < 3.12)
# At runtime, this is just Dict[str, Any], but type checkers will see it as AutopopulationLangGraphAgentsState
AutopopulationLangGraphStateDict = Dict[str, Any]  # type: ignore


# ============================================================================
# REDUCER FUNCTIONS
# ============================================================================

def deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(a)
    for k, v in b.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v      # last-writer-wins for scalars/lists
    return out


def deep_merge_reducer(
    old: Optional[AutopopulationLangGraphStateDict], 
    new: Optional[AutopopulationLangGraphStateDict]
) -> Optional[AutopopulationLangGraphStateDict]:
    """
    Reducer that deep merges AutopopulationLangGraphAgentsState dicts.
    Handles None cases: if old is None, returns new; if new is None, returns old.
    Uses the same deep_merge logic as AutopopulationLangGraphAgentsState fields.
    """
    if old is None:
        return new
    if new is None:
        return old
    # Both are dicts at runtime (TypedDict is just a type annotation)
    return deep_merge(old, new)  # type: ignore


def stage_merge_reducer(
    old: Optional[Any], new: Optional[Any]
) -> Optional[Any]:
    """
    Reducer for nested Pydantic stage models. Merges only explicitly-set fields
    from new into old. Handles old/new as either Pydantic models or dicts
    (e.g. when state is restored from checkpoint and channel value is deserialized).
    """
    if old is None:
        return new
    if new is None:
        return old
    if isinstance(old, BaseModel):
        merged = old.model_dump()
    elif isinstance(old, dict):
        merged = dict(old)
    else:
        merged = {}
    if isinstance(new, BaseModel):
        updates = new.model_dump(exclude_unset=True)
    elif isinstance(new, dict):
        updates = new
    else:
        updates = {}
    merged.update(updates)
    # Return a model instance when possible so the channel stays typed
    if isinstance(new, BaseModel):
        return type(new)(**merged)
    if isinstance(old, BaseModel):
        return type(old)(**merged)
    return merged


# ============================================================================
# NESTED DATA MODELS
# ============================================================================

class BusinessInfo(BaseModel):
    """Extracted business essentials for auto-population."""
    business_name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    hours: Optional[str] = None
    website: Optional[str] = None
    google_maps_url: Optional[str] = None
    yelp_url: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    price_level: Optional[str] = None
    categories: Optional[List[str]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class CampaignIntent(BaseModel):
    """LLM-synthesized campaign brief."""
    campaign_query: str
    business_overview: Optional[str] = None
    target_audience: Optional[str] = None
    brand_voice: Optional[str] = None
    key_services: Optional[List[str]] = None
    competitive_advantages: Optional[List[str]] = None


# ============================================================================
# NODE RESULT MODELS
# ============================================================================

class SectionRepoResult(BaseModel):
    """Output from section_repo_fetcher node (section_repo + allowed L0/L1 types + query used for tracking)."""
    section_repo: List[Dict[str, Any]]
    section_repo_size: int
    query_used: Dict[str, Any]
    allowed_section_types: Optional[List[Dict[str, Any]]] = None


class TradeAssignment(BaseModel):
    """Single trade assignment with confidence and reasoning."""
    trade: str
    parent_category: str
    confidence: str
    reasoning: str


class TradeClassificationResult(BaseModel):
    """Result from trade classification node."""
    success: bool
    assigned_trades: Optional[List[TradeAssignment]] = None
    business_summary: Optional[str] = None
    timestamp: Optional[str] = None
    error: Optional[str] = None


# ============================================================================
# STAGE MODELS (nested state for pipeline phases)
# ============================================================================


class DataCollectionResult(BaseModel):
    """Stage 1 output: external data + campaign intent."""
    google_maps_data: Optional[Dict[str, Any]] = None
    yelp_data: Optional[Dict[str, Any]] = None
    google_data_valid: bool = False
    yelp_scraping_success: bool = False
    yelp_scraping_error: Optional[str] = None
    derived_sector: Optional[str] = None
    business_info: Optional[BusinessInfo] = None
    campaign_intent: Optional[CampaignIntent] = None
    trade_classification_result: Optional[TradeClassificationResult] = None
    # Page context from URL (intent subgraph): merged Gemini/ScrapingBee/screenshot extraction
    page_context: Optional[str] = None
    extraction_methods_used: Optional[List[str]] = None
    input_type: Optional[str] = None  # e.g. "page_context_only", "query_and_page_context"


class TemplateResult(BaseModel):
    """Stage 2 output: template generation + section repo."""
    # Build section repo, on which we will apply retrieval
    section_repo_result: Optional[SectionRepoResult] = None
    
    # Raw L0/L1 results from the LLM. This is the raw result from the LLM, 
    # before we apply the template checks like all L0/L1 should be present.
    raw_l0_l1_result: Optional[Dict[str, Any]] = None
    
    # Whether the template was picked from the cache.
    section_cache_hit: Optional[bool] = None

    # Template generation results (3x templates)
    templates: Optional[List[Dict[str, Any]]] = None

    # Template evaluations, used for reflection (3x templates)
    template_evaluations: Optional[Dict[str, Any]] = None
    # Refined templates (3x templates) using template evaluations
    refined_templates: Optional[List[Dict[str, Any]]] = None
    # Template evaluation iteration.
    iteration: int = 0

    # Ephemeral: payload for current resolve_template_sections_from_repo invocation (from Send)
    section_retrieval_payload: Optional[Dict[str, Any]] = None


class PostProcessResult(BaseModel):
    """Stage 4 output: compilation, screenshots, DB save."""
    template_compilation_results: Optional[Dict[str, Any]] = None
    html_compilation_results: Optional[Dict[str, Any]] = None
    screenshot_capture_results: Optional[Dict[str, Any]] = None


# ============================================================================
# MAIN WORKFLOW STATE
# ============================================================================

class LandingPageWorkflowState(BaseModel):
    """
    Main state for SMB Recommendation Workflow.
    Uses nested stage models (input, data, template, post_process, meta) with
    stage_merge_reducer; reflection lives in execution_config.
    """

    # Immutable user input (from request form)
    input: UserInput
    # Execution config, updated per run. It contains the execution state of the workflow.
    execution_config: Optional[ExecutionConfig] = None

    # Data collection results.
    data: Annotated[Optional[DataCollectionResult], stage_merge_reducer] = None
    
    # Template generation results.
    template: Annotated[Optional[TemplateResult], stage_merge_reducer] = None
    
    # The final template recommendations, from the parallel section_retriever nodes.
    resolved_template_recommendations: Annotated[List[Dict[str, Any]], operator.add] = Field(
        default_factory=list,
        description="Results from parallel section_retriever nodes",
    )

    # Stable mapping from repo_section_id_index to unique_section_id.
    # This connects the recommended section ids to template json with styles for each 
    # section in the template.
    template_unique_section_id_map: Optional[Dict[str, str]] = Field(
        default=None,
        description="Stable mapping from repo_section_id_index to unique_section_id.",
    )

    # Autopopulation state. 
    autopopulation_langgraph_state: Annotated[
        Optional[AutopopulationLangGraphStateDict], deep_merge_reducer
    ] = Field(
        default=None,
        description="Autopopulation state (deep_merge reducer)",
    )

    # Post-processing results
    post_process: Annotated[Optional[PostProcessResult], stage_merge_reducer] = None

    # UI execution log. This is the log of the execution of the workflow, used for UI streaming.
    ui_execution_log: Annotated[List[Dict[str, Any]], operator.add] = Field(
        default_factory=list,
        description="Accumulated node execution entries for UI streaming",
    )

    class Config:
        arbitrary_types_allowed = True
        extra = "forbid"

    @classmethod
    def from_restored_state(
        cls,
        restored: Dict[str, Any],
        *,
        generation_version_id: Optional[str] = None,
        palette: Optional[Dict[str, Any]] = None,
        font_family: Optional[str] = None,
        execution_config: Any = None,
    ) -> "LandingPageWorkflowState":
        """
        Build LandingPageWorkflowState from a checkpoint state dict (nested only).
        Used by workflows that restore from checkpoint.
        """
        def get(key: str, default: Any = None) -> Any:
            return restored.get(key, default)

        # Input: build nested UserInput (supports restored dict with nested or flat keys)
        inp = restored.get("input")
        if inp is not None:
            user_input = user_input_from_restored(
                inp if isinstance(inp, dict) else inp.model_dump(),
                palette=palette,
                font_family=font_family,
                generation_version_id=generation_version_id,
            )
        else:
            user_input = UserInput(
                business_name="",
                brand_context=BrandContext(palette=palette, font_family=font_family),
                generation_version_id=generation_version_id,
            )

        # Data: require nested
        data = restored.get("data")
        if data is not None:
            data_result = DataCollectionResult(**(data if isinstance(data, dict) else data.model_dump()))
        else:
            data_result = DataCollectionResult()

        # Template: require nested
        t = restored.get("template")
        if t is not None:
            template_result = TemplateResult(**(t if isinstance(t, dict) else t.model_dump()))
        else:
            template_result = TemplateResult()

        # Post_process: require nested
        p = restored.get("post_process")
        if p is not None:
            post_result = PostProcessResult(**(p if isinstance(p, dict) else p.model_dump()))
        else:
            post_result = PostProcessResult()

        # Meta: require nested
        m = restored.get("meta")

        return cls(
            input=user_input,
            execution_config=execution_config,
            data=data_result,
            template=template_result,
            post_process=post_result,
            resolved_template_recommendations=get("resolved_template_recommendations", []),
            autopopulation_langgraph_state=get("autopopulation_langgraph_state"),
            template_unique_section_id_map=get("template_unique_section_id_map"),
            ui_execution_log=get("ui_execution_log", []),
        )