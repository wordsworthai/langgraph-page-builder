import json
from pathlib import Path

from wwai_agent_orchestration.evals import cli


def test_build_set_command_writes_json(tmp_path):
    output_file = tmp_path / "eval_set.json"
    cli.main(
        [
            "--store",
            "local",
            "--local-store-dir",
            str(tmp_path / "store"),
            "build-set",
            "--eval-set-id",
            "set_cli_1",
            "--eval-type",
            "landing_page",
            "--business-ids",
            "biz_1,biz_2",
            "--output-json",
            str(output_file),
        ]
    )
    payload = json.loads(output_file.read_text())
    assert payload["eval_set_id"] == "set_cli_1"
    assert len(payload["cases"]) == 2


def test_run_set_dry_run_from_json(tmp_path):
    eval_set_payload = {
        "eval_set_id": "set_cli_2",
        "eval_type": "landing_page",
        "version": "v1",
        "seed": 1,
        "cases": [
            {
                "case_id": "case_abc123",
                "eval_set_id": "set_cli_2",
                "eval_type": "landing_page",
                "workflow_mode": "landing_page",
                "business_id": "biz_1",
                "business_index": 0,
                "website_intention": "lead_generation",
                "website_tone": "professional",
                "inputs": {"website_intention": "lead_generation"},
                "metadata": {},
            }
        ],
    }
    eval_set_file = tmp_path / "set.json"
    eval_set_file.write_text(json.dumps(eval_set_payload))

    cli.main(
        [
            "--store",
            "local",
            "--local-store-dir",
            str(tmp_path / "store"),
            "run-set",
            "--eval-set-json",
            str(eval_set_file),
            "--dry-run",
        ]
    )
    store_runs = Path(tmp_path / "store" / "runs.jsonl")
    assert not store_runs.exists() or store_runs.read_text().strip() == ""

