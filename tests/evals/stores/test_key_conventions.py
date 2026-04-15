from wwai_agent_orchestration.evals.stores.key_conventions import (
    CanonicalKeys,
    build_output_doc_id,
    normalize_task_type,
    validate_canonical_keys,
)


def test_normalize_task_type_passes_through():
    """normalize_task_type returns task_type as-is (no normalization)."""
    assert normalize_task_type("landing_page") == "landing_page"
    assert normalize_task_type("template_selection") == "template_selection"
    assert normalize_task_type("section_coverage") == "section_coverage"


def test_validate_canonical_keys():
    keys = CanonicalKeys(
        eval_set_id="set_1",
        case_id="case_abc123",
        run_id="run_abc123",
        thread_id="run_abc123",
        task_type="landing_page",
    )
    validate_canonical_keys(keys)


def test_output_doc_id_uniqueness():
    first = build_output_doc_id("set_1", "run_1", "case_1")
    second = build_output_doc_id("set_1", "run_2", "case_1")
    assert first != second

