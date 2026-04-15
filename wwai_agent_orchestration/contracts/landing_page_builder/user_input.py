"""
UserInput and context sub-models for landing page workflow.

Defines GenericContext, WebsiteContext, BrandContext, ExternalDataContext, UserInput,
restore helper (user_input_from_restored), and state-resolution helpers for
page_url/query from state (nested input.generic_context or top-level).
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Union


# --- Context sub-models (extensible buckets) ---


class GenericContext(BaseModel):
    """User-provided context: query, sector, or page URL."""
    query: Optional[str] = None
    sector: Optional[str] = None
    page_url: Optional[str] = None


class WebsiteContext(BaseModel):
    """Website goals and tone."""
    website_intention: str = "generate_leads"
    website_tone: str = "professional"


class BrandContext(BaseModel):
    """Brand / visual identity."""
    palette: Optional[Dict[str, Any]] = None
    font_family: Optional[str] = None


class ExternalDataContext(BaseModel):
    """References to external data (Yelp, Google, etc.)."""
    yelp_url: Optional[str] = None
    google_places_data: Optional[Dict[str, Any]] = None


class UserInput(BaseModel):
    """Immutable user input from the request form. Never updated by nodes."""
    # Identity (who and which run)
    business_name: str
    business_id: Optional[str] = None
    generation_version_id: Optional[str] = None
    # Multi-page support, store the type of page, that corresponds to the generation version id.
    page_type: str = "homepage"
    # Context buckets (extensible)
    generic_context: GenericContext = Field(default_factory=GenericContext)
    website_context: WebsiteContext = Field(default_factory=WebsiteContext)
    brand_context: BrandContext = Field(default_factory=BrandContext)
    external_data_context: ExternalDataContext = Field(default_factory=ExternalDataContext)


def user_input_from_restored(
    inp: Dict[str, Any],
    *,
    palette: Optional[Dict[str, Any]] = None,
    font_family: Optional[str] = None,
    generation_version_id: Optional[str] = None,
) -> UserInput:
    """Build UserInput from restored checkpoint dict (nested or legacy flat keys)."""
    def g(key: str, default: Any = None) -> Any:
        return inp.get(key, default)

    if "generic_context" in inp:
        gc = inp["generic_context"]
        generic_context = GenericContext(**(gc if isinstance(gc, dict) else gc.model_dump()))
    else:
        generic_context = GenericContext(
            query=g("query"),
            sector=g("sector"),
            page_url=g("page_url"),
        )
    if "website_context" in inp:
        wc = inp["website_context"]
        website_context = WebsiteContext(**(wc if isinstance(wc, dict) else wc.model_dump()))
    else:
        website_context = WebsiteContext(
            website_intention=g("website_intention", "generate_leads"),
            website_tone=g("website_tone", "professional"),
        )
    if "brand_context" in inp:
        bc = inp["brand_context"]
        bc_dict = dict(bc if isinstance(bc, dict) else bc.model_dump())
        # Apply palette/font_family overrides when provided (for partial_autopop)
        if palette is not None:
            bc_dict["palette"] = palette
        if font_family is not None:
            bc_dict["font_family"] = font_family
        brand_context = BrandContext(**bc_dict)
    else:
        brand_context = BrandContext(
            palette=palette if palette is not None else g("palette"),
            font_family=font_family if font_family is not None else g("font_family"),
        )
    if "external_data_context" in inp:
        ed = inp["external_data_context"]
        external_data_context = ExternalDataContext(**(ed if isinstance(ed, dict) else ed.model_dump()))
    else:
        external_data_context = ExternalDataContext(
            yelp_url=g("yelp_url"),
            google_places_data=g("google_places_data"),
        )

    return UserInput(
        business_name=g("business_name", ""),
        business_id=g("business_id"),
        generation_version_id=generation_version_id if generation_version_id is not None else g("generation_version_id"),
        page_type=g("page_type", "homepage"),
        generic_context=generic_context,
        website_context=website_context,
        brand_context=brand_context,
        external_data_context=external_data_context,
    )


# --- State-resolution helpers (for intent subgraph / url_page_intent) ---


def get_page_url_from_state(state: Union[Any, dict]) -> Optional[str]:
    """Resolve page_url from state (nested input.generic_context or top-level)."""
    if hasattr(state, "input") and state.input is not None and hasattr(state.input, "generic_context") and state.input.generic_context is not None:
        return getattr(state.input.generic_context, "page_url", None) or None
    if isinstance(state, dict):
        inp = state.get("input")
        if isinstance(inp, dict) and inp.get("generic_context"):
            gc = inp["generic_context"]
            return gc.get("page_url") if isinstance(gc, dict) else getattr(gc, "page_url", None)
        return state.get("page_url")
    return getattr(state, "page_url", None)


def get_query_from_state(state: Union[Any, dict]) -> Optional[str]:
    """Resolve query from state (nested input.generic_context or top-level)."""
    if hasattr(state, "input") and state.input is not None and hasattr(state.input, "generic_context") and state.input.generic_context is not None:
        return getattr(state.input.generic_context, "query", None) or None
    if isinstance(state, dict):
        inp = state.get("input")
        if isinstance(inp, dict) and inp.get("generic_context"):
            gc = inp["generic_context"]
            return gc.get("query") if isinstance(gc, dict) else getattr(gc, "query", None)
        return state.get("query")
    return getattr(state, "query", None)
