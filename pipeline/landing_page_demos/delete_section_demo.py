#!/usr/bin/env python3
"""
Delete Section Demo Script

Demonstrates section deletion propagation:
1. Fetches compiled template from generated_templates_with_values
2. Calls save_template_updates with deleted_sections
3. Asserts both generated_templates_with_values and generation_template_sections
   are updated correctly (section removed from both)

Usage:
    poetry run python pipeline/landing_page_demos/delete_section_demo.py \
        --existing_request_id=8196cd24-fb31-42dd-9c23-cbbccf2b73f6 \
        --delete_index=1
"""

from absl import app, flags

from pipeline import env_utils
from pipeline.landing_page_demos.utils import setup_environment
from wwai_agent_orchestration.contracts.landing_page_builder.template_update import SaveTemplateRequest
from wwai_agent_orchestration.utils.landing_page_builder.template.db_service import template_db_service
from wwai_agent_orchestration.utils.landing_page_builder.template_utils import save_template_updates

FLAGS = flags.FLAGS
flags.DEFINE_string(
    "existing_request_id",
    None,
    "Generation version ID with completed autopop",
    required=True,
)
flags.DEFINE_integer(
    "delete_index",
    1,
    "0-based index of section to delete (1 = 2nd section)",
)


def main(argv):
    """Main entry point."""
    setup_environment()
    env_utils.check_env_vars()

    generation_version_id = FLAGS.existing_request_id
    delete_index = FLAGS.delete_index

    print("=" * 60)
    print("DELETE SECTION DEMO (Deletion Propagation)")
    print("=" * 60)
    print(f"\n  Generation ID : {generation_version_id}")
    print(f"  Delete index  : {delete_index}")
    print()

    # Step 1: Fetch compiled template
    doc = template_db_service.get_compiled_template(generation_version_id)
    if not doc:
        raise ValueError(
            f"generated_templates_with_values not found for {generation_version_id}. "
            "Ensure the generation has completed autopop and template compilation."
        )

    tbo = doc.get("template_build_output")
    if not tbo:
        raise ValueError(
            f"Document {generation_version_id} has no template_build_output."
        )

    enabled_section_ids = tbo.get("enabled_section_ids", [])
    if not enabled_section_ids:
        raise ValueError(
            f"Document {generation_version_id} has no enabled_section_ids."
        )

    # Step 2: Validate delete_index
    if delete_index < 0 or delete_index >= len(enabled_section_ids):
        raise ValueError(
            f"delete_index must be in [0, {len(enabled_section_ids)}). Got {delete_index}."
        )
    if len(enabled_section_ids) <= 1:
        raise ValueError(
            "Cannot delete the only section; at least one section must remain."
        )

    deleted_schema_id = enabled_section_ids[delete_index]

    # Step 3: Get before counts from both collections
    sections_count_before = len(enabled_section_ids)
    merged_before = template_db_service.get_merged_all(generation_version_id)
    template_sections_count_before = merged_before.get("section_count", 0)

    print(f"BEFORE: {sections_count_before} sections in generated_templates_with_values, "
          f"{template_sections_count_before} in generation_template_sections")
    print(f"Deleting section at index {delete_index}: {deleted_schema_id}")
    print()

    # Step 4: Call save_template_updates
    request = SaveTemplateRequest(
        section_updates={},
        section_order=None,
        deleted_sections=[deleted_schema_id],
    )
    save_template_updates(generation_version_id, request)

    # Step 5: Assertions
    doc_after = template_db_service.get_compiled_template(generation_version_id)
    tbo_after = doc_after.get("template_build_output", {})
    enabled_after = tbo_after.get("enabled_section_ids", [])
    sections_after = tbo_after.get("sections", {})
    section_id_list_after = tbo_after.get("section_id_list", [])

    merged_after = template_db_service.get_merged_all(generation_version_id)
    template_sections_count_after = merged_after.get("section_count", 0)
    section_ids_after = merged_after.get("section_ids", [])
    section_mappings_after = merged_after.get("section_mappings", [])

    print(f"AFTER: {len(enabled_after)} sections in generated_templates_with_values, "
          f"{template_sections_count_after} in generation_template_sections")
    print()

    # Assert generated_templates_with_values
    pass_gtwv = (
        deleted_schema_id not in enabled_after
        and deleted_schema_id not in sections_after
        and len(enabled_after) == sections_count_before - 1
    )
    if pass_gtwv:
        print("PASS: generated_templates_with_values - section removed")
    else:
        print("FAIL: generated_templates_with_values - section still present or count wrong")
        print(f"  deleted_schema_id in enabled_after: {deleted_schema_id in enabled_after}")
        print(f"  deleted_schema_id in sections_after: {deleted_schema_id in sections_after}")
        print(f"  expected count: {sections_count_before - 1}, got: {len(enabled_after)}")

    # Assert generation_template_sections
    pass_gts = (
        template_sections_count_after == template_sections_count_before - 1
        and len(section_mappings_after) == template_sections_count_after
    )
    if pass_gts:
        print("PASS: generation_template_sections - section removed")
    else:
        print("FAIL: generation_template_sections - count wrong")
        print(f"  expected count: {template_sections_count_before - 1}, got: {template_sections_count_after}")
        print(f"  section_mappings count: {len(section_mappings_after)}")

    print()
    print("=" * 60)
    if pass_gtwv and pass_gts:
        print("DEMO COMPLETED SUCCESSFULLY")
    else:
        print("DEMO FAILED - assertions did not pass")
    print("=" * 60)


if __name__ == "__main__":
    app.run(main)
