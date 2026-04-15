# agent_workflows/landing_page_builder/workflows/partial_autopop_workflow.py
"""
Partial Autopop Workflow.

Runs only specific parts of the autopopulation subgraph, restoring final state
from a previous completed autopop run. Useful for regenerating only styles,
text, or images without re-running the entire autopopulation.

Supported modes:
- "styles": Regenerate styles only (colors, semantic names)
- "text": Regenerate text content only
- "media": Regenerate images/media only

Graph Structure (varies by mode):
    START → autopop_start → save_template_sections → autopopulation_input_builder → [selected subgraph(s)] → 
    final_snapshot → autopop_end → [post_processing_subgraph] → END

State Restoration:
    Loads final checkpoint state from a source_thread_id (completed autopop run),
    then starts a fresh workflow with the restored state. Selected subgraph(s)
    will overwrite their respective keys in autopopulation_langgraph_state.
"""

from typing import Dict, Any, Optional, Literal
from langgraph.graph import StateGraph, START, END

from wwai_agent_orchestration.core.observability.logger import set_request_context
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import (
    LandingPageWorkflowState,
    BrandContext,
)

from wwai_agent_orchestration.agent_workflows.landing_page_builder.workflows.base_workflow import BaseLandingPageWorkflow
from wwai_agent_orchestration.agent_workflows.landing_page_builder.subgraphs.post_processing_subgraph import build_post_processing_subgraph

# Import autopopulation nodes
from wwai_agent_orchestration.nodes.landing_page_builder.autopop import (
    autopop_start_node,
    autopopulation_input_builder_node,
    autopop_end_node,
    final_snapshot,
)
from wwai_agent_orchestration.nodes.landing_page_builder.post_processing.save_generation_template_sections import save_generation_template_sections_node

# Import subgraph builders
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.style_nodes import build_style_subgraph
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.content_nodes.text.text_subgraph import build_text_subgraph
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.content_nodes.media.media_subgraph import build_media_subgraph

# Load final state from source checkpoint
from wwai_agent_orchestration.utils.landing_page_builder.checkpoint_load_utils import get_final_checkpoint_state
from wwai_agent_orchestration.utils.landing_page_builder.template_utils import (
    build_minimal_template_for_section_ops,
    get_resolved_and_map_from_db,
)

from wwai_agent_orchestration.core.observability.logger import get_logger
logger = get_logger(__name__)

# Type for regenerate mode
RegenerateMode = Literal["styles", "text", "media", "all"]


