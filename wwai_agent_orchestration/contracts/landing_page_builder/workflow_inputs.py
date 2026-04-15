"""
Landing Page Builder Workflow Input Types.

This module defines typed input dataclasses for all Landing Page Builder workflow types.
Each workflow type has a corresponding input dataclass that maps one-to-one
with the workflows created by LandingPageWorkflowFactory.

Uses the same context classes as UserInput (GenericContext, WebsiteContext,
BrandContext, ExternalDataContext) so workflow inputs are segregated in the
same fashion. build_stream_kwargs passes context objects to workflow.stream().

Used by workflow_background_runner to provide type-safe workflow execution.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union, Literal

from wwai_agent_orchestration.contracts.landing_page_builder.user_input import (
    GenericContext,
    WebsiteContext,
    BrandContext,
    ExternalDataContext,
)


# =============================================================================
# WORKFLOW INPUT DATACLASSES (nested context, same shape as UserInput)
# =============================================================================

@dataclass
class TradeClassificationInput:
    """Input parameters for trade classification workflow."""
    business_name: str
    business_id: str
    execution_config: Any
    request_id: str
    generic_context: GenericContext = field(default_factory=GenericContext)
    website_context: WebsiteContext = field(default_factory=WebsiteContext)
    external_data_context: ExternalDataContext = field(default_factory=ExternalDataContext)


@dataclass
class TemplateSelectionInput:
    """Input parameters for template selection workflow."""
    business_name: str
    business_id: str
    execution_config: Any
    request_id: str
    generic_context: GenericContext = field(default_factory=GenericContext)
    website_context: WebsiteContext = field(default_factory=WebsiteContext)
    external_data_context: ExternalDataContext = field(default_factory=ExternalDataContext)


@dataclass
class LandingPageInput:
    """Input parameters for full Landing Page Builder recommendation workflow."""
    business_name: str
    business_id: str
    execution_config: Any
    request_id: str
    generic_context: GenericContext = field(default_factory=GenericContext)
    website_context: WebsiteContext = field(default_factory=WebsiteContext)
    brand_context: BrandContext = field(default_factory=BrandContext)
    external_data_context: ExternalDataContext = field(default_factory=ExternalDataContext)


# =============================================================================
# AUTOPOP INPUTS (restore from checkpoint; use brand_context)
# =============================================================================

@dataclass
class PartialAutopopInput:
    """Input parameters for partial autopop workflow."""
    request_id: str
    source_thread_id: str  # Thread ID to restore state from
    execution_config: Any
    regenerate_mode: Optional[Literal["styles", "text", "media", "all"]] = None
    brand_context: BrandContext = field(default_factory=BrandContext)


@dataclass
class PresetSectionsInput:
    """Input parameters for preset sections workflow (bypass template selection)."""
    business_name: str
    business_id: str
    request_id: str
    section_ids: List[str]
    execution_config: Any
    generic_context: GenericContext = field(default_factory=GenericContext)
    website_context: WebsiteContext = field(default_factory=WebsiteContext)
    brand_context: BrandContext = field(default_factory=BrandContext)
    external_data_context: ExternalDataContext = field(default_factory=ExternalDataContext)
    page_type: str = "homepage"
    # We use parent generation version id, so that in compilation node, we can 
    # get the header and footer of parent page, in case page type is non homepage.
    parent_generation_version_id: Optional[str] = None


@dataclass
class RegenerateSectionInput:
    """Regenerate content for a section at index. Structure already in place (from add_section_in_place)."""
    request_id: str
    source_thread_id: str   # Parent generation version id.
    section_index: int     # 0-based index of section to regenerate
    section_id: str        # Repo ObjectId of the section at that index
    execution_config: Any


# =============================================================================
# UNION TYPES
# =============================================================================

LandingPageWorkflowInput = Union[
    TradeClassificationInput,
    TemplateSelectionInput,
    LandingPageInput,
    PartialAutopopInput,
    PresetSectionsInput,
    RegenerateSectionInput,
]

LandingPageWorkflowType = Literal[
    "trade_classification",
    "template_selection",
    "landing_page",
    "partial_autopop",
    "preset_sections",
    "regenerate_section",
]


# =============================================================================
# PRESET SECTIONS INPUT SERIALIZATION (for eval case storage)
# =============================================================================


def _context_to_dict(ctx: Any) -> Dict[str, Any]:
    """Convert a Pydantic context to a JSON-serializable dict."""
    if hasattr(ctx, "model_dump"):
        return ctx.model_dump()
    if hasattr(ctx, "__dict__"):
        return dict(ctx.__dict__)
    return {}


def preset_sections_input_to_dict(psi: PresetSectionsInput) -> Dict[str, Any]:
    """Convert PresetSectionsInput to a JSON-serializable dict for storage."""
    return {
        "business_name": psi.business_name,
        "business_id": psi.business_id,
        "request_id": psi.request_id,
        "section_ids": list(psi.section_ids),
        "generic_context": _context_to_dict(psi.generic_context),
        "website_context": _context_to_dict(psi.website_context),
        "brand_context": _context_to_dict(psi.brand_context),
        "external_data_context": _context_to_dict(psi.external_data_context),
        "page_type": psi.page_type,
        "parent_generation_version_id": psi.parent_generation_version_id,
    }


def preset_sections_input_from_dict(d: Dict[str, Any]) -> PresetSectionsInput:
    """Reconstruct PresetSectionsInput from a dict (e.g. from eval case storage)."""
    return PresetSectionsInput(
        business_name=d.get("business_name", ""),
        business_id=d.get("business_id", ""),
        request_id=d.get("request_id", ""),
        section_ids=list(d.get("section_ids", [])),
        execution_config=None,
        generic_context=GenericContext(**(d.get("generic_context") or {})),
        website_context=WebsiteContext(**(d.get("website_context") or {})),
        brand_context=BrandContext(**(d.get("brand_context") or {})),
        external_data_context=ExternalDataContext(**(d.get("external_data_context") or {})),
        page_type=d.get("page_type", "homepage"),
        parent_generation_version_id=d.get("parent_generation_version_id"),
    )


# =============================================================================
# LANDING PAGE INPUT SERIALIZATION (for eval case storage)
# =============================================================================


def landing_page_input_to_dict(lpi: LandingPageInput) -> Dict[str, Any]:
    """Convert LandingPageInput to a JSON-serializable dict for storage."""
    return {
        "business_name": lpi.business_name,
        "business_id": lpi.business_id,
        "request_id": lpi.request_id,
        "generic_context": _context_to_dict(lpi.generic_context),
        "website_context": _context_to_dict(lpi.website_context),
        "brand_context": _context_to_dict(lpi.brand_context),
        "external_data_context": _context_to_dict(lpi.external_data_context),
    }


def landing_page_input_from_dict(d: Dict[str, Any]) -> LandingPageInput:
    """Reconstruct LandingPageInput from a dict (e.g. from eval case storage)."""
    return LandingPageInput(
        business_name=d.get("business_name", ""),
        business_id=d.get("business_id", ""),
        execution_config=None,
        request_id=d.get("request_id", ""),
        generic_context=GenericContext(**(d.get("generic_context") or {})),
        website_context=WebsiteContext(**(d.get("website_context") or {})),
        brand_context=BrandContext(**(d.get("brand_context") or {})),
        external_data_context=ExternalDataContext(**(d.get("external_data_context") or {})),
    )


# =============================================================================
# TEMPLATE SELECTION INPUT SERIALIZATION (for eval case storage)
# =============================================================================


def template_selection_input_to_dict(tsi: TemplateSelectionInput) -> Dict[str, Any]:
    """Convert TemplateSelectionInput to a JSON-serializable dict for storage."""
    return {
        "business_name": tsi.business_name,
        "business_id": tsi.business_id,
        "request_id": tsi.request_id,
        "generic_context": _context_to_dict(tsi.generic_context),
        "website_context": _context_to_dict(tsi.website_context),
        "external_data_context": _context_to_dict(tsi.external_data_context),
    }


def template_selection_input_from_dict(d: Dict[str, Any]) -> TemplateSelectionInput:
    """Reconstruct TemplateSelectionInput from a dict (e.g. from eval case storage)."""
    return TemplateSelectionInput(
        business_name=d.get("business_name", ""),
        business_id=d.get("business_id", ""),
        execution_config=None,
        request_id=d.get("request_id", ""),
        generic_context=GenericContext(**(d.get("generic_context") or {})),
        website_context=WebsiteContext(**(d.get("website_context") or {})),
        external_data_context=ExternalDataContext(**(d.get("external_data_context") or {})),
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _stream_kwargs_from_nested_input(
    wi: Union[TradeClassificationInput, TemplateSelectionInput, LandingPageInput],
) -> Dict[str, Any]:
    """Build stream kwargs by passing context objects through (no flattening)."""
    d: Dict[str, Any] = {
        "business_name": wi.business_name,
        "business_id": wi.business_id,
        "request_id": wi.request_id,
        "execution_config": wi.execution_config,
        "generic_context": wi.generic_context,
        "website_context": wi.website_context,
        "external_data_context": wi.external_data_context,
    }
    if isinstance(wi, LandingPageInput):
        d["brand_context"] = wi.brand_context
    return d


def build_stream_kwargs(workflow_input: LandingPageWorkflowInput) -> Dict[str, Any]:
    """
    Build stream kwargs dictionary from workflow input.

    For nested input types (TradeClassification, TemplateSelection, LandingPage),
    passes context objects through to workflow.stream().
    For PartialAutopop, passes brand_context object.
    For PresetSectionsInput, passes section_ids and all context objects.

    Args:
        workflow_input: One of the SMB workflow input types

    Returns:
        Dictionary of kwargs to pass to workflow.stream()
    """
    valid_types = (
        TradeClassificationInput,
        TemplateSelectionInput,
        LandingPageInput,
        PartialAutopopInput,
        PresetSectionsInput,
        RegenerateSectionInput,
    )
    if not isinstance(workflow_input, valid_types):
        raise ValueError(
            f"Invalid workflow_input type: {type(workflow_input)}. "
            "Must be one of the LandingPageWorkflowInput types."
        )
    if isinstance(workflow_input, (TradeClassificationInput, TemplateSelectionInput, LandingPageInput)):
        return _stream_kwargs_from_nested_input(workflow_input)
    if isinstance(workflow_input, PresetSectionsInput):
        return {
            "business_name": workflow_input.business_name,
            "business_id": workflow_input.business_id,
            "request_id": workflow_input.request_id,
            "section_ids": workflow_input.section_ids,
            "execution_config": workflow_input.execution_config,
            "generic_context": workflow_input.generic_context,
            "website_context": workflow_input.website_context,
            "brand_context": workflow_input.brand_context,
            "external_data_context": workflow_input.external_data_context,
            "page_type": workflow_input.page_type,
            "parent_generation_version_id": workflow_input.parent_generation_version_id,
        }
    if isinstance(workflow_input, RegenerateSectionInput):
        return {
            "request_id": workflow_input.request_id,
            "source_thread_id": workflow_input.source_thread_id,
            "section_id": workflow_input.section_id,
            "section_index": workflow_input.section_index,
            "execution_config": workflow_input.execution_config,
        }
    # PartialAutopopInput: pass brand_context object
    d: Dict[str, Any] = {
        "request_id": workflow_input.request_id,
        "source_thread_id": workflow_input.source_thread_id,
        "execution_config": workflow_input.execution_config,
        "brand_context": workflow_input.brand_context,
    }
    if isinstance(workflow_input, PartialAutopopInput):
        d["regenerate_mode"] = workflow_input.regenerate_mode
    return d


def get_workflow_type(workflow_input: LandingPageWorkflowInput) -> LandingPageWorkflowType:
    """
    Determine workflow type from input.

    Args:
        workflow_input: One of the SMB workflow input types

    Returns:
        Workflow type string
    """
    if isinstance(workflow_input, TradeClassificationInput):
        return "trade_classification"
    elif isinstance(workflow_input, TemplateSelectionInput):
        return "template_selection"
    elif isinstance(workflow_input, LandingPageInput):
        return "landing_page"
    elif isinstance(workflow_input, PartialAutopopInput):
        return "partial_autopop"
    elif isinstance(workflow_input, PresetSectionsInput):
        return "preset_sections"
    elif isinstance(workflow_input, RegenerateSectionInput):
        return "regenerate_section"
    else:
        raise ValueError(
            f"Invalid workflow_input type: {type(workflow_input)}. "
            "Must be one of the LandingPageWorkflowInput types."
        )


def get_request_id(workflow_input: LandingPageWorkflowInput) -> str:
    """
    Extract request_id from workflow input.

    Args:
        workflow_input: One of the SMB workflow input types

    Returns:
        Request ID string
    """
    return workflow_input.request_id


def get_workflow_name(workflow_input: LandingPageWorkflowInput) -> str:
    """
    Get a descriptive name for the workflow for logging purposes.

    Args:
        workflow_input: One of the SMB workflow input types

    Returns:
        String name for the workflow
    """
    if isinstance(workflow_input, TradeClassificationInput):
        return f"trade_classification_{workflow_input.business_name}"
    elif isinstance(workflow_input, TemplateSelectionInput):
        return f"template_selection_{workflow_input.business_name}"
    elif isinstance(workflow_input, LandingPageInput):
        return workflow_input.business_name
    elif isinstance(workflow_input, PartialAutopopInput):
        mode = workflow_input.regenerate_mode or "all"
        return f"partial_autopop_{mode}_{workflow_input.source_thread_id[:8]}"
    elif isinstance(workflow_input, PresetSectionsInput):
        return f"preset_sections_{workflow_input.business_name}"
    elif isinstance(workflow_input, RegenerateSectionInput):
        return f"regenerate_section_{workflow_input.source_thread_id[:8]}"
    else:
        raise ValueError(
            f"Invalid workflow_input type: {type(workflow_input)}. "
            "Must be one of the LandingPageWorkflowInput types."
        )
