from pathlib import Path

from wwai_agent_orchestration.evals.cli import build_parser


def test_cli_contains_cutover_commands():
    parser = build_parser()
    help_text = parser.format_help()
    assert "build-set" in help_text
    assert "run-set" in help_text
    assert "resume" in help_text