class PartialAutopopWorkflow(BaseLandingPageWorkflow):
    """
    Partial autopop workflow that regenerates only specific parts.
    
    Use Case:
        Re-run specific parts of autopopulation (styles, text, or media) on an
        existing completed autopop run, without regenerating everything.
    
    Required:
        - source_thread_id: Thread ID from which to restore final state (must be completed autopop run)
        - request_id: New thread ID for this run (creates new checkpoint chain)
        - regenerate_mode: Which parts to regenerate ("styles", "text", "media", or "all")
    
    Optional Overrides:
        - brand_context: Override palette/font_family from the source state
    """
    
    workflow_name = "partial_autopop"
    
    def __init__(self, config: Dict[str, Any] = None, regenerate_mode: RegenerateMode = "all"):
        """
        Initialize partial autopop workflow.
        
        Args:
            config: Workflow configuration dict
            regenerate_mode: Which parts to regenerate
                - "styles": Only style subgraph (colors, semantic names)
                - "text": Only text content subgraph
                - "media": Only media/images subgraph
                - "all": All subgraphs (style + content)
        """
        self.regenerate_mode = regenerate_mode
        super().__init__(config)
    
    def _build_graph(self) -> StateGraph:
        """
        Build graph with only selected subgraph(s).
        
        Graph Structure (varies by mode):
            START → autopop_start → save_template_sections → autopopulation_input_builder → 
            [selected subgraph(s)] → final_snapshot → autopop_end → 
            [post_processing_subgraph] → END
        """
        graph = StateGraph(LandingPageWorkflowState)
        
        # Always add these nodes
        graph.add_node("autopop_start", autopop_start_node)
        graph.add_node("save_template_sections", save_generation_template_sections_node)
        graph.add_node("autopopulation_input_builder", autopopulation_input_builder_node)
        graph.add_node("final_snapshot", final_snapshot)
        graph.add_node("autopop_end", autopop_end_node)
        
        # Wire entry
        graph.add_edge(START, "autopop_start")
        graph.add_edge("autopop_start", "save_template_sections")
        graph.add_edge("save_template_sections", "autopopulation_input_builder")
        
        # Conditionally build subgraphs based on mode
        if self.regenerate_mode == "styles":
            # Only style subgraph
            build_style_subgraph(
                graph,
                entry_node="autopopulation_input_builder",
                exit_node="final_snapshot"
            )
        elif self.regenerate_mode == "text":
            # Text subgraph ideally needs content planner, but we use the same plan as used in the 
            # previous autopop run
            build_text_subgraph(
                graph,
                entry_node="autopopulation_input_builder",
                exit_node="final_snapshot"
            )
        elif self.regenerate_mode == "media":
            # Media subgraph ideally needs content planner, but we use the same plan as used in the 
            # previous autopop run
            build_media_subgraph(
                graph,
                entry_node="autopopulation_input_builder",
                exit_node="final_snapshot"
            )
        else:
            raise ValueError(f"Unknown regenerate_mode: {self.regenerate_mode}")
        
        # Wire final snapshot to autopop_end
        graph.add_edge("final_snapshot", "autopop_end")
        
        # Build post-processing subgraph
        build_post_processing_subgraph(
            graph,
            entry_node="autopop_end"
        )
        
        logger.info(f"Built PartialAutopopWorkflow graph (mode: {self.regenerate_mode})")
        
        return graph.compile(
            checkpointer=self.checkpointer,
            cache=self.cache
        )
    
    async def stream(
        self,
        request_id: str,
        source_thread_id: str,
        execution_config: Any = None,
        regenerate_mode: Optional[RegenerateMode] = None,
        brand_context: Optional[BrandContext] = None,
    ):
        """
        Execute partial autopop workflow with state restoration.

        Loads final checkpoint state from source_thread_id, applies overrides from brand_context,
        then streams. Only selected subgraph(s) run.
        """
        if not request_id:
            raise ValueError("request_id (generation_version_id) is required")
        if not source_thread_id:
            raise ValueError("source_thread_id is required - specify the thread to restore state from")

        mode = regenerate_mode if regenerate_mode is not None else self.regenerate_mode

        set_request_context(request_id=request_id, workflow=self.workflow_name)

        palette = brand_context.palette if brand_context else None
        font_family = brand_context.font_family if brand_context else None
        logger.info(
            f"Starting {self.workflow_name} workflow with state restoration",
            request_id=request_id,
            source_thread_id=source_thread_id,
            regenerate_mode=mode,
            has_palette_override=palette is not None,
            has_font_override=font_family is not None
        )

        restored_state = get_final_checkpoint_state(
            thread_id=source_thread_id,
            workflow_type="landing_page"
        )

        if not restored_state.get("resolved_template_recommendations"):
            raise ValueError(
                f"Source checkpoint {source_thread_id} doesn't have resolved_template_recommendations. "
                "Make sure the source workflow completed the section retrieval stage."
            )

        if not restored_state.get("autopopulation_langgraph_state"):
            raise ValueError(
                f"Source checkpoint {source_thread_id} doesn't have autopopulation_langgraph_state. "
                "Make sure the source workflow completed autopopulation."
            )

        # Clear so the re-run produces fresh autopop state for selected subgraph(s)
        restored_state["autopopulation_langgraph_state"] = None

        # Read resolved and template_unique_section_id_map from DB (user edits reflected)
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

        async for chunk in self._stream_with_restored_state(
            request_id,
            restored_state,
            palette=palette,
            font_family=font_family,
            execution_config=execution_config,
            config_extra={"workflow_params": {"source_thread_id": source_thread_id}},
        ):
            yield chunk
