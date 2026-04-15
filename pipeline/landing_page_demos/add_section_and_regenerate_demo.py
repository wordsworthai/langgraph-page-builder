#!/usr/bin/env python3
"""
Add Section In-Place + Regenerate Demo Script

Demonstrates the two-phase flow:
1. add_section_in_place: Updates 3 DBs in place with lorem content (no redirect)
2. regenerate_section: Runs AI to replace lorem with generated content

Usage:
    poetry run python pipeline/landing_page_demos/add_section_and_regenerate_demo.py \
        --existing_request_id=d0d6c80c-b7aa-4028-8736-562868fb8944 \
        --section_id=69666ae6db7c2f2d24b5814e \
        --insert_index=1
        

    poetry run python pipeline/landing_page_demos/add_section_and_regenerate_demo.py \
        --existing_request_id=232a5540-f361-4a3a-96cf-7499c3877888 \
        --section_id=69666aeedb7c2f2d24b58152 \
        --mode=replace \
        --replace_index=1

Notes:
    - Step 1: add_section_in_place updates 3 DBs in place (no redirect)
    - Step 2: Regenerate creates a NEW generation version (redirect to new URL)
    - add_section_in_place updates generation_template_sections, autopopulation_snapshots,
      generated_templates_with_values with lorem content
    - Regenerate runs regenerate_section workflow with source=original, request_id=new UUID
"""

import asyncio
import uuid

from absl import app, flags

from pipeline import env_utils
from pipeline.landing_page_demos.utils import (
    setup_environment,
    setup_workflow_config,
    create_default_execution_config,
    print_workflow_header,
    run_workflow_stream,
    get_html_url_from_state,
)
from wwai_agent_orchestration.agent_workflows.landing_page_builder.workflows.workflow_factory import (
    LandingPageWorkflowFactory,
)
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_inputs import (
    RegenerateSectionInput,
    build_stream_kwargs,
)
from wwai_agent_orchestration.utils.landing_page_builder.section_add_utils import (
    add_section_in_place,
)

FLAGS = flags.FLAGS
flags.DEFINE_string(
    "existing_request_id",
    None,
    "Generation to modify (must have completed autopop)",
    required=True,
)
flags.DEFINE_string(
    "section_id",
    None,
    "ObjectId of the section to add/replace from developer_hub_prod_sections",
    required=True,
)
flags.DEFINE_integer(
    "insert_index",
    -1,
    "Position to insert (insert mode); -1 = beginning",
)
flags.DEFINE_string(
    "mode",
    "insert",
    "Operation mode: 'insert' or 'replace'",
)
flags.DEFINE_integer(
    "replace_index",
    None,
    "0-based index for replace mode",
)


async def main_async():
    """Main async entry point."""
    setup_environment()
    env_utils.check_env_vars()

    generation_version_id = FLAGS.existing_request_id
    section_id = FLAGS.section_id
    insert_index = FLAGS.insert_index
    mode = FLAGS.mode
    replace_index = FLAGS.replace_index

    if mode == "replace" and replace_index is None:
        raise ValueError("replace_index is required when mode='replace'")

    target_index = replace_index if mode == "replace" else insert_index
    if target_index < 0 and mode == "insert":
        target_index = 0

    print("=" * 60)
    print("ADD SECTION IN-PLACE + REGENERATE DEMO")
    print("=" * 60)
    print(f"\n  Generation ID : {generation_version_id}")
    print(f"  Section       : {section_id}")
    print(f"  Mode          : {mode}")
    print(f"  Target index  : {target_index}")
    print()

    # ---- Step 1: add_section_in_place ----
    print_workflow_header(
        "STEP 1: add_section_in_place (updates 3 DBs with lorem)",
        request_id=generation_version_id,
        section_id=section_id,
        mode=mode,
        insert_index=insert_index,
        replace_index=replace_index,
    )

    await add_section_in_place(
        generation_version_id=generation_version_id,
        section_id=section_id,
        insert_index=insert_index,
        mode=mode,
        replace_index=replace_index,
    )

    print("  Done. 3 DBs updated with lorem content.")
    print()

    # ---- Step 2: regenerate_section workflow (regenerate content with AI) ----
    # Section is already at target_index from Step 1.
    # Creates a NEW generation version. Restores from source checkpoint, replace runs,
    # autopop generates AI content. merge_source_snapshots uses generated_templates_with_values
    # (from step 1) and overwrites new section's lorem with AI.
    new_request_id = str(uuid.uuid4())
    section_index = target_index
    print_workflow_header(
        "STEP 2: regenerate_section workflow (regenerate with AI)",
        request_id=new_request_id,
        source_thread_id=generation_version_id,
        section_id=section_id,
        mode="replace",
        insert_index=insert_index,
        replace_index=section_index,
    )

    workflow_config = setup_workflow_config()
    workflow = LandingPageWorkflowFactory.create("regenerate_section", config=workflow_config)
    print(f"Workflow initialized: {workflow.workflow_name}")
    print(f"  New generation ID: {new_request_id}")

    exec_config = create_default_execution_config(use_mock_autopopulation=True)

    workflow_input = RegenerateSectionInput(
        request_id=new_request_id,
        source_thread_id=generation_version_id,
        section_id=section_id,
        section_index=section_index,
        execution_config=exec_config,
    )

    stream_kwargs = build_stream_kwargs(workflow_input)

    print("\nStarting Regenerate Section Workflow...")
    print("-" * 50)

    await run_workflow_stream(workflow, stream_kwargs)

    html_url = get_html_url_from_state(workflow, new_request_id, workflow_config)

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"\n  HTML URL: {html_url or 'N/A'}")
    print(f"  Source generation: {generation_version_id}")
    print(f"  New generation: {new_request_id}")
    print()
    print("Validation checklist:")
    print("  - add_section_in_place updated 3 DBs with lorem (in-place)")
    print("  - regenerate_section workflow created new generation with AI content")
    print("  - Redirect to new generation version")
    print("=" * 60)


def main(argv):
    """Entry point for absl."""
    asyncio.run(main_async())


if __name__ == "__main__":
    app.run(main)
