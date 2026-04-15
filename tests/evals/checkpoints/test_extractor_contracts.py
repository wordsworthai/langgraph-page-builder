import json
from pathlib import Path

from wwai_agent_orchestration.evals.graph_output_extractors.landing_page_builder import (
    LandingPageExtractor,
    PresetSectionsExtractor,
    TemplateSelectionExtractor,
)


FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "evals" / "checkpoints"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text())


def test_template_selection_contract_fixture():
    state = _load_fixture("template_selection_state.json")
    output = TemplateSelectionExtractor().extract(state, [])
    assert output.workflow_mode == "template_selection"
    assert output.template_id == "tpl_001"


def test_preset_sections_contract_fixture():
    state = _load_fixture("preset_sections_state.json")
    output = PresetSectionsExtractor().extract(state, [])
    assert output.workflow_mode == "preset_sections"
    assert output.section_ids == ["h_1", "m_1", "m_2", "f_1"]


def test_landing_page_contract_fixture():
    state = _load_fixture("landing_page_state.json")
    output = LandingPageExtractor().extract(state, [])
    assert output.workflow_mode == "landing_page"
    assert output.generation_version_id == "gen_landing_1"

