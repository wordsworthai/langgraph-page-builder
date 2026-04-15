#!/usr/bin/env python3
"""
Partial Autopop Workflow Demo Script

This script demonstrates the partial autopop workflow functionality:
1. Runs a full workflow to create a base template (or uses existing_request_id)
2. Runs PartialAutopopWorkflow in all 3 modes:
   - "styles": Regenerate styles only (with different palette)
   - "text": Regenerate text content only
   - "media": Regenerate images/media only
3. Outputs HTML URLs for all 4 versions for comparison

Usage:
    poetry run python pipeline/landing_page_demos/partial_autopop_demo.py --existing_request_id=fd85a7d2-f285-42fd-a803-061e3f3bc7e0

MongoDB: Checkpoints are loaded via the global db_manager (configured at startup).
  Ensure MONGO_CONNECTION_URI and CHECKPOINT_DB_NAME are set in .env if needed.
"""

import uuid
import asyncio

from absl import app, flags

from pipeline import env_utils
from pipeline.user_website_input_choices import get_color_palette_and_font
from pipeline.landing_page_demos.utils import (
    setup_environment,
    setup_workflow_config,
    create_default_execution_config,
    print_workflow_header,
    run_workflow_stream,
    get_html_url_from_state,
)
from wwai_agent_orchestration.agent_workflows.landing_page_builder.workflows.workflow_factory import LandingPageWorkflowFactory
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_inputs import (
    PartialAutopopInput,
    build_stream_kwargs,
)
from wwai_agent_orchestration.contracts.landing_page_builder.user_input import BrandContext

# Define flags
FLAGS = flags.FLAGS
flags.DEFINE_string(
    'existing_request_id',
    None,
    'Existing request ID (generation_version_id) to use instead of running a new full workflow',
    required=True
)


async def run_partial_autopop_workflow(
    workflow_config,
    partial_request_id,
    base_request_id,
    regenerate_mode,
    palette_override=None,
    font_family_override=None
):
    """Run partial autopop workflow for a specific mode."""
    mode_display = {
        "styles": "Styles Only",
        "text": "Text Content Only",
        "media": "Images/Media Only"
    }
    
    print_workflow_header(
        f"STEP 1.{regenerate_mode.upper()}: RUNNING PARTIAL AUTOPOP ({mode_display[regenerate_mode]})",
        request_id=partial_request_id,
        Mode=regenerate_mode,
        Source_Thread_ID=base_request_id[:8] + "..."
    )
    
    # Create partial autopop workflow using factory
    partial_workflow = LandingPageWorkflowFactory.create(
        "partial_autopop",
        config=workflow_config,
        regenerate_mode=regenerate_mode
    )
    
    print(f"✅ Workflow initialized: {partial_workflow.workflow_name}")
    
    if palette_override:
        print(f"🎨 NEW Palette: {palette_override['palette_id']} ({palette_override['category']})")
    if font_family_override:
        print(f"🔤 NEW Font: {font_family_override}")
    
    exec_config = create_default_execution_config(
        use_mock_autopopulation=True
    )
    
    # Create workflow input (checkpoint loading uses global db_manager)
    workflow_input = PartialAutopopInput(
        request_id=partial_request_id,
        source_thread_id=base_request_id,
        execution_config=exec_config,
        regenerate_mode=regenerate_mode,
        brand_context=BrandContext(palette=palette_override, font_family=font_family_override),
    )
    
    # Build stream kwargs
    stream_kwargs = build_stream_kwargs(workflow_input)
    
    # Run workflow
    print("\n🚀 Starting Partial Autopop Workflow...")
    print(f"   Restoring state from: {base_request_id[:8]}...")
    print(f"   Regenerating: {mode_display[regenerate_mode]}")
    print("-" * 50)
    
    await run_workflow_stream(partial_workflow, stream_kwargs)
    
    return partial_workflow


