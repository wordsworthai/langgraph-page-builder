# Usage

`wwai-agent-orchestration` is a LangGraph-based pipeline that takes business information and produces a populated HTML landing page. This document covers installation, configuration, and how to run the available demo and evaluation scripts.

---

## Installation

**Requirements:** Python 3.11+, Poetry, Node.js (for HTML compilation), MongoDB, Redis

```bash
git clone <repository-url>
cd wwai-agent-orchestration
poetry install
cp .env.example .env
# Edit .env with your service credentials
```

---

## Configuration

Copy `.env.example` to `.env` and fill in the values you need. See `.env.example` for inline comments on every variable.

### Required for all demos

| Variable | Purpose | Default |
|----------|---------|---------|
| `ENVIRONMENT` | Config profile: `local`, `dev`, `staging`, `prod` | `local` |
| `MONGO_CONNECTION_URI` | MongoDB connection string | `mongodb://localhost:27017/` |
| `REDIS_HOST` | Redis hostname for LangGraph node cache | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `NODE_SERVER_URL` | Node.js HTML compiler service URL | `http://localhost:3002` |

### Required for real content (LLM calls)

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | Template generation, content autopopulation, color agents |
| `ANTHROPIC_API_KEY` | Alternative LLM provider; LLM-as-judge for evals |
| `GEMINI_API_KEY` | URL page context extraction; alternative LLM |

### Required for business data

| Variable | Purpose |
|----------|---------|
| `RAPIDAPI_KEY` | Yelp business details via RapidAPI |
| `RAPIDAPI_HOST` | RapidAPI host for Yelp endpoint |

### Required for S3 output

| Variable | Purpose |
|----------|---------|
| `ACCESS_KEY_ID` | AWS access key |
| `SECRET_ACCESS_KEY` | AWS secret key |
| `S3_BUCKET_NAME` | S3 bucket for compiled HTML uploads |
| `S3_BUCKET_REGION` | AWS region for the bucket |

### Section repository (MongoDB)

| Variable | Purpose |
|----------|---------|
| `SECTION_REPO_DATABASE` | MongoDB database containing the section catalog |
| `SECTION_REPO_COLLECTION` | Collection of available landing page sections |
| `SECTION_REPO_METADATA_COLLECTION` | Section metadata collection |

### Optional

| Variable | Purpose | Default |
|----------|---------|---------|
| `GCP_PROJECT_ID` | GCP project for Secret Manager (staging/prod only) | — |
| `WWAI_AGENT_ORCHESTRATION_LOG_LEVEL` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |
| `WWAI_AGENT_ORCHESTRATION_SUPPRESS_INFO_LOGS` | Suppress INFO logs | `true` |
| `WWAI_AGENT_ORCHESTRATION_PERF_LOGS_ENABLED` | Enable performance timing logs | `false` |
| `WWAI_AGENT_ORCHESTRATION_ENABLE_PROMPT_TRACE` | Write prompts + responses to DB | `false` |

---

## Quick Start

**Mock mode** (no LLM calls, placeholder content):

```bash
# Run the full end-to-end workflow with lorem ipsum content
poetry run python pipeline/landing_page_demos/landing_page_demo.py \
    --business_id=660097b0-03df-42b5-b68e-5ccf18193b26 \
    --business_name="Bailey Plumbing"
```

> **`business_id`** is a UUID that identifies a business in MongoDB. In mock mode any UUID works — placeholder content is generated regardless of the ID. For real content mode you need a business with Google Maps/Yelp data already ingested into your MongoDB `businesses` database.

**Real content** (requires LLM API keys):

Edit `pipeline/landing_page_demos/utils.py` and change the `use_mock_autopopulation` default from `True` to `False` in `create_default_execution_config` (line 96). Then run the same command.

---

## Demo Scripts

All demo scripts share these common flags (defined in `pipeline/landing_page_demos/utils.py`):

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--business_id` | str | `"your-business-id-here"` | MongoDB business ID |
| `--business_name` | str | `"Your Business Name"` | Business display name |
| `--website_intention` | str | `"generate_leads"` | Website goal: `generate_leads`, `showcase`, etc. |
| `--website_tone` | str | `"professional"` | Tone: `professional`, `friendly`, etc. |

### `pipeline/landing_page_demos/landing_page_demo.py`

Full end-to-end workflow: business data extraction → template selection → autopopulation → HTML compilation.

```bash
poetry run python pipeline/landing_page_demos/landing_page_demo.py \
    --business_id=<BUSINESS_ID> \
    --business_name="<Business Name>"
