# wwai-agent-orchestration

A [LangGraph](https://github.com/langchain-ai/langgraph)-based AI agent orchestration system that takes business information (name, brand, website intent) and produces a fully populated HTML landing page.

The pipeline runs a multi-phase sequence of LLM agents, data providers, and a template rendering service:

```
Business Input → Data Collection → Template Selection → Autopopulation → HTML Output
```

See [docs/architecture.md](docs/architecture.md) for a full breakdown of the pipeline, workflow modes, and key abstractions.

---

## Requirements

- Python 3.11+
- [Poetry](https://python-poetry.org/)
- MongoDB
- Redis
- Node.js compiler service (for HTML rendering)

---

## Installation

```bash
git clone <repository-url>
cd wwai-agent-orchestration
poetry install
cp .env.example .env
# Edit .env with your API keys and service URLs
```

---

## Quick Start

Run the full end-to-end workflow in mock mode (no LLM calls, placeholder content):

```bash
poetry run python pipeline/landing_page_demos/landing_page_demo.py \
    --business_id=<your-business-id> \
    --business_name="Your Business Name"
```

The script prints a `Request ID` and an HTML file path (or S3 URL) on completion.

For real LLM-generated content, set `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `GEMINI_API_KEY` in `.env` and set `use_mock_autopopulation=False` in the demo script.

---

## Configuration

Copy `.env.example` to `.env` and fill in the values for the services you need. See `.env.example` for inline documentation on every variable.

Minimum required for local mock mode:

| Variable | Default |
|----------|---------|
| `ENVIRONMENT` | `local` |
| `MONGO_CONNECTION_URI` | `mongodb://localhost:27017/` |
| `REDIS_HOST` | `localhost` |
| `NODE_SERVER_URL` | `http://localhost:3002` |

---

## Documentation

- [docs/architecture.md](docs/architecture.md) — Pipeline, workflow modes, key abstractions, external services
- [docs/usage.md](docs/usage.md) — All demo scripts, eval CLI, configuration reference

---

## License

MIT — see [LICENSE](LICENSE).
