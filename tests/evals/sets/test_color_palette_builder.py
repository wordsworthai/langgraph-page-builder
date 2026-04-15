from wwai_agent_orchestration.evals.sets.landing_page_builder.color_palette_builder import (
    build_color_palette_eval_set,
)


def test_color_palette_builder_with_palette_ids_filter():
    """When palette_ids is provided, only those palettes are used."""
    eval_set = build_color_palette_eval_set(
        eval_set_id="cp_filtered",
        version="v1",
        seed=42,
        business_ids=["biz_1"],
        palette_ids=["friendly-1", "bold-2", "minimal-1"],
    )
    assert len(eval_set.cases) == 3
    assert [c.set_inputs["palette_id"] for c in eval_set.cases] == [
        "friendly-1",
        "bold-2",
        "minimal-1",
    ]
    for case in eval_set.cases:
        psi = case.workflow_inputs["preset_sections_input"]
        assert "brand_context" in psi
        assert psi["brand_context"]["palette"] is not None
        assert psi["brand_context"]["font_family"] is not None


def test_color_palette_builder_without_filter_uses_all_palettes():
    """When palette_ids is None, all palettes are used."""
    eval_set = build_color_palette_eval_set(
        eval_set_id="cp_all",
        version="v1",
        seed=42,
        business_ids=["biz_1"],
    )
    from pipeline.user_website_input_choices import get_expanded_palettes

    expanded = get_expanded_palettes()
    assert len(eval_set.cases) == len(expanded)


def test_color_palette_builder_raises_on_unknown_palette_id():
    import pytest

    with pytest.raises(ValueError, match="Unknown palette_id 'invalid-id'"):
        build_color_palette_eval_set(
            eval_set_id="cp_bad",
            version="v1",
            seed=42,
            business_ids=["biz_1"],
            palette_ids=["friendly-1", "invalid-id"],
        )