```

**Output:** HTML file path (local) or S3 URL. Prints `Request ID: <uuid>` for use with partial autopop.

**Services:** MongoDB, Redis, OpenAI/Anthropic/Gemini (mock mode uses none), Node.js compiler, S3 (optional)

---

### `pipeline/landing_page_demos/template_selection_demo.py`

Runs template selection only (data collection + template generation + section retrieval). Stops before autopopulation.

```bash
poetry run python pipeline/landing_page_demos/template_selection_demo.py \
    --business_id=<BUSINESS_ID> \
    --business_name="<Business Name>"
```

**Output:** Template recommendations printed to stdout. No HTML generated.

---

### `pipeline/landing_page_demos/preset_sections_demo.py`

Skips template selection entirely. Runs autopopulation + HTML compilation from a predefined list of section IDs.

```bash
poetry run python pipeline/landing_page_demos/preset_sections_demo.py \
    --business_id=<BUSINESS_ID> \
    --business_name="<Business Name>"
```

---

### `pipeline/landing_page_demos/partial_autopop_demo.py`

Re-runs styles, text, or media autopopulation from an existing workflow checkpoint.

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--existing_request_id` | str | Yes | Request ID (generation_version_id) from a prior full workflow run |

```bash
poetry run python pipeline/landing_page_demos/partial_autopop_demo.py \
    --existing_request_id=<REQUEST_ID_FROM_FULL_WORKFLOW>
```

**Output:** Three updated HTML files — one each for styles, text, and media regeneration.

---

### `pipeline/landing_page_demos/create_non_homepage_demo.py`

Creates a non-homepage page (e.g. Services, Contact Us) by fetching body sections from the curated pages catalog and merging the parent homepage's header/footer.

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--homepage_generation_version_id` | str | Yes | Request ID of an existing homepage (from `landing_page_demo.py`) |
| `--curated_page_path` | str | No | Page path to generate (e.g. `services`, `contact`). Default: `services` |

```bash
# Step 1: generate a homepage first
poetry run python pipeline/landing_page_demos/landing_page_demo.py \
    --business_id=<BUSINESS_ID> \
    --business_name="<Business Name>"
# Note the printed Request ID

# Step 2: create a non-homepage using that homepage
poetry run python pipeline/landing_page_demos/create_non_homepage_demo.py \
    --homepage_generation_version_id=<REQUEST_ID_FROM_STEP_1> \
    --curated_page_path=services
```

---

### `pipeline/landing_page_demos/delete_section_demo.py`

Validates section deletion DB propagation. Removes a section at a given index from an existing generation.

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--existing_request_id` | str | Yes | Request ID of an existing generation |
| `--delete_index` | int | No | Index of the section to delete (default: 1) |

```bash
poetry run python pipeline/landing_page_demos/delete_section_demo.py \
    --existing_request_id=<REQUEST_ID> \
    --delete_index=2
```

---

### `pipeline/landing_page_demos/add_section_and_regenerate_demo.py`

Two-phase demo: inserts a new section at a given index then regenerates its content using AI.

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--existing_request_id` | str | Yes | Request ID of an existing generation |
| `--section_id` | str | No | Section template ID to insert |
| `--mode` | str | No | `"add_only"` or `"add_and_regenerate"` (default: `"add_and_regenerate"`) |

```bash
poetry run python pipeline/landing_page_demos/add_section_and_regenerate_demo.py \
    --existing_request_id=<REQUEST_ID>
```

---

## Programmatic API

All workflows are instantiated via the factory:

```python
from wwai_agent_orchestration.agent_workflows.landing_page_builder.workflows.workflow_factory import (
    LandingPageWorkflowFactory,
)
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_inputs import (
    LandingPageInput,
    build_stream_kwargs,
)
from wwai_agent_orchestration.contracts.landing_page_builder.execution_config import ExecutionConfig

# Create a workflow
workflow = LandingPageWorkflowFactory.create(
    mode="landing_page",
    config={"mongo_uri": "mongodb://localhost:27017/", "db_name": "checkpointing_db"},
)

