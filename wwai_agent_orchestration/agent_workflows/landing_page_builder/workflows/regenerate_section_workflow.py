"""
Regenerate Section Workflow.

Regenerates content for a section at index. Section structure must already be
in place (from add_section_in_place with lorem). Runs autopopulation for the
section, merges with source's existing snapshots, and runs post-processing.

Graph Structure:
    START → save_template_sections → autopopulation_input_builder
          → [full autopop subgraph: styles + text + media]
          → final_snapshot → autopop_end → [post-processing] → END

State Restoration:
    Loads final checkpoint state from source_thread_id (completed generation),
    reads resolved and template_unique_section_id_map from DB in stream(),
    injects into state, then starts graph at save_template_sections.
"""

from typing import Any
from langgraph.graph import StateGraph, START, END

from wwai_agent_orchestration.core.observability.logger import set_request_context
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState

from wwai_agent_orchestration.agent_workflows.landing_page_builder.workflows.base_workflow import BaseLandingPageWorkflow
from wwai_agent_orchestration.agent_workflows.landing_page_builder.subgraphs.post_processing_subgraph.post_processing_subgraph import build_post_processing_subgraph

from wwai_agent_orchestration.nodes.landing_page_builder.post_processing.save_generation_template_sections import save_generation_template_sections_node
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.autopopulation_input_builder import autopopulation_input_builder_node

from wwai_agent_orchestration.nodes.landing_page_builder.autopop import (
    autopop_end_node,
    final_snapshot,
)

from wwai_agent_orchestration.nodes.landing_page_builder.autopop.style_nodes import build_style_subgraph
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.content_nodes import build_content_subgraph

from wwai_agent_orchestration.utils.landing_page_builder.checkpoint_load_utils import get_final_checkpoint_state
from wwai_agent_orchestration.utils.landing_page_builder.template_utils import (
    build_minimal_template_for_section_ops,
    get_resolved_and_map_from_db,
)

from wwai_agent_orchestration.core.observability.logger import get_logger
logger = get_logger(__name__)


class RegenerateSectionWorkflow(BaseLandingPageWorkflow):
    """
    Workflow that regenerates content for a section at index.

    Section structure must already be in place (from add_section_in_place).
    Always uses replace mode internally.

    Required stream() kwargs:
        - request_id: New thread ID for this run
        - source_thread_id: Thread ID of the existing generation (modified by add_section_in_place)
        - section_id: Repo ObjectId of the section at that index
        - section_index: 0-based index of section to regenerate (used as replace_index)
    """

    workflow_name = "regenerate_section"

    def _build_graph(self) -> StateGraph:
        """
        Build the regenerate-section graph.

        START → save_template_sections
              → autopopulation_input_builder
              → [styles + content subgraphs in parallel]
              → final_snapshot → autopop_end
              → [post-processing] → END
        """
        graph = StateGraph(LandingPageWorkflowState)

        graph.add_node("save_template_sections", save_generation_template_sections_node)
        graph.add_node("autopopulation_input_builder", autopopulation_input_builder_node)

        # Autopop subgraph nodes
        build_style_subgraph(
            graph,
            entry_node="autopopulation_input_builder",
            exit_node="final_snapshot",
            add_exit_edge=False,
        )
        build_content_subgraph(
            graph,
            entry_node="autopopulation_input_builder",
            exit_node="final_snapshot",
            add_exit_edge=False,
        )

        graph.add_node("final_snapshot", final_snapshot)
        graph.add_node("autopop_end", autopop_end_node)

        # ---- Wiring ----
        graph.add_edge(START, "save_template_sections")
        graph.add_edge("save_template_sections", "autopopulation_input_builder")

        # AND-join: final_snapshot waits for all three pipelines
        graph.add_edge(
            ["semantic_names_snapshot", "content_text_snapshot", "content_media_snapshot"],
            "final_snapshot",
        )

        graph.add_edge("final_snapshot", "autopop_end")

        # Post-processing subgraph wired from autopop_end → END
        build_post_processing_subgraph(graph, entry_node="autopop_end")

        logger.info("Built RegenerateSectionWorkflow graph")

        return graph.compile(
            checkpointer=self.checkpointer,
            cache=self.cache,
        )

    async def stream(
        self,
        request_id: str,
        source_thread_id: str,
        section_id: str,
        section_index: int,
        execution_config: Any = None,
    ):
        """
        Execute the regenerate-section workflow.

        Restores state from source_thread_id, passes section_id and section_index
        through config.configurable. Always uses replace mode internally.
        """
        if not request_id:
            raise ValueError("request_id (generation_version_id) is required")
        if not source_thread_id:
            raise ValueError("source_thread_id is required")
        if not section_id:
            raise ValueError("section_id is required")
        if section_index is None or section_index < 0:
            raise ValueError("section_index must be >= 0")

        set_request_context(request_id=request_id, workflow=self.workflow_name)

        logger.info(
            "Starting regenerate_section workflow",
            request_id=request_id,
            source_thread_id=source_thread_id,
            section_id=section_id,
            section_index=section_index,
        )

        restored_state = get_final_checkpoint_state(
            thread_id=source_thread_id,
            workflow_type="landing_page",
        )

        if not restored_state.get("resolved_template_recommendations"):
            raise ValueError(
                f"Source checkpoint {source_thread_id} doesn't have "
                "resolved_template_recommendations."
            )
        if not restored_state.get("autopopulation_langgraph_state"):
            raise ValueError(
                f"Source checkpoint {source_thread_id} doesn't have "
                "autopopulation_langgraph_state."
            )

        # Clear so the deep_merge_reducer starts fresh for the new section only
        restored_state["autopopulation_langgraph_state"] = None

        # Read resolved and template_unique_section_id_map from DB (section already in place)
        resolved = restored_state.get("resolved_template_recommendations", [])
        minimal_template = build_minimal_template_for_section_ops(resolved)
        updated_resolved, template_unique_section_id_map = get_resolved_and_map_from_db(
            source_thread_id, minimal_template
        )
        restored_state["resolved_template_recommendations"] = updated_resolved
        restored_state["template_unique_section_id_map"] = template_unique_section_id_map

        logger.info(
            "Restored state from source checkpoint, read resolved from DB",
            source_thread_id=source_thread_id,
            num_templates=len(resolved),
        )

        config_extra = {
            "workflow_params": {
                "source_thread_id": source_thread_id,
                "section_id": section_id,
                "section_index": section_index,
            }
        }

        async for chunk in self._stream_with_restored_state(
            request_id,
            restored_state,
            execution_config=execution_config,
            config_extra=config_extra,
        ):
            yield chunk
