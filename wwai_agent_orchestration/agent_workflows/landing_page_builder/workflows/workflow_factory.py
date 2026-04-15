# agent_workflows/landing_page_builder/workflows/workflow_factory.py
"""
Landing Page Builder Workflow Factory.

Factory pattern for creating Landing Page Builder workflow instances based on mode.
"""

from typing import Dict, Any, Literal, Optional

from wwai_agent_orchestration.agent_workflows.landing_page_builder.workflows.base_workflow import BaseLandingPageWorkflow
from wwai_agent_orchestration.agent_workflows.landing_page_builder.workflows.trade_classification_workflow import TradeClassificationWorkflow
from wwai_agent_orchestration.agent_workflows.landing_page_builder.workflows.template_selection_workflow import TemplateSelectionWorkflow
from wwai_agent_orchestration.agent_workflows.landing_page_builder.workflows.landing_page_builder_workflow import LandingPageWorkflow
from wwai_agent_orchestration.agent_workflows.landing_page_builder.workflows.partial_autopop_workflow import PartialAutopopWorkflow
from wwai_agent_orchestration.agent_workflows.landing_page_builder.workflows.preset_sections_workflow import PresetSectionsLandingPageWorkflow
from wwai_agent_orchestration.agent_workflows.landing_page_builder.workflows.regenerate_section_workflow import RegenerateSectionWorkflow


class LandingPageWorkflowFactory:
    """Factory for creating Landing Page Builder workflow instances."""
    
    @staticmethod
    def create(
        mode: Literal["trade_classification", "template_selection", "landing_page", "full", "partial_autopop", "preset_sections", "regenerate_section"],
        config: Dict[str, Any] = None,
        regenerate_mode: Optional[Literal["styles", "text", "media", "all"]] = None
    ) -> BaseLandingPageWorkflow:
        """
        Create a workflow instance based on mode.
        
        Args:
            mode: Workflow type
                - "trade_classification": Quick trade/industry classification
                - "template_selection": Template generation without autopop
                - "landing_page": Complete end-to-end recommendation (alias: "full" for backward compat)
                - "partial_autopop": Re-run specific parts of autopop (styles, text, or media)
                - "preset_sections": Bypass template selection, take section IDs directly
                - "regenerate_section": Regenerate content for a section at index (section must be in place via add_section_in_place)
            config: Optional workflow configuration
            regenerate_mode: Required for "partial_autopop" mode. One of "styles", "text", "media", or "all"
        
        Returns:
            Appropriate workflow instance
        """
        if mode == "trade_classification":
            return TradeClassificationWorkflow(config)
        elif mode == "template_selection":
            return TemplateSelectionWorkflow(config)
        elif mode in ("landing_page", "full"):
            return LandingPageWorkflow(config)
        elif mode == "partial_autopop":
            if regenerate_mode is None:
                regenerate_mode = "all"  # Default to "all" if not specified
            return PartialAutopopWorkflow(config=config, regenerate_mode=regenerate_mode)
        elif mode == "preset_sections":
            return PresetSectionsLandingPageWorkflow(config)
        elif mode == "regenerate_section":
            return RegenerateSectionWorkflow(config)
        else:
            raise ValueError(f"Unknown workflow mode: {mode}")