# Build the input
workflow_input = LandingPageInput(
    request_id="<uuid>",
    business_name="My Business",
    business_id="<business-id>",
    # ... see LandingPageInput for all fields
)

execution_config = ExecutionConfig(use_mock_autopopulation=True)

# Stream events
async for stream_type, event in workflow.stream(
    **build_stream_kwargs(workflow_input, execution_config)
):
    print(stream_type, event)
```

**Filling in the placeholders:**
- `request_id`: generate with `str(uuid.uuid4())`. Must be unique per run — used as the LangGraph thread ID and MongoDB checkpoint key.
- `business_id`: any string works for mock mode. For real content, use a UUID that exists in your MongoDB `businesses` database with ingested Google Maps/Yelp data.

See `pipeline/landing_page_demos/landing_page_demo.py` for a complete working example.

---

## Eval CLI

The eval framework has a unified CLI exposed as a module:

```bash
python -m wwai_agent_orchestration.evals [global-args] <command> [command-args]
```

**Global args:**

| Flag | Default | Description |
|------|---------|-------------|
| `--store {local,mongo}` | `local` | Storage backend |
| `--local-store-dir DIR` | `.evals_local` | Dir for local JSONL store |
| `--mongo-uri URI` | — | MongoDB URI (when `--store=mongo`) |
| `--db-name NAME` | `eval` | MongoDB database name |

**Commands:**

### `build-set` — build an eval set without running it

```bash
python -m wwai_agent_orchestration.evals \
    --store local \
    build-set \
    --eval-set-id my_run_001 \
    --eval-type landing_page \
    --business-ids 660097b0-03df-42b5-b68e-5ccf18193b26 \
    --max-cases 5 \
    --output-json eval_set.json
```

### `run-set` — build and execute an eval set

```bash
python -m wwai_agent_orchestration.evals \
    --store mongo \
    --mongo-uri mongodb://localhost:27020/ \
    run-set \
    --eval-set-id my_run_001 \
    --eval-type landing_page \
    --business-ids 660097b0-03df-42b5-b68e-5ccf18193b26 \
    --max-concurrency 2 \
    --dry-run
```

### `resume` — re-run failed/running cases

```bash
python -m wwai_agent_orchestration.evals \
    --store mongo \
    --mongo-uri mongodb://localhost:27020/ \
    resume \
    --eval-set-id my_run_001 \
    --max-concurrency 2
```

**Supported eval types:** `landing_page`, `template_selection`, `section_coverage`, `color_palette`, `curated_pages`

---

## Scripts

```
scripts/
├── evals/                            # Eval harness convenience wrappers
│   ├── _real_data_common.py          # Shared constants and helpers
│   ├── run_landing_page_sample.py
│   ├── run_template_selection_sample.py
│   ├── run_section_coverage_sample.py
│   ├── run_color_palette_sample.py
│   └── run_curated_pages_sample.py
├── metrics/                          # Metrics computation and validation
│   ├── _common.py                    # Shared constants (collection names)
│   ├── compute_metrics.py
│   └── verify_metrics.py
└── human_feedback/                   # Reserved (currently empty)
```

All scripts:
- Use `absl.flags` for CLI argument parsing
- Call `load_dotenv()` at startup to read `.env`
- Must be run from the **project root** (not from within `scripts/`)
- Connect to MongoDB for both reading business data and storing results

> **MongoDB port:** Scripts default to port **27020** (`mongodb://localhost:27020/`), not the standard 27017 used by workflows. Override with `--mongo_uri` if your MongoDB runs on a different port.

---

## Eval Harness Scripts

Convenience wrappers around the eval CLI. Each script builds an eval set, executes it against real business data, and stores results in MongoDB.

### Common flags (all harness scripts)

| Flag | Default | Description |
|------|---------|-------------|
| `--mongo_uri` | `mongodb://localhost:27020/` | MongoDB URI |
| `--db_name` | `eval` | Eval storage database |
| `--sample_size` | `3` | Number of businesses to sample |
| `--eval_set_id` | auto-generated | Eval set ID (defaults to `{type}_sample_{timestamp}`) |
| `--max_concurrency` | `2` | Parallel case executions |
| `--max_attempts` | `1` | Retry attempts per case |
| `--seed` | `42` | Random seed for deterministic sampling |
| `--dry_run` | `False` | Skip execution, print summary only |
| `--dump_output_dir` | `None` | Directory to write debug output artifacts |

