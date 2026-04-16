#!/usr/bin/env python3
"""
Landing Page Demo Script

This script demonstrates the complete Landing Page Builder recommendation workflow:
1. Business data extraction
2. Template generation
3. Section retrieval
4. Autopopulation
5. HTML compilation

Usage:
    poetry run python pipeline/landing_page_demos/landing_page_demo.py \\
        --business_id=660097b0-03df-42b5-b68e-5ccf18193b26 \\
        --business_name="Bailey Plumbing"

    # Or run with fallback defaults (no real business data):
    poetry run python pipeline/landing_page_demos/landing_page_demo.py
"""

import uuid
import asyncio

from absl import app

from pipeline import env_utils
from pipeline.user_website_input_choices import get_color_palette_and_font
from pipeline.landing_page_demos.utils import (
    setup_environment,
    setup_workflow_config,
    get_default_business_config,
    create_default_execution_config,
    print_workflow_header,
    print_workflow_results,
    run_workflow_stream,
)
from wwai_agent_orchestration.agent_workflows.landing_page_builder.workflows.workflow_factory import LandingPageWorkflowFactory
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_inputs import (
    LandingPageInput,
    build_stream_kwargs,
)
from wwai_agent_orchestration.contracts.landing_page_builder.user_input import (
    GenericContext,
    WebsiteContext,
    BrandContext,
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
    print("LANDING PAGE DEMO")
    print("=" * 60)
    print(f"\n📋 Request ID: {request_id}")
    
    # Get color palette and font
    palette_data = get_color_palette_and_font(index=0)
    palette = palette_data["PALETTE"]
    font_family = palette_data["FONT_FAMILY"]
    
    print(f"\n🎨 Palette: {palette['palette_id']} ({palette['category']})")
    print(f"🔤 Font: {font_family}")
    
    # Create workflow using factory
    workflow = LandingPageWorkflowFactory.create("landing_page", config=workflow_config)
    
    print_workflow_header(
        "RUNNING LANDING PAGE WORKFLOW",
        request_id=request_id,
        Business=business_config["business_name"],
        Workflow=workflow.workflow_name
    )
    
    # Create execution config
    exec_config = create_default_execution_config(
        use_mock_autopopulation=False
    )
    
    # Create workflow input (nested context, same shape as UserInput)
    workflow_input = LandingPageInput(
        business_name=business_config["business_name"],
        business_id=business_config["business_id"],
        execution_config=exec_config,
        request_id=request_id,
        generic_context=GenericContext(query="", sector=None, page_url=None),
        website_context=WebsiteContext(
            website_intention=business_config["website_intention"],
            website_tone=business_config["website_tone"],
        ),
        brand_context=BrandContext(palette=palette, font_family=font_family),
        external_data_context=ExternalDataContext(yelp_url=""),
    )
    
    # Build stream kwargs
    stream_kwargs = build_stream_kwargs(workflow_input)
    
    # Run workflow
    await run_workflow_stream(workflow, stream_kwargs)
    
    # Display results
    print_workflow_header("VIEWING WORKFLOW RESULTS", request_id=request_id)
    html_url = print_workflow_results(workflow, request_id, workflow_config)
    
    # Template compilation now runs automatically in the workflow (template_compilation node)
    # No need to call it manually here
    
    print("\n" + "=" * 60)
    print("✅ DEMO COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    if html_url:
        print(f"\n🌐 HTML URL: {html_url}")


def main(argv):
    """Entry point for absl."""
    asyncio.run(main_async())


if __name__ == "__main__":
    app.run(main)
