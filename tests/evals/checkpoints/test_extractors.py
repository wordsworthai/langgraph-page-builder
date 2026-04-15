from wwai_agent_orchestration.evals.graph_output_extractors.landing_page_builder import (
    LandingPageExtractor,
    PresetSectionsExtractor,
    TemplateSelectionExtractor,
)


def test_template_selection_extractor_maps_template_output():
    state = {
        "refined_templates": [
            {
                "template_id": "tpl_001",
                "reasoning": "good fit",
                "section_info": [{"section_id": "a"}],
            }
        ]
    }
    output = TemplateSelectionExtractor().extract(state, [])
    assert output.template_id == "tpl_001"
    assert output.selected_template_index == 0


def test_preset_sections_extractor_maps_html_and_sections():
    state = {
        "generation_version_id": "gen_1",
        "execution_config": {"routing": {"section_ids": ["h_1", "m_1", "f_1"]}},
        "post_process": {
            "html_compilation_results": {
                "compiled_html_s3_url": "https://example.com/preset",
                "compiled_html_path": "/tmp/preset.html",
            }
        },
    }
    output = PresetSectionsExtractor().extract(state, [])
    assert output.generation_version_id == "gen_1"
    assert output.section_ids[0] == "h_1"
    assert output.html_url == "https://example.com/preset"


def test_preset_sections_extractor_post_process_template_compilation_results():
    """Extractor reads generation_version_id from post_process.template_compilation_results."""
    state = {
        "execution_config": {"routing": {"section_ids": ["h_1", "m_1", "f_1"]}},
        "post_process": {
            "template_compilation_results": {
                "status": "success",
                "generation_version_id": "run_abc123",
                "compiled_at": 1772535894.0,
            },
            "html_compilation_results": {
                "compiled_html_s3_url": "https://example-bucket.s3.amazonaws.com/ai_pages/run_abc123/compiled.html",
            },
        },
    }
    output = PresetSectionsExtractor().extract(state, [])
    assert output.generation_version_id == "run_abc123"
    assert output.html_url == "https://example-bucket.s3.amazonaws.com/ai_pages/run_abc123/compiled.html"
    assert output.section_ids == ["h_1", "m_1", "f_1"]


def test_landing_page_extractor_maps_core_fields():
    state = {
        "generation_version_id": "gen_lp",
        "refined_templates": [
            {"template_id": "tpl_lp", "section_info": [{"section_id": "hero_1"}]}
        ],
        "post_process": {
            "html_compilation_results": {"compiled_html_s3_url": "https://example.com/lp"}
        },
    }
    output = LandingPageExtractor().extract(state, [])
    assert output.generation_version_id == "gen_lp"
    assert output.template_id == "tpl_lp"
    assert output.selected_sections == ["hero_1"]


def test_landing_page_extractor_nested_template_channel():
    """Extractor reads from template.refined_templates (nested TemplateResult)."""
    state = {
        "input": {"generation_version_id": "gen_nested"},
        "template": {
            "refined_templates": [
                {"template_id": "tpl_nested", "section_info": [{"section_id": "s1"}, {"section_id": "s2"}]}
            ]
        },
        "post_process": {"html_compilation_results": {"compiled_html_s3_url": "https://example.com/nested"}},
    }
    output = LandingPageExtractor().extract(state, [])
    assert output.generation_version_id == "gen_nested"
    assert output.template_id == "tpl_nested"
    assert output.selected_sections == ["s1", "s2"]
    assert output.html_url == "https://example.com/nested"


def test_landing_page_extractor_resolved_recommendations_fallback():
    """Extractor falls back to resolved_template_recommendations when template is empty."""
    state = {
        "input": {"generation_version_id": "gen_resolved"},
        "resolved_template_recommendations": [
            {
                "template_id": "ea94691b-1db9-41d3-892a-13df1b06700f",
                "template_name": "Custom Section Selection",
                "section_mappings": [
                    {"section_id": "69666d36db7c2f2d24b5829e", "section_l0": "Nav", "section_l1": "Nav Bar"},
                    {"section_id": "69666ae6db7c2f2d24b5814e", "section_l0": "Hero", "section_l1": "Hero"},
                ],
            }
        ],
    }
    output = LandingPageExtractor().extract(state, [])
    assert output.generation_version_id == "gen_resolved"
    assert output.template_id == "ea94691b-1db9-41d3-892a-13df1b06700f"
    assert output.selected_sections == ["69666d36db7c2f2d24b5829e", "69666ae6db7c2f2d24b5814e"]


def test_template_selection_extractor_nested_template_channel():
    """Extractor reads from template.refined_templates (nested TemplateResult)."""
    state = {
        "template": {
            "refined_templates": [
                {
                    "template_id": "tpl_nested",
                    "template_name": "Alpha",
                    "reasoning": "best match",
                    "section_info": [{"section_id": "a", "section_l0": "Hero"}],
                }
            ]
        }
    }
    output = TemplateSelectionExtractor().extract(state, [])
    assert output.template_id == "tpl_nested"
    assert output.selected_template_index == 0
    assert output.rationale == "best match"
    assert output.section_plan == [{"section_id": "a", "section_l0": "Hero"}]


def test_template_selection_extractor_resolved_recommendations_fallback():
    """Extractor falls back to resolved_template_recommendations when template is empty."""
    state = {
        "resolved_template_recommendations": [
            {
                "template_id": "tpl_resolved",
                "template_name": "Resolved Template",
                "section_mappings": [
                    {"section_id": "sec_1", "section_l0": "Hero", "section_l1": "Simple Hero"},
                    {"section_id": "sec_2", "section_l0": "Footer", "section_l1": "Footer A"},
                ],
            }
        ]
    }
    output = TemplateSelectionExtractor().extract(state, [])
    assert output.template_id == "tpl_resolved"
    assert output.selected_template_index == 0
    assert output.section_plan == [
        {"section_id": "sec_1", "section_l0": "Hero", "section_l1": "Simple Hero"},
        {"section_id": "sec_2", "section_l0": "Footer", "section_l1": "Footer A"},
    ]