### `run_landing_page_sample.py`

Runs the full landing page eval on a sample of businesses.

```bash
poetry run python scripts/evals/run_landing_page_sample.py \
    --mongo_uri="mongodb://localhost:27020/" \
    --max_cases=1 \
    --dry_run
```

### `run_template_selection_sample.py`

Runs template selection eval (no HTML compilation). Optionally runs LLM-as-judge afterward.

```bash
poetry run python scripts/evals/run_template_selection_sample.py \
    --mongo_uri="mongodb://localhost:27020/" \
    --max_cases=1 \
    --dry_run
```

### `run_section_coverage_sample.py`

Evaluates section coverage using a fixed color palette.

| Flag | Default | Description |
|------|---------|-------------|
| `--business_id` | `"your-business-id-here"` | Business ID to eval |
| `--sample_size` | `10` | Number of businesses to sample |

```bash
poetry run python scripts/evals/run_section_coverage_sample.py \
    --business_id=660097b0-03df-42b5-b68e-5ccf18193b26 \
    --mongo_uri="mongodb://localhost:27020/" \
    --max_cases=1 \
    --dry_run
```

### `run_color_palette_sample.py`

Evaluates color palette generation across businesses.

```bash
poetry run python scripts/evals/run_color_palette_sample.py \
    --mongo_uri="mongodb://localhost:27020/" \
    --max_cases=1 \
    --dry_run
```

### `run_curated_pages_sample.py`

Evaluates non-homepage page generation against curated page definitions.

| Flag | Required | Description |
|------|----------|-------------|
| `--homepage_generation_version_id` | Yes | Request ID of an existing homepage |
| `--business_id` | No | Business ID to eval |
| `--curated_page_paths` | No | Comma-separated page paths to eval (e.g. `services,about`) |

```bash
poetry run python scripts/evals/run_curated_pages_sample.py \
    --business_id=660097b0-03df-42b5-b68e-5ccf18193b26 \
    --homepage_generation_version_id=<REQUEST_ID> \
    --mongo_uri="mongodb://localhost:27020/" \
    --max_cases=1 \
    --dry_run
```

---

## Metrics Scripts

### `scripts/metrics/compute_metrics.py`

Aggregates eval results into metrics (pass rate, scores by category, etc.) for a completed eval set.

| Flag | Required | Description |
|------|----------|-------------|
| `--eval_set_id` | Yes | Eval set to compute metrics for |
| `--task_name` | No | Filter to a specific judge task |

```bash
poetry run python scripts/metrics/compute_metrics.py \
    --eval_set_id=my_run_001 \
    --mongo_uri="mongodb://localhost:27020/"
```

### `scripts/metrics/verify_metrics.py`

Validates that metrics are within expected bounds and internally consistent.

```bash
poetry run python scripts/metrics/verify_metrics.py \
    --eval_set_id=my_run_001 \
    --mongo_uri="mongodb://localhost:27020/"
```

---

## Service Dependencies

| Service | Required For | Default |
|---------|-------------|---------|
| MongoDB | All workflows and evals | `mongodb://localhost:27017/` |
| Redis | LangGraph node cache | `localhost:6379` |
| Node.js compiler | HTML compilation (skipped in mock mode) | `http://localhost:3002` |

Start MongoDB and Redis with Docker:

```bash
docker run -d -p 27017:27017 mongo
docker run -d -p 6379:6379 redis
```

**Node.js compiler service:** The HTML compilation step requires a separate Node.js service that renders template JSON into final HTML. It is a companion service to this repo — refer to its README for setup instructions. Once running, it listens at `http://localhost:3002` by default (configurable via `NODE_SERVER_URL`).

If you are using mock mode (`use_mock_autopopulation=True`), HTML compilation is skipped and this service is not required.

---

## Logging

```python
from wwai_agent_orchestration.core.observability.logger import get_logger
logger = get_logger(__name__)
logger.info("message", key="value")  # structured JSON output
```

| Variable | Values | Default |
|----------|--------|---------|
| `WWAI_AGENT_ORCHESTRATION_LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |
| `WWAI_AGENT_ORCHESTRATION_SUPPRESS_INFO_LOGS` | `true`, `false` | `true` |
| `WWAI_AGENT_ORCHESTRATION_PERF_LOGS_ENABLED` | `true`, `false` | `false` |
