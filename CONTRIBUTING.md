# Contributing

Thank you for your interest in contributing to wwai-agent-orchestration.

## Development Setup

**Prerequisites:**
- Python 3.11+
- [Poetry](https://python-poetry.org/docs/#installation)
- MongoDB (local or remote)
- Redis (local or remote)

**Install dependencies:**
```bash
poetry install
```

**Configure environment:**
```bash
cp .env.example .env
# Fill in your API keys and service URLs
```

**Note:** The `template-json-builder` and `wwai-bundle-pipeline` dependencies are being open-sourced separately. Until those repos are public, a full end-to-end run requires access to the Wordsworth AI GitHub org.

## Running Tests

```bash
# Run all tests
poetry run pytest

# Run a specific file
poetry run pytest tests/nodes/landing_page_builder/test_some_node.py

# Run by pattern
poetry run pytest -k "test_name_pattern"
```

## Running Demos

```bash
poetry run python pipeline/landing_page_demos/landing_page_demo.py
```

See `pipeline/landing_page_demos/README.md` for all available demos.

## Pull Requests

1. Fork the repo and create a branch from `main`.
2. Make your changes with clear, focused commits.
3. Ensure all tests pass before submitting.
4. Open a PR with a clear description of what changed and why.

## Reporting Issues

Open a GitHub issue with a minimal reproduction case and relevant environment details (OS, Python version, error traceback).

## Code Style

No formatter is enforced. Follow the patterns already present in the file you're editing.
