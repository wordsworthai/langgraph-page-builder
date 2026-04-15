"""
Background Workflow Runner for FastAPI.

This module provides utilities to run workflows in the background without blocking
FastAPI request handlers. This is essential for long-running workflows with parallelism.

Supports multiple workflow types via the factory pattern:
- TradeClassificationWorkflow
- TemplateSelectionWorkflow
- FullWorkflow
- PartialAutopopWorkflow

Optimizations:
- Periodic event loop yields to prevent starvation
- Batched node updates to reduce callback overhead
- Semaphore-based concurrency limiting
- Callback rate limiting to prevent task explosion
- Automatic task cleanup and tracking

Usage:
    from wwai_agent_orchestration.core.workflow_background_runner import run_workflow_in_background
    from wwai_agent_orchestration.contracts.landing_page_builder.workflow_inputs import (
        LandingPageInput,
        PartialAutopopInput,
        build_stream_kwargs,
        get_workflow_type,
        get_request_id,
        get_workflow_name,
    )
    from wwai_agent_orchestration.contracts.landing_page_builder.user_input import (
        GenericContext,
        WebsiteContext,
        BrandContext,
        ExternalDataContext,
    )

    # For full workflow (nested context):
    task = await run_workflow_in_background(
        workflow=workflow,
        workflow_input=LandingPageInput(
            business_name="Test Business",
            business_id="...",
            request_id=request_id,
            execution_config=exec_config,
            generic_context=GenericContext(query="...", sector="...", page_url="..."),
            website_context=WebsiteContext(website_intention="generate_leads", website_tone="professional"),
            brand_context=BrandContext(palette=..., font_family="..."),
            external_data_context=ExternalDataContext(yelp_url="..."),
        ),
        on_node_update=handle_node_update,
        on_complete=handle_complete,
        on_error=handle_error
    )
    
    # For partial workflow (brand_context for palette/font overrides):
    task = await run_workflow_in_background(
        workflow=partial_workflow,
        workflow_input=PartialAutopopInput(
            request_id=request_id,
            source_thread_id=base_request_id,
            execution_config=exec_config,
            regenerate_mode="styles",
            brand_context=BrandContext(palette=..., font_family="..."),
        ),
        on_node_update=handle_node_update,
        on_complete=handle_complete,
        on_error=handle_error
    )
    
    # Return immediately
    return {"status": "running", "request_id": request_id}
"""

import asyncio
import time
from typing import Dict, Any, Callable, Optional, Awaitable, List, Tuple

from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_inputs import (
    LandingPageWorkflowInput,
    build_stream_kwargs,
    get_workflow_type,
    get_request_id,
    get_workflow_name,
)

logger = get_logger(__name__)

# Global semaphore to limit concurrent workflows (prevents event loop overload)
# Default: 20 concurrent workflows (adjust based on your server capacity)
WORKFLOW_SEMAPHORE = asyncio.Semaphore(20)

# Track active tasks for monitoring and cleanup
_active_tasks: Dict[str, asyncio.Task] = {}


