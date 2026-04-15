#!/usr/bin/env python3
"""
Preset Sections Workflow Demo Script

This script demonstrates the PresetSectionsLandingPageWorkflow:
1. Takes a list of section IDs directly (preset_section_ids)
2. Fetches sections from the repo
3. Runs autopopulation and post-processing
4. Outputs HTML URL for validation

Usage:
    poetry run python pipeline/landing_page_demos/preset_sections_demo.py \\
        --business_id=660097b0-03df-42b5-b68e-5ccf18193b26 \\
        --business_name="Bailey Plumbing"

Populate preset_section_ids below with valid MongoDB ObjectIds from section_repo_prod.section_metadata.
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
    PresetSectionsInput,
    build_stream_kwargs,
)
from wwai_agent_orchestration.contracts.landing_page_builder.user_input import (
    GenericContext,
    WebsiteContext,
    BrandContext,
    ExternalDataContext,
)

# Populate with valid section IDs from section_repo_prod.section_metadata (MongoDB ObjectId strings)
# "69666d3ddb7c2f2d24b582a2",
# "69666ae6db7c2f2d24b5814e",
# "69666d78db7c2f2d24b582c2"

# "69666d3ddb7c2f2d24b582a2", ==> header.
# "69666ae6db7c2f2d24b5814e", ==> hero banner with form with dropdown.
# "69666d23db7c2f2d24b58296", ==> form with checkbox.
# "69666c93db7c2f2d24b58242", ==> button text being ipsum lorem
# "69666d8adb7c2f2d24b582ce", ==> button text being ipsum lorem and maps location
# "69666d78db7c2f2d24b582c2" ==> footer.

preset_section_ids = [
    "69666d3ddb7c2f2d24b582a2",
    "69666ae6db7c2f2d24b5814e",
    "69666d23db7c2f2d24b58296",
    "69666c93db7c2f2d24b58242",
    "69666d8adb7c2f2d24b582ce",
    "69666d78db7c2f2d24b582c2"
]

async def main_async():
    """Main async function to run the demo."""
    if not preset_section_ids:
        print("ERROR: preset_section_ids is empty. Populate it with valid section IDs from section_repo_prod.section_metadata.")
        print("Example: preset_section_ids = ['507f1f77bcf86cd799439011', '507f1f77bcf86cd799439012']")
        return

    # Setup environment
    setup_environment()
    env_utils.check_env_vars()

    # Setup configuration
    workflow_config = setup_workflow_config()
    business_config = get_default_business_config()

    # Generate unique request ID
    request_id = str(uuid.uuid4())

    print("=" * 60)
    print("PRESET SECTIONS WORKFLOW DEMO")
    print("=" * 60)
    print(f"\n📋 Request ID: {request_id}")
    print(f"📦 Section IDs: {preset_section_ids}")

    # Get color palette and font
    palette_data = get_color_palette_and_font(index=0)
    palette = palette_data["PALETTE"]
    font_family = palette_data["FONT_FAMILY"]

    print(f"\n🎨 Palette: {palette['palette_id']} ({palette['category']})")
    print(f"🔤 Font: {font_family}")

    # Create workflow using factory
    workflow = LandingPageWorkflowFactory.create("preset_sections", config=workflow_config)
    print(f"✅ Workflow initialized: {workflow.workflow_name}")

    print_workflow_header(
        "RUNNING PRESET SECTIONS WORKFLOW",
        request_id=request_id,
        Business=business_config["business_name"],
        Workflow=workflow.workflow_name,
        Section_Count=len(preset_section_ids),
    )

    # Create execution config with section_ids for PresetSectionsLandingPageWorkflow
    exec_config = create_default_execution_config(
        section_ids=preset_section_ids,
        use_mock_autopopulation=True
    )

    # Create workflow input
    workflow_input = PresetSectionsInput(
        business_name=business_config["business_name"],
        business_id=business_config["business_id"],
        request_id=request_id,
        section_ids=preset_section_ids,
        execution_config=exec_config,
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

    # Compile template from section IDs (DB-driven)
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
