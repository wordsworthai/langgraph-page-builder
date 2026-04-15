"""Unit tests for EvalRunOutputWriter."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from wwai_agent_orchestration.evals.runners.run_output_writer import EvalRunOutputWriter


def test_write_run_output_creates_file_with_expected_structure():
    """EvalRunOutputWriter.write_run_output writes a JSON file with run_id, thread_id, case_id, workflow_mode, final_state, history, extractor_output."""
    with TemporaryDirectory() as tmpdir:
        writer = EvalRunOutputWriter(tmpdir)
        writer.write_run_output(
            run_id="run_123",
            thread_id="thread_456",
            case_id="case_789",
            workflow_mode="template_selection",
            final_state={"template_id": "tpl_1", "input": {"foo": "bar"}},
            extractor_output={"template_id": "tpl_1", "raw_output": {}},
        )
        out_path = Path(tmpdir) / "final_state_run_123_case_789.json"
        assert out_path.exists()
        payload = json.loads(out_path.read_text())
        assert payload["run_id"] == "run_123"
        assert payload["thread_id"] == "thread_456"
        assert payload["case_id"] == "case_789"
        assert payload["workflow_mode"] == "template_selection"
        assert payload["final_state"] == {"template_id": "tpl_1", "input": {"foo": "bar"}}
        assert payload["extractor_output"] == {"template_id": "tpl_1", "raw_output": {}}


def test_write_run_output_creates_dir_if_missing():
    """EvalRunOutputWriter creates the output directory if it does not exist."""
    with TemporaryDirectory() as tmpdir:
        nested = Path(tmpdir) / "nested" / "dir"
        writer = EvalRunOutputWriter(nested)
        writer.write_run_output(
            run_id="r1",
            thread_id="t1",
            case_id="c1",
            workflow_mode="landing_page",
            final_state={},
            extractor_output={},
        )
        assert (nested / "final_state_r1_c1.json").exists()
