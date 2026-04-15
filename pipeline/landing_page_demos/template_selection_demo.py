#!/usr/bin/env python3
"""
Template Selection Demo Script

This script demonstrates the template selection workflow:
1. Business data extraction
2. Template generation
3. Section retrieval
(Stops before autopopulation)

Usage:
    poetry run python pipeline/landing_page_demos/template_selection_demo.py \\
        --business_id=660097b0-03df-42b5-b68e-5ccf18193b26 \\
        --business_name="Bailey Plumbing"
"""

import uuid
import asyncio

from absl import app

from pipeline import env_utils
from pipeline.landing_page_demos.utils import (
    setup_environment,
    setup_workflow_config,
    get_default_business_config,
    create_default_execution_config,
    print_workflow_header,
    print_workflow_results,
    run_workflow_stream,
    get_workflow_state,
)
from wwai_agent_orchestration.agent_workflows.landing_page_builder.workflows.workflow_factory import LandingPageWorkflowFactory
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_inputs import (
    TemplateSelectionInput,
    build_stream_kwargs,
)
from wwai_agent_orchestration.contracts.landing_page_builder.user_input import (
    GenericContext,
    WebsiteContext,
    ExternalDataContext,
)


async def main_async():
    """Main async function to run the demo."""
    # Setup environment
    setup_environment()
    env_utils.check_env_vars()
    
    # Setup configuration
    workflow_config = setup_workflow_config()
    business_config = get_default_business_config()
    
    # Generate unique request ID
    request_id = str(uuid.uuid4())
    
    print("=" * 60)
    print("TEMPLATE SELECTION DEMO")
    print("=" * 60)
    print(f"\n📋 Request ID: {request_id}")
    
    # Create workflow using factory
    workflow = LandingPageWorkflowFactory.create("template_selection", config=workflow_config)
    
    print_workflow_header(
        "RUNNING TEMPLATE SELECTION WORKFLOW",
        request_id=request_id,
        Business=business_config["business_name"],
        Workflow=workflow.workflow_name
    )
    
    # Create execution config
    exec_config = create_default_execution_config()
    
    # Create workflow input (nested context, same shape as UserInput)
    workflow_input = TemplateSelectionInput(
        business_name=business_config["business_name"],
        business_id=business_config["business_id"],
        execution_config=exec_config,
        request_id=request_id,
        generic_context=GenericContext(query="", sector=None, page_url=None),
        website_context=WebsiteContext(
            website_intention=business_config["website_intention"],
            website_tone=business_config["website_tone"],
        ),
        external_data_context=ExternalDataContext(yelp_url=""),
    )
    
    # Build stream kwargs
    stream_kwargs = build_stream_kwargs(workflow_input)
    
    # Run workflow
    await run_workflow_stream(workflow, stream_kwargs)
    
    # Display results (includes HTML compilation S3 URL when available)
    print_workflow_header("VIEWING TEMPLATE SELECTION RESULTS", request_id=request_id)
    html_url = print_workflow_results(workflow, request_id, workflow_config)

    print("\n" + "=" * 60)
    print("✅ DEMO COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    if html_url:
        print(f"\n🌐 HTML URL: {html_url}")
    print("\n💡 Note: This workflow uses ipsum_lorem placeholder content (no autopopulation).")
    print("   Use 'full' workflow for complete end-to-end flow with real content.")


def main(argv):
    """Entry point for absl."""
    asyncio.run(main_async())


if __name__ == "__main__":
    app.run(main)
