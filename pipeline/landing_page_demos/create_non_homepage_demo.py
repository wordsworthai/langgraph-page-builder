#!/usr/bin/env python3
"""
Create Non-Homepage Demo Script

This script demonstrates creating a non-homepage page (e.g. Services, Contact Us)
using PresetSectionsLandingPageWorkflow with a parent homepage:

1. Fetches body-only section IDs from the curated_pages collection
2. Runs PresetSectionsLandingPageWorkflow with page_type and parent_generation_version_id
3. At compilation time, the parent homepage's header/footer are automatically
   looked up from DB and merged with this page's body sections

Usage:
    poetry run python pipeline/landing_page_demos/create_non_homepage_demo.py \
        --homepage_generation_version_id=ab8265e2-212a-403c-a8d5-4e49ed33f1b7 \
        --curated_page_path=services

Prerequisites:
    - Run create_homepage_demo.py first and pass its generation_version_id via --homepage_generation_version_id
    - Ensure curated_pages collection exists in section_repo_prod DB
"""

import uuid
import asyncio
from typing import List

from absl import app, flags

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
from bson import ObjectId

from wwai_agent_orchestration.core.database import db_manager
from wwai_agent_orchestration.constants.section_types import (
    HEADER_SECTION_L0_LIST,
    FOOTER_SECTION_L0_LIST,
)
from wwai_agent_orchestration.data.providers.section_catalog_provider import (
    SectionCatalogProvider,
)
from template_json_builder.db.queries import SECTION_REPO_PROD_DB

FLAGS = flags.FLAGS
flags.DEFINE_string(
    "homepage_generation_version_id",
    None,
    "Generation version ID from the homepage demo (create_homepage_demo.py output)",
    required=True,
)
flags.DEFINE_string(
    "curated_page_path",
    "services",
    "Curated page to build (matches page_path in curated_pages; also used as page_type)",
)


def _filter_out_header_footer_sections(section_ids: List[str]) -> List[str]:
    """
    Filter out header/footer sections; return only body section IDs in order.
    Uses section repo to look up section_l0 for each ID.
    """
    if not section_ids:
        return []
    disallowed_l0 = set(HEADER_SECTION_L0_LIST) | set(FOOTER_SECTION_L0_LIST)
    try:
        provider = SectionCatalogProvider()
        sections = provider.fetch_sections_with_metadata(
            query_filter={"_id": {"$in": [ObjectId(sid) for sid in section_ids]}}
        )
    except Exception:
        return section_ids  # Fallback: use all if lookup fails

    id_to_l0 = {str(s.get("_id", "")): s.get("section_l0", "") for s in sections}
    return [
        sid for sid in section_ids
        if id_to_l0.get(sid, "") not in disallowed_l0
    ]


def fetch_body_section_ids_from_curated_pages(
    page_path: str,
    db_name: str = SECTION_REPO_PROD_DB,
    collection_name: str = "curated_pages",
) -> List[str]:
    """
    Read body-only section IDs from curated_pages collection.
    Expects simplified schema (section_ids). Filters out header/footer via section repo.
    """
    db = db_manager.get_database(db_name)
    collection = db[collection_name]

    doc = collection.find_one({"page_path": page_path})
    if not doc:
        raise ValueError(
            f"No curated page found for page_path='{page_path}' "
            f"in {db_name}.{collection_name}"
        )

    section_ids = [str(sid) for sid in doc.get("section_ids", [])]
    if not section_ids:
        print(f"  Curated page '{page_path}': no section_ids found")
        return []

    body_ids = _filter_out_header_footer_sections(section_ids)
    print(f"  Curated page '{page_path}': {len(body_ids)} body sections "
          f"(filtered from {len(section_ids)} total)")
    return body_ids


async def main_async():
    """Main async function to run the non-homepage demo."""
    setup_environment()
    env_utils.check_env_vars()

    workflow_config = setup_workflow_config()
    business_config = get_default_business_config()

    print("=" * 60)
    print("CREATE NON-HOMEPAGE DEMO")
    print("=" * 60)
    print(f"\nParent Homepage ID: {FLAGS.homepage_generation_version_id}")
    print(f"Curated Page Path: {FLAGS.curated_page_path}")

    # Fetch body section IDs from curated_pages
    print(f"\nFetching body section IDs from curated_pages...")
    body_section_ids = fetch_body_section_ids_from_curated_pages(FLAGS.curated_page_path)

    if not body_section_ids:
        print("ERROR: No body section IDs found in curated_pages.")
        return

    request_id = str(uuid.uuid4())

    print(f"\nRequest ID: {request_id}")
    print(f"Body Section IDs ({len(body_section_ids)}): {body_section_ids}")

    palette_data = get_color_palette_and_font(index=4)
    palette = palette_data["PALETTE"]
    font_family = palette_data["FONT_FAMILY"]

    print(f"\nPalette: {palette['palette_id']} ({palette['category']})")
    print(f"Font: {font_family}")

    workflow = LandingPageWorkflowFactory.create("preset_sections", config=workflow_config)
    print(f"Workflow initialized: {workflow.workflow_name}")

    print_workflow_header(
        "RUNNING NON-HOMEPAGE WORKFLOW",
        request_id=request_id,
        Business=business_config["business_name"],
        Workflow=workflow.workflow_name,
        Section_Count=len(body_section_ids),
        Page_Type=FLAGS.curated_page_path,
        Parent_Homepage=FLAGS.homepage_generation_version_id,
    )

    exec_config = create_default_execution_config(
        section_ids=body_section_ids,
        use_mock_autopopulation=True
    )

    workflow_input = PresetSectionsInput(
        business_name=business_config["business_name"],
        business_id=business_config["business_id"],
        request_id=request_id,
        section_ids=body_section_ids,
        execution_config=exec_config,
        generic_context=GenericContext(query="", sector=None, page_url=None),
        website_context=WebsiteContext(
            website_intention=business_config["website_intention"],
            website_tone=business_config["website_tone"],
        ),
        brand_context=BrandContext(palette=palette, font_family=font_family),
        external_data_context=ExternalDataContext(yelp_url=""),
        page_type=FLAGS.curated_page_path,
        parent_generation_version_id=FLAGS.homepage_generation_version_id,
    )

    stream_kwargs = build_stream_kwargs(workflow_input)
    await run_workflow_stream(workflow, stream_kwargs)

    print_workflow_header("VIEWING WORKFLOW RESULTS", request_id=request_id)
    html_url = print_workflow_results(workflow, request_id, workflow_config)

    print("\n" + "=" * 60)
    print(f"NON-HOMEPAGE PAGE '{FLAGS.curated_page_path}' CREATED SUCCESSFULLY!")
    print("=" * 60)
    if html_url:
        print(f"\nHTML URL: {html_url}")
    print(f"\nGeneration Version ID: {request_id}")
    print(f"Parent Homepage ID: {FLAGS.homepage_generation_version_id}")
    print("Header/footer were merged from the parent homepage at compilation time.")


def main(argv):
    """Entry point for absl."""
    asyncio.run(main_async())


if __name__ == "__main__":
    app.run(main)