async def run_workflow_in_background(
    workflow,
    workflow_input: LandingPageWorkflowInput,
    on_node_update: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None,
    on_complete: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
    on_error: Optional[Callable[[Exception], Awaitable[None]]] = None,
    batch_size: int = 2,
    yield_interval: int = 5,
    timeout_seconds: Optional[int] = None,
    simulate_fail_at_event: Optional[int] = None,
) -> asyncio.Task:
    """
    Run workflow in background task without blocking FastAPI.
    
    This function:
    1. Creates an asyncio task to run the workflow (with semaphore limiting)
    2. Processes streaming events asynchronously with periodic yields
    3. Batches node updates to reduce callback overhead
    4. Calls callbacks for node updates, completion, and errors
    5. Returns immediately so FastAPI can handle other requests
        
    Args:
        workflow: Workflow instance (e.g., LandingPageWorkflow, PartialAutopopWorkflow, etc.)
        workflow_input: Workflow input parameters (one of: TradeClassificationInput, TemplateSelectionInput, 
                       LandingPageInput, or PartialAutopopInput)
        on_node_update: Async callback(node_name, node_data) called on each node completion.
            node_data is the node's return dict. Consumer must extract from node_data["ui_execution_log"]
            only when building progress UI payloads. See docs/design/UI_LOGS_CONSUMER_CONTRACT.md.
        on_complete: Async callback(final_state) called when workflow completes
        on_error: Async callback(exception) called on errors
        batch_size: Number of node updates to batch before processing (default: 2)
        yield_interval: Number of events before yielding to event loop (default: 5)
        timeout_seconds: Optional timeout for workflow execution (None = no timeout)
        simulate_fail_at_event: If set, raise a test error after N stream events (for retry testing)
        
    Returns:
        asyncio.Task that can be tracked/cancelled if needed
        
    Example:
        # Full workflow
        task = await run_workflow_in_background(
            workflow=workflow,
            workflow_input=LandingPageInput(
                business_name="Test Business",
                request_id=request_id,
                # ... other params
            ),
            on_node_update=lambda node, data: logger.info(f"Node {node} completed"),
            on_complete=lambda state: logger.info("Workflow completed"),
            on_error=lambda e: logger.error(f"Error: {e}")
        )
        
        # Partial autopop workflow
        task = await run_workflow_in_background(
            workflow=partial_workflow,
            workflow_input=PartialAutopopInput(
                request_id=request_id,
                source_thread_id=base_request_id,
                execution_config=exec_config,
                mongo_uri=mongo_uri,
                db_name=db_name,
                regenerate_mode="styles"
            ),
            on_node_update=lambda node, data: logger.info(f"Node {node} completed"),
            on_complete=lambda state: logger.info("Workflow completed"),
            on_error=lambda e: logger.error(f"Error: {e}")
        )
    """
    
    # Determine workflow type and extract request_id
    workflow_type = get_workflow_type(workflow_input)
    request_id = get_request_id(workflow_input)
    workflow_name = get_workflow_name(workflow_input)
    
    async def _run_workflow():
        """Internal function that actually runs the workflow."""
        start_time = time.time()
        final_state = None
        update_batch: List[Tuple[str, Dict[str, Any]]] = []
        event_count = 0
        node_count = 0
        last_heartbeat_sec = [0.0]
        
        async def _flush_update_batch():
            """Flush batched node updates."""
            nonlocal update_batch
            if not update_batch or not on_node_update:
                return
            
            # Process batch in background task
            batch_copy = update_batch.copy()
            update_batch.clear()
            
            async def _process_batch():
                for node_name, node_data in batch_copy:
                    try:
                        await on_node_update(node_name, node_data)
                    except Exception as callback_error:
                        logger.error(
                            f"Error in on_node_update callback: {callback_error}",
                            exc_info=True,
                            request_id=request_id
                        )
            
            # Fire and forget - don't await to prevent blocking
            asyncio.create_task(_process_batch())
        
        try:
            logger.info(
                f"Starting background workflow execution",
                request_id=request_id,
                workflow_type=workflow_type,
                workflow_name=workflow_name
            )
            
            # Use semaphore to limit concurrent workflows
            async with WORKFLOW_SEMAPHORE:
                # Build stream kwargs from workflow input
                stream_kw = build_stream_kwargs(workflow_input)
                stream_iter = workflow.stream(**stream_kw)
                
                # Process stream with timeout check
                async for stream_type, chunk in stream_iter:
                    elapsed = time.time() - start_time
                    # Check timeout periodically
                    if timeout_seconds:
                        if elapsed > timeout_seconds:
                            raise asyncio.TimeoutError(
                                f"Workflow exceeded timeout of {timeout_seconds}s (elapsed: {elapsed:.2f}s)"
                            )
                    # Heartbeat: log every 30s to detect event-loop blocking
                    if elapsed - last_heartbeat_sec[0] >= 30:
                        logger.info(
                            "Workflow heartbeat",
                            request_id=request_id,
                            elapsed_seconds=round(elapsed),
                            event_count=event_count,
                            node_count=node_count,
                        )
                        last_heartbeat_sec[0] = elapsed
                    
                    event_count += 1

                    # Simulate failure for retry testing (when simulate_fail_at_event query param is set)
                    if simulate_fail_at_event is not None and event_count >= simulate_fail_at_event:
                        raise AssertionError(
                            f"TEST: simulated workflow failure for retry testing after {simulate_fail_at_event} events"
                        )

                    # CRITICAL: Yield control back to event loop periodically
                    # This prevents blocking when processing many parallel events
                    if event_count % yield_interval == 0:
                        await asyncio.sleep(0)  # Yield to event loop
                        
                        # Also flush batch when yielding
                        await _flush_update_batch()
                    
                    if stream_type == "updates":
                        # Node completion events
                        for node_name, node_data in chunk.items():
                            node_count += 1
                            elapsed = time.time() - start_time
                            logger.info(
                                "Node completed",
                                request_id=request_id,
                                node=node_name,
                                node_count=node_count,
                                elapsed_seconds=round(elapsed, 2),
                            )
                            logger.debug(
                                f"Node completed: {node_name}",
                                node=node_name,
                                request_id=request_id,
                                node_count=node_count
                            )
                            
                            # Batch node updates instead of processing individually
                            if on_node_update:
                                update_batch.append((node_name, node_data))
                                
                                # Flush batch when it reaches batch_size
                                if len(update_batch) >= batch_size:
                                    await _flush_update_batch()
                    
                    elif stream_type == "messages":
                        # LLM token events - skip processing to reduce overhead
                        pass
                
                # Flush any remaining batched updates
                await _flush_update_batch()
            
            # Workflow completed successfully
            duration = time.time() - start_time
            logger.info(
                f"Background workflow completed successfully",
                request_id=request_id,
                has_final_state=final_state is not None,
                duration_seconds=duration,
                total_events=event_count,
                total_nodes=node_count
            )
            
            # Call completion callback if provided
            if on_complete:
                try:
                    await on_complete(final_state)
                except Exception as callback_error:
                    logger.error(
                        f"Error in on_complete callback: {callback_error}",
                        exc_info=True,
                        request_id=request_id
                    )
        
        except asyncio.CancelledError:
            logger.warning(
                f"Background workflow cancelled",
                request_id=request_id
            )
            # Don't call error callback for cancellation
            raise
        
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Background workflow failed",
                exc_info=True,
                request_id=request_id,
                error=str(e),
                duration_seconds=duration,
                total_events=event_count,
                total_nodes=node_count
            )
            
            # Call error callback if provided
            if on_error:
                try:
                    await on_error(e)
                except Exception as callback_error:
                    logger.error(
                        f"Error in on_error callback: {callback_error}",
                        exc_info=True,
                        request_id=request_id
                    )
            else:
                # Re-raise if no error handler
                raise
        finally:
            # Cleanup: remove task from tracking
            _active_tasks.pop(request_id, None)
    
    # Create and return background task
    task = asyncio.create_task(_run_workflow())
    
    # Track active task for monitoring
    _active_tasks[request_id] = task
    
    # Auto-cleanup when task completes
    def _cleanup_on_done(t):
        _active_tasks.pop(request_id, None)
    
    task.add_done_callback(_cleanup_on_done)
    
    logger.info(
        f"Created background task for workflow execution",
        request_id=request_id,
        task_name=task.get_name(),
        active_workflows=len(_active_tasks)
    )
    
    return task