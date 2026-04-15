from wwai_agent_orchestration.contracts.landing_page_builder.execution_config import ExecutionConfig
from wwai_agent_orchestration.utils.landing_page_builder.execution_config_utils import create_execution_config
from wwai_agent_orchestration.contracts.landing_page_builder.user_input import (
    GenericContext,
    WebsiteContext,
    BrandContext,
    ExternalDataContext,
)
import json
import uuid
from pathlib import Path
from wwai_agent_orchestration.agent_workflows.landing_page_builder.workflows.landing_page_builder_workflow import LandingPageWorkflow

from wwai_agent_orchestration.core.observability.logger import get_logger
logger = get_logger(__name__)


# ========================================================================
# HELPER FUNCTIONS
# ========================================================================


async def handle_streaming_output(
    workflow,
    business_name: str,
    website_intention: str,
    query: str,
    yelp_url: str,
    business_id: str,
    website_tone: str,
    execution_config: ExecutionConfig,
    request_id: str,
    palette: dict = None,
    font_family: str = None
):
    """Handle streaming output from workflow execution (async)."""
    async for stream_type, chunk in workflow.stream(
        business_name=business_name,
        request_id=request_id,
        business_id=business_id,
        execution_config=execution_config,
        generic_context=GenericContext(query=query),
        website_context=WebsiteContext(
            website_intention=website_intention,
            website_tone=website_tone,
        ),
        brand_context=BrandContext(palette=palette, font_family=font_family),
        external_data_context=ExternalDataContext(yelp_url=yelp_url),
    ):
        if stream_type == "updates":
            # Node completion events
            for node_name, node_data in chunk.items():
                logger.info(
                    f"Node completed: {node_name}",
                    node=node_name,
                    request_id=request_id
                )
        elif stream_type == "messages":
            # LLM token events
            logger.debug(
                f"LLM token: {chunk}",
                request_id=request_id
            )


def get_final_state(workflow, request_id: str):
    """Retrieve and return final state from workflow."""
    config = {
        "configurable": {
            "thread_id": request_id,
            **workflow.config
        }
    }
    return workflow.graph.get_state(config)


def save_state_to_file(state_dict: dict, request_id: str, output_dir: Path):
    """Save final state to JSON file."""
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"state_{request_id}.json"
    
    with open(output_file, "w") as f:
        json.dump(state_dict, f, indent=2, default=str)
    
    logger.info(
        f"Final state written to: {output_file}",
        output_file=str(output_file),
        request_id=request_id
    )
    return output_file


def print_final_state(state_dict: dict):
    """Print final state as formatted JSON."""
    print("\n" + "=" * 80)
    print("FINAL STATE:")
    print("=" * 80)
    print(json.dumps(state_dict, indent=2, default=str))
    print("=" * 80 + "\n")


async def run_workflow(
    business_name: str,
    website_intention: str,
    website_tone: str,
    workflow_config: dict = None,
    request_id: str = None,
    output_dir: Path = None,
    save_to_file: bool = True,
    query: str = None,
    yelp_url: str = None,
    business_id: str = None,
    palette: dict = None,
    font_family: str = None,
    enable_screenshot_compilation: bool = False
) -> dict:
    """
    Run the Landing Page Builder (full/agent) workflow and return final state (async).

    Args:
        business_name: Name of the business
        website_intention: Website intention (e.g., "generate_leads")
        website_tone: Website tone (e.g., "professional")
        workflow_config: Optional workflow configuration
        request_id: Request ID (auto-generated if None)
        output_dir: Directory to save output files
        save_to_file: Whether to save state to file
        query: Query string for agent path
        yelp_url: Yelp URL for business data extraction
        business_id: Business ID
        palette: Color palette for design
        font_family: Font family for design
        enable_screenshot_compilation: If True, captures screenshots from compiled HTML.

    Returns:
        Final state dictionary

    ASYNC: This function is async because workflow.stream() is async.
    Call with: await run_workflow(...) or asyncio.run(run_workflow(...))
    """
    # Generate request_id if not provided
    if request_id is None:
        request_id = str(uuid.uuid4())
    
    # Default output directory
    if output_dir is None:
        output_dir = Path(__file__).parent / "output"
    
    # Create workflow
    workflow = LandingPageWorkflow(config=workflow_config or {})
    
    logger.info(
        "Starting Landing Page Builder workflow",
        business_name=business_name,
        request_id=request_id
    )

    try:
        exec_config = create_execution_config(
            enable_screenshot_compilation=enable_screenshot_compilation
        )
        
        # Execute workflow with streaming (async)
        await handle_streaming_output(
                workflow = workflow,
                business_name = business_name,
                website_intention = website_intention,
                query = query or "",
                yelp_url = yelp_url or "",
                business_id = business_id or "",
                website_tone = website_tone,
                execution_config = exec_config,
                request_id = request_id,
                palette = palette,
                font_family = font_family
            )

        logger.info(
            "✅ Workflow completed successfully",
            request_id=request_id
        )
        
        # Get and process final state
        final_state = get_final_state(workflow, request_id)
        
        if final_state.values:
            state_dict = final_state.values
            
            # Print state
            print_final_state(state_dict)
            
            # Save to file if requested
            if save_to_file:
                save_state_to_file(state_dict, request_id, output_dir)
            
            return state_dict
        else:
            logger.warning("Final state is empty", request_id=request_id)
            return {}
            
    except Exception as e:
        logger.error(
            f"❌ Landing Page Builder workflow failed: {str(e)}",
            error=str(e),
            request_id=request_id
        )
        raise