# agent_workflows/landing_page_builder/workflows/base_workflow.py
"""
Base Landing Page Builder Workflow Class.

Provides shared infrastructure for all Landing Page Builder workflow variants:
- MongoDB checkpointing for state persistence
- Redis caching for node results
- Async streaming support
- Resume from checkpoint capability
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncIterator
from langgraph.graph import StateGraph
from langgraph.checkpoint.mongodb import MongoDBSaver

from wwai_agent_orchestration.core.database.redis.langgraph_redis_cache import smb_workflow_cache
from wwai_agent_orchestration.core.database import db_manager

from wwai_agent_orchestration.core.observability.logger import set_request_context
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import (
    LandingPageWorkflowState,
    UserInput,
    GenericContext,
    WebsiteContext,
    BrandContext,
    ExternalDataContext,
)
from wwai_agent_orchestration.contracts.landing_page_builder.execution_config import ExecutionConfig

from wwai_agent_orchestration.core.observability.logger import get_logger
logger = get_logger(__name__)


class BaseLandingPageWorkflow(ABC):
    """
    Base class with shared checkpointer, cache, and streaming logic.
    
    All Landing Page Builder workflows inherit from this to get:
    - MongoDB checkpointer for state persistence
    - Redis cache for node result caching
    - Async streaming with resume capability
    """
    
    # Workflow name for logging (override in subclasses)
    workflow_name: str = "base_landing_page_builder"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        if config is None:
            self.config = {}
        elif hasattr(config, "to_configurable_dict") and callable(getattr(config, "to_configurable_dict")):
            self.config = config.to_configurable_dict()
        else:
            self.config = dict(config) if config else {}
        # Use MongoDB checkpointer for persistent state storage
        # This enables short-term memory, human-in-the-loop, time travel, and fault-tolerance
        self.checkpointer = MongoDBSaver(db_manager.sync_client)
        self.cache = smb_workflow_cache
        self.graph = self._build_graph()

    @abstractmethod
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow. Override in subclasses."""
        raise NotImplementedError
    
    async def stream(
        self,
        business_name: str,
        request_id: str,
        business_id: Optional[str] = None,
        execution_config: Any = None,
        generic_context: Optional[GenericContext] = None,
        website_context: Optional[WebsiteContext] = None,
        brand_context: Optional[BrandContext] = None,
        external_data_context: Optional[ExternalDataContext] = None,
    ):
        """
        Execute workflow with streaming (async).
        
        Yields tuples of (stream_type, chunk) where:
        - stream_type == "updates": Node completion events
        - stream_type == "messages": LLM token events

        request_id: MUST be generation_version_id from backend (not optional)
        
        ASYNC: Uses graph.astream() to support async nodes.
        """
        if not request_id:
            raise ValueError("request_id (generation_version_id) is required")
        
        set_request_context(
            request_id=request_id,
            workflow=self.workflow_name
        )
        
        _wc = website_context or WebsiteContext()
        _ed = external_data_context or ExternalDataContext()
        has_google = bool(getattr(_ed, "google_places_data", None))
        has_yelp = bool(getattr(_ed, "yelp_url", None))
        logger.info(
            f"Starting streaming {self.workflow_name} workflow",
            business_name=business_name,
            website_intention=getattr(_wc, "website_intention", None),
            website_tone=getattr(_wc, "website_tone", None),
            has_google_data=has_google,
            has_yelp_url=has_yelp,
            request_id=request_id
        )
        
        user_input = UserInput(
            business_name=business_name,
            business_id=business_id,
            generation_version_id=request_id,
            generic_context=generic_context or GenericContext(),
            website_context=website_context or WebsiteContext(),
            brand_context=brand_context or BrandContext(),
            external_data_context=external_data_context or ExternalDataContext(),
        )

        initial_state_kw: Dict[str, Any] = dict(
            input=user_input,
            execution_config=execution_config,
        )
        initial_state = LandingPageWorkflowState(**initial_state_kw)
        
        # Execute with streaming
        config = {
            "configurable": {
                "thread_id": request_id,
                "workflow_name": self.workflow_name,
                **{k: v for k, v in self.config.items()}
            }
        }
        logger.info(
            f"🔍 DEBUG: Config being passed to graph.astream - "
            f"rapidapi_key={'[SET - length=' + str(len(self.config.get('rapidapi_key', ''))) + ']' if self.config.get('rapidapi_key') else '[EMPTY]'}, "
            f"config_keys={list(self.config.keys())[:5]}..."
        )
        
        # Check if checkpoint exists for this thread_id to enable resume
        existing_state = self.graph.get_state(config)
        if existing_state and existing_state.values:
            # Checkpoint exists - resume from last checkpoint by passing None
            logger.info(
                f"🔄 RESUMING from existing checkpoint for thread_id={request_id}",
                checkpoint_id=existing_state.config.get("configurable", {}).get("checkpoint_id", "unknown")[:16] + "...",
                last_node=existing_state.next[0] if existing_state.next else "completed",
                request_id=request_id
            )
            stream_input = None  # None = resume from checkpoint
        else:
            # No checkpoint - start fresh
            logger.info(
                f"🆕 Starting NEW workflow (no checkpoint found) for thread_id={request_id}",
                request_id=request_id
            )
            stream_input = initial_state.model_dump()
        
        # Stream both node updates AND LLM tokens (async API for async nodes)
        async for chunk in self.graph.astream(
            stream_input,
            config=config,
            stream_mode=["updates", "messages"]
        ):
            yield chunk

    async def _stream_with_restored_state(
        self,
        request_id: str,
        restored_state: Dict[str, Any],
        *,
        palette: Optional[Dict[str, Any]] = None,
        font_family: Optional[str] = None,
        execution_config: Any = None,
        config_extra: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Any]:
        """
        Common logic for workflows that restore state from a checkpoint then stream.

        Builds initial state from restored_state + overrides, then runs graph.astream.
        Pass enable_reflection and max_iterations via execution_config if needed.
        """
        initial_state = LandingPageWorkflowState.from_restored_state(
            restored_state,
            generation_version_id=request_id,
            palette=palette,
            font_family=font_family,
            execution_config=execution_config,
        )
        if palette is not None:
            logger.info(
                "Palette override applied",
                original_palette_id=restored_state.get("palette", {}).get("palette_id") if restored_state.get("palette") else None,
                new_palette_id=palette.get("palette_id") if palette else None
            )
        if font_family is not None:
            logger.info(
                "Font family override applied",
                original_font=restored_state.get("font_family"),
                new_font=font_family
            )
        config = {
            "configurable": {
                "thread_id": request_id,
                "workflow_name": self.workflow_name,
                **(config_extra or {}),
                **{k: v for k, v in self.config.items()}
            }
        }
        async for chunk in self.graph.astream(
            initial_state.model_dump(),
            config=config,
            stream_mode=["updates", "messages"]
        ):
            yield chunk