async def main_async():
    """Main async function to run the demo."""
    # Setup environment
    setup_environment()
    env_utils.check_env_vars()
    
    # Get existing_request_id from flags
    existing_request_id = FLAGS.existing_request_id
    
    # Setup workflow configuration
    workflow_config = setup_workflow_config()
    
    # Generate unique request IDs
    base_request_id = existing_request_id
    styles_request_id = str(uuid.uuid4())
    text_request_id = str(uuid.uuid4())
    media_request_id = str(uuid.uuid4())
    
    print("=" * 60)
    print("PARTIAL AUTOPOP WORKFLOW DEMO")
    print("=" * 60)
    print(f"\n📋 Base Workflow Request ID (existing): {base_request_id}")
    print(f"📋 Styles-Only Request ID: {styles_request_id}")
    print(f"📋 Text-Only Request ID: {text_request_id}")
    print(f"📋 Media-Only Request ID: {media_request_id}")
    
    # Styles-only workflow: index 6 = different palette (different from friendly-1)
    palette_data_styles = get_color_palette_and_font(index=6)
    palette_styles = palette_data_styles["PALETTE"]
    font_family_styles = palette_data_styles["FONT_FAMILY"]
    
    print(f"\n🎨 Styles-Only Palette: {palette_styles['palette_id']} ({palette_styles['category']})")
    print(f"🔤 Styles-Only Font: {font_family_styles}")
    
    # Step 1: Run partial autopop workflows
    # 2a. Styles-only (with different palette)
    styles_workflow = await run_partial_autopop_workflow(
        workflow_config,
        styles_request_id,
        base_request_id,
        regenerate_mode="styles",
        palette_override=palette_styles,
        font_family_override=font_family_styles
    )
    styles_html_url = get_html_url_from_state(styles_workflow, styles_request_id, workflow_config)
    
    # 2b. Text-only
    text_workflow = await run_partial_autopop_workflow(
        workflow_config,
        text_request_id,
        base_request_id,
        regenerate_mode="text"
    )
    text_html_url = get_html_url_from_state(text_workflow, text_request_id, workflow_config)
    
    # 2c. Media-only
    media_workflow = await run_partial_autopop_workflow(
        workflow_config,
        media_request_id,
        base_request_id,
        regenerate_mode="media"
    )
    media_html_url = get_html_url_from_state(media_workflow, media_request_id, workflow_config)
    
    # Step 2: Output all HTML URLs for comparison
    print("\n" + "=" * 60)
    print("📊 FINAL RESULTS - HTML URLs FOR VALIDATION")
    print("=" * 60)
    
    print(f"\n1️⃣ STYLES-ONLY REGENERATION:")
    print(f"   Palette: {palette_styles['palette_id']} ({palette_styles['category']}) [CHANGED]")
    print(f"   Font: {font_family_styles} [CHANGED]")
    print(f"   HTML: {styles_html_url or 'N/A'}")
    print(f"   Expected: Different colors/styles, same content and images")
    
    print(f"\n2️⃣ TEXT-ONLY REGENERATION:")
    print(f"   HTML: {text_html_url or 'N/A'}")
    print(f"   Expected: Different text content, same styles and images")
    
    print(f"\n3️⃣ MEDIA-ONLY REGENERATION:")
    print(f"   HTML: {media_html_url or 'N/A'}")
    print(f"   Expected: Different images/media, same styles and text")
    
    # Compile templates from section IDs for all partial workflows (DB-driven)
    print("\n" + "=" * 60)
    print("✅ DEMO COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("\n💡 Validation Checklist:")
    print("   □ Styles-only: Colors/fonts changed, content/images unchanged")
    print("   □ Text-only: Text content changed, styles/images unchanged")
    print("   □ Media-only: Images changed, styles/text unchanged")
    print("=" * 60)


def main(argv):
    """Main function for absl app.run."""
    asyncio.run(main_async())


if __name__ == "__main__":
    app.run(main)
