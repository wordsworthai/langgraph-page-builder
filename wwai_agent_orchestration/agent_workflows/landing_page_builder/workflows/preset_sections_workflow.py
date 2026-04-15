"""
Preset Sections Workflow.

Bypasses template selection entirely. Takes section IDs as direct input,
fetches sections from the repo, and runs autopopulation + post-processing.

Graph Structure:
    START → fetch_sections_by_id → save_template_sections → autopop_start →
    [autopop_subgraph] → autopop_end → [post_processing_subgraph] → END

No checkpoint restoration - builds fresh state from inputs.
"""

from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, START, END

from wwai_agent_orchestration.core.observability.logger import set_request_context
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.contracts.landing_page_builder.execution_config import ExecutionConfig
from wwai_agent_orchestration.contracts.landing_page_builder.user_input import (
    UserInput,
    GenericContext,
    WebsiteContext,
    BrandContext,
    ExternalDataContext,
)

from wwai_agent_orchestration.agent_workflows.landing_page_builder.workflows.base_workflow import BaseLandingPageWorkflow
from wwai_agent_orchestration.agent_workflows.landing_page_builder.subgraphs.autopop_subgraph import build_autopop_subgraph
from wwai_agent_orchestration.agent_workflows.landing_page_builder.subgraphs.post_processing_subgraph import build_post_processing_subgraph
from wwai_agent_orchestration.nodes.landing_page_builder.routing.fetch_sections_by_id import fetch_sections_by_id_node
from wwai_agent_orchestration.nodes.landing_page_builder.post_processing.save_generation_template_sections import save_generation_template_sections_node

from wwai_agent_orchestration.core.observability.logger import get_logger

logger = get_logger(__name__)


class PresetSectionsLandingPageWorkflow(BaseLandingPageWorkflow):
    """
    Workflow that takes section IDs directly and bypasses template selection.

    Use Case:
        When section IDs are already known (e.g. from a form, preset, or
        previous selection), skip template generation and run autopopulation.

    Required:
        - section_ids: List of MongoDB ObjectId strings for sections
        - business_name: Business name for autopopulation
        - request_id: Generation version ID (thread_id for checkpoints)

    No checkpoint restoration - always starts fresh.
    """

    workflow_name = "preset_sections"

    def _build_graph(self) -> StateGraph:
        """
        Build graph: fetch sections by ID → save → autopop → post-process.

        Graph Structure:
            START → fetch_sections_by_id → save_template_sections → autopop_start →
            [autopop_subgraph] → autopop_end → [post_processing_subgraph] → END
        """
        graph = StateGraph(LandingPageWorkflowState)

        graph.add_node("fetch_sections_by_id", fetch_sections_by_id_node)
        graph.add_node("save_template_sections", save_generation_template_sections_node)

        build_autopop_subgraph(graph)
        build_post_processing_subgraph(
            graph,
            entry_node="autopop_end"
        )

        graph.add_edge(START, "fetch_sections_by_id")
        graph.add_edge("fetch_sections_by_id", "save_template_sections")
        graph.add_edge("save_template_sections", "autopop_start")

        logger.info("Built PresetSectionsLandingPageWorkflow graph")

        return graph.compile(
            checkpointer=self.checkpointer,
            cache=self.cache
        )

    async def stream(
        self,
        business_name: str,
        request_id: str,
        section_ids: List[str],
        business_id: Optional[str] = None,
        execution_config: Any = None,
        generic_context: Optional[GenericContext] = None,
        website_context: Optional[WebsiteContext] = None,
        brand_context: Optional[BrandContext] = None,
        external_data_context: Optional[ExternalDataContext] = None,
        page_type: str = "homepage",
        parent_generation_version_id: Optional[str] = None,
    ):
        """
        Execute preset sections workflow with streaming.

        Builds fresh state from inputs. No checkpoint restoration.
        """
        if not request_id:
            raise ValueError("request_id (generation_version_id) is required")
        if not section_ids:
            raise ValueError("section_ids is required (non-empty list)")

        set_request_context(request_id=request_id, workflow=self.workflow_name)

        base_config = {}
        if execution_config is not None:
            if hasattr(execution_config, "model_dump"):
                base_config = execution_config.model_dump()
            elif isinstance(execution_config, dict):
                base_config = dict(execution_config)
        routing = base_config.get("routing") or {}
        if isinstance(routing, dict):
            routing = {**routing, "section_ids": section_ids}
        else:
            routing = {"section_ids": section_ids}
        exec_config_dict = {**base_config, "routing": routing}

        logger.info(
            f"Starting {self.workflow_name} workflow",
            business_name=business_name,
            section_count=len(section_ids),
            request_id=request_id,
        )

        user_input = UserInput(
            business_name=business_name,
            business_id=business_id,
            generation_version_id=request_id,
            page_type=page_type,
            generic_context=generic_context or GenericContext(),
            website_context=website_context or WebsiteContext(),
            brand_context=brand_context or BrandContext(),
            external_data_context=external_data_context or ExternalDataContext(),
        )

        exec_config_obj = ExecutionConfig(**exec_config_dict)
        initial_state = LandingPageWorkflowState(
            input=user_input,
            execution_config=exec_config_obj,
        )

        # We pass parent_generation_version_id, this is passed to the compilation node 
        # to get the header and footer of parent page, in case page type is non homepage.
        config = {
            "configurable": {
                "thread_id": request_id,
                "parent_generation_version_id": parent_generation_version_id,
                "workflow_name": self.workflow_name,
                **{k: v for k, v in self.config.items()}
            }
        }

        logger.info(
            f"Starting NEW {self.workflow_name} workflow (no checkpoint)",
            request_id=request_id
        )

        async for chunk in self.graph.astream(
            initial_state.model_dump(),
            config=config,
            stream_mode=["updates", "messages"]
        ):
            yield chunk
