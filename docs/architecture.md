# Architecture

`wwai-agent-orchestration` is a LangGraph-based AI agent orchestration system that takes business information (name, brand, website intent) and produces a fully populated HTML landing page by running a multi-phase pipeline of LLM agents, data providers, and a template rendering service. The system is organized around four major subsystems: the **pipeline graph** (LangGraph workflows and nodes), a **data layer** (providers, repositories, and LLM tools), an **eval framework** (deterministic test sets, runners, judges, and metrics), and **scripts** for driving evals and metrics from the command line.

---

## Pipeline

```
Business Input (name, brand, intent)
        |
        v
  [ Data Collection ]
  business_data_extractor       <- Google Maps, Yelp, internal DB
  campaign_intent_synthesizer   <- LLM: synthesize campaign brief
  trade_classifier              <- LLM: classify business industry (async)
        |
        v
  [ Template Selection ]
  cache_lookup                  <- Redis: check for cached recommendations
        |
        +-- cache hit --> save_template_sections
        |
        +-- cache miss -->
              section_repo_fetcher          <- MongoDB: fetch available sections
              generate_template_structures  <- LLM: generate 3 template layouts
              [optional reflection loop]    <- LLM: evaluate + refine templates
              resolve_template_sections     <- LLM: map layouts to real sections (parallel)
              cache_template_recommendations <- Redis: persist recommendations
        |
        v
  [ Autopopulation ]  (4 parallel pipelines)
  +--> Styles:   container_color -> text_color / button_color / misc_color -> semantic_names
  +--> Text:     content_text_fanout -> per-section LLM agents -> collect
  +--> Media:    media_fanout -> per-section matching -> collect
  +--> HTML:     per-section HTML generation
        |
        v  (AND-join: all 4 pipelines must complete)
  [ Post-Processing ]
  template_compilation    <- compile template JSON
  html_compilation        <- Node.js service: render HTML
  screenshot_capture      <- optional
        |
        v
  Output: HTML file (local path or S3 URL)
```

---

## Workflow Modes

All workflows are instantiated via `LandingPageWorkflowFactory.create(mode, config)`.

| Mode | Workflow | What it runs |
|------|----------|-------------|
| `"landing_page"` | `LandingPageWorkflow` | Full pipeline end-to-end |
| `"template_selection"` | `TemplateSelectionWorkflow` | Data collection + template selection only (no content) |
| `"preset_sections"` | `PresetSectionsLandingPageWorkflow` | Skip template selection; use provided section IDs directly |
| `"partial_autopop"` | `PartialAutopopWorkflow` | Re-run styles, text, or media from a saved checkpoint |
| `"regenerate_section"` | `RegenerateSectionWorkflow` | Regenerate one section at a specific index |
| `"trade_classification"` | `TradeClassificationWorkflow` | Business industry classification only |

---

## Core Abstractions

| Name | Module | Role |
|------|--------|------|
| `LandingPageWorkflowState` | `contracts/landing_page_builder/workflow_state.py` | Pydantic model that IS the LangGraph state. Fields use `Annotated[T, reducer]` to specify merge semantics: `stage_merge_reducer` (partial update), `deep_merge_reducer` (recursive dict merge), `operator.add` (list append). Every node reads from and writes to this model. |
| `BaseLandingPageWorkflow` | `agent_workflows/.../workflows/base_workflow.py` | ABC requiring `_build_graph() -> StateGraph`. Provides checkpointing, caching, streaming, and resume logic shared by all workflow variants. |
| `LandingPageWorkflowFactory` | `agent_workflows/.../workflows/workflow_factory.py` | Factory: maps a mode string to the correct workflow class. The only constructor for all workflow types. |
| `NodeFunction` | `nodes/base.py` | Protocol `(state, config) -> dict`. The universal signature every graph node must implement. Return value is a partial state update — never mutate state directly. |
| `NodeRegistry` | `core/registry/node_registry.py` | Decorator-based singleton. `@NodeRegistry.register(...)` attaches display name, retry strategy, and UI visibility metadata. Does not control execution flow — that is LangGraph wiring. |
| `ExecutionConfig` | `contracts/landing_page_builder/execution_config.py` | Nested Pydantic config composed of `CacheStrategy`, `RoutingConfig`, `CompilationConfig`, `ReflectionConfig`, `AutopopConfig`. Per-request. Nodes branch on these flags to skip or enable pipeline stages. |
| `PromptSpec` | `prompt_builder/prompt_builder.py` | Declarative LLM call pattern: subclass, set `PROMPT_NAME` / `InputModel` / `OutputModel`, call `execute()`. Handles prompt loading, template variable injection, LLM call, and Pydantic output validation. |
| `BaseProvider` | `data/connectors/base_mongo_provider.py` | Base class for all data providers. Wraps the global `db_manager` with common query methods (`find_one`, `find_many`, `upsert_one`, `update_one`). |
| `EvalStore` | `evals/stores/interfaces.py` | `@runtime_checkable` Protocol for eval artifact persistence. Two concrete implementations: `MongoEvalStore` (production) and `LocalJsonlEvalStore` (local dev). |
| `BaseJudgeTask` / `BaseJudgeTaskInstance` | `evals/judges/base.py` | Two-layer ABC for LLM-as-judge evaluation. `BaseJudgeTask` handles versioned prompt loading; `BaseJudgeTaskInstance` defines per-run `build_input()`, `build_output_for_eval()`, `parse_llm_response()`. |

---

## Data Flow

| Phase | Input | Output |
|-------|-------|--------|
| **Data Collection** | `UserInput` (business name, query, page_url, yelp_url) | `DataCollectionResult` — `business_info`, `google_maps_data`, `yelp_data`, `derived_sector`, `campaign_intent` |
| **Template Selection** | `DataCollectionResult` + section repository from MongoDB | `TemplateResult` — `templates` (3 layout dicts), `resolved_template_recommendations` (sections mapped to each template) |
| **Autopopulation** | `TemplateResult` + `BrandContext` (palette, font) + business data | `autopopulation_langgraph_state` — color assignments, text content, media assets, HTML fragments per section |
| **Post-Processing** | Autopopulated template state | `PostProcessResult` — `template_compilation_results`, `html_compilation_results` (S3 URL or local path), optional `screenshot_capture_results` |

---

## Caching

Two independent Redis caching layers:

**1. Node-level cache (LangGraph `BaseCache`)**
Nodes declare a `CachePolicy` with a deterministic key function. Results are cached for 60 days. Cached nodes: `business_data_extractor`, `campaign_intent_synthesizer`, `section_repo_fetcher`, `generate_template_structures`, `resolve_template_sections_from_repo`. Per-node caching can be disabled via `ExecutionConfig.cache_strategy`.

**2. Template recommendation cache**
`cache_lookup_template_recommendations` checks Redis for previously generated section recommendations keyed on business + workflow config. On a cache hit, the entire template generation subgraph is bypassed via a conditional edge.

Additionally, MongoDB checkpointing persists full workflow state per `request_id`, enabling fault-tolerant resume and the `partial_autopop` / `regenerate_section` workflow modes.

---

## Error Handling and Retry

- `NodeRegistry` stores `max_retries` and `RetryStrategy` (NONE, SIMPLE, EXPONENTIAL) per node as metadata. This is consumed by the workflow execution layer — the registry itself does not execute retries.
- `BaseProvider` methods (`find_one`, `find_many`, `upsert_one`) catch exceptions, log, and return empty/None/False — fail-soft by default.
- LangGraph checkpointing enables resume-from-failure at the graph level: `partial_autopop` and `regenerate_section` modes pick up from a saved checkpoint without re-running completed phases.
- The eval batch runner retries at the case level via `max_attempts` with bounded concurrency.

---

## Data Layer

The `data/` package provides business data retrieval, transformation, and LLM tool exposure. It is organized in four layers:

```
LLM Agent → data/tools/ → data/providers/ → data/repositories/ → MongoDB
                                           → data/providers/utils/ (parsers)
                                           → External APIs (Yelp, ScrapingBee, Gemini)
data/services/media/ → data/providers/
```

| Layer | Location | Responsibility |
|-------|----------|----------------|
| **Repositories** | `data/repositories/` | Pure MongoDB access. `business_data_storage` (module-level functions), `SectionRepositoryService`, `TradesRepositoryService`. No external API calls. |
| **Providers** | `data/providers/` | Data fetching + transformation. Most extend `BaseProvider` from `data/connectors/`. Transform raw data via parser utilities in `data/providers/utils/`. |
| **Services** | `data/services/media/` | Multi-step orchestration. `MediaService` coordinates `MediaProviderClient` → `MediaAssetMatcher` (source-weighted scoring) → `transformer` (format conversion). |
| **Tools** | `data/tools/` | LLM-callable surface. Five OpenAI function-calling schemas in `definitions.py`, routed through `executor.py`. |

### Provider categories

| Category | Providers | Pattern |
|----------|-----------|---------|
| DB-only | `GoogleMaps`, `BusinessProfile`, `Reviews`, `BusinessPhotos`, `ReviewPhotos`, `MediaAssets`, `Logo` | Read from MongoDB `businesses.*` or `media_management.media`, normalize via parser utils |
| External API | `WebScraping` (ScrapingBee), `Gemini` | Call external service, return structured Pydantic result |
| Hybrid | `Yelp` | DB lookup first; on miss, calls Yelp RapidAPI, upserts result to DB, then transforms |
| Facade | `TradesCatalog`, `SectionCatalog`, `TradeClassification` | Thin wrappers over a repository service; do not extend `BaseProvider` |

### LLM tools

Five tools are defined as OpenAI function-calling schemas and dispatched through `data/tools/executor.py`:
`get_business_profile`, `get_reviews`, `get_media_assets`, `scrape_website`, `analyze_page_intent`.

### Contracts and parsers

- Pydantic input/output models: `data/providers/models/`
- Parser utilities (pure, stateless): `data/providers/utils/` — `google_maps_parser.py`, `yelp_parser.py`, `scraper/`

> **Note:** `data/media/` (`gemini_service`, `media_service`, `variation_service`) is a FastAPI-oriented subsystem that uses `app.*` imports and async MongoDB. It is architecturally separate from the LangGraph pipeline and is not used by any workflow node.

---

## Eval Framework

The `evals/` package provides deterministic evaluation of workflow outputs, from test set generation through LLM judging and metrics aggregation.

### Core types

| Type | Module | Purpose |
|------|--------|---------|
| `EvalCase` | `evals/types/eval_case.py` | Immutable test input. `case_id` is a deterministic SHA-256 hash of the case content — the same inputs always produce the same ID. |
| `EvalSet` | `evals/types/eval_set.py` | Ordered collection of `EvalCase` objects with `eval_set_id`, `version`, and `seed`. |
| `RunRecord` | `evals/types/run_record.py` | One execution attempt. Tracks `run_id`, `status` (created / running / completed / failed), `duration_ms`, `attempt`, and `error_message`. |

### Storage

`EvalStore` is a `@runtime_checkable` Protocol with two implementations:
- `LocalJsonlEvalStore` — append-only JSONL files under a local directory (for development)
- `MongoEvalStore` — MongoDB with upserts across four collections (`eval_sets`, `eval_runs`, `eval_outputs`, `eval_judge_results`)

### Eval set builders

`evals/sets/factory.py` dispatches `build_eval_set(eval_type, ...)` to one of five type-specific builders:

| Eval type | What it builds |
|-----------|---------------|
| `landing_page` | One case per business (full end-to-end) |
| `template_selection` | Business × website-purpose cross-product |
| `section_coverage` | Batches of sections ensuring every section is covered at least once |
| `color_palette` | Same template + business, varying only color palette |
| `curated_pages` | Non-homepage pages from the `curated_pages` catalog |

### Runner pipeline

`evals/runners/workflow_runner.py` — `run_case()` flow for a single eval case:

1. Create `RunRecord` with `status=running`, persist to store
2. `workflow_executor` calls `LandingPageWorkflowFactory.create(mode)` and streams the workflow to completion
3. `CheckpointReader` reads final state and history from the graph checkpoint
4. `ExtractorRegistry` resolves the correct `BaseOutputExtractor` for the workflow mode (three extractors: `LandingPage`, `TemplateSelection`, `PresetSections`) and produces a typed output
5. Optional: `judge_evaluator` scores the output via LLM
6. `RunRecord` updated to `completed` or `failed` with duration and error

`evals/runners/batch_runner.py` runs all cases concurrently using `asyncio.Semaphore(max_concurrency)` with per-case retry up to `max_attempts`.

### Judge system

`BaseJudgeTask` loads versioned prompt templates (`.txt` with `===SYSTEM===` / `===USER===` markers). `BaseJudgeTaskInstance` builds input/output JSON and parses the LLM response. `JudgeRunner` dispatches to `OpenAIJudgeProvider` or `AnthropicJudgeProvider`, both async with retry.

The only currently implemented judge task is `TemplateEvalJudgeTask`, which evaluates section selection against intent-specific guidelines defined in `evals/judges/tasks/landing_page_builder/template_eval/guidelines.py`.

### Metrics

`MetricsService` in `evals/metrics/service.py` is a registry that maps task types to metric functions. `generic_metrics()` computes pass rates (AI and human), human-AI agreement, and coverage. Task-specific functions extend these with domain metrics.

### Human feedback

`evals/human_feedback/` provides a taxonomy system for structured feedback collection, KPI derivation, and MongoDB-backed feedback storage. Taxonomy schemas are defined per task type in `evals/human_feedback/taxonomy/landing_page_builder/`.

---

## External Services

| Service | Purpose |
|---------|---------|
| **MongoDB** | Workflow state checkpointing, business data storage, section repository, generation records, eval artifacts |
| **Redis** | Node result cache (LangGraph `BaseCache`), template recommendation cache |
| **OpenAI** | LLM for template generation, campaign intent, content autopopulation, color agents. Default model: `gpt-4.1` |
| **Anthropic** | Alternative LLM provider; eval judge |
| **Google Gemini** | URL page context extraction; alternative LLM provider |
| **Google Maps / Places** | Business data (location, hours, photos, rating, reviews) |
| **Yelp (RapidAPI)** | Business details and reviews |
| **AWS S3** | Compiled HTML uploads, media file storage, screenshots |
| **GCP Secret Manager** | API key and DB credential retrieval in non-local environments |
| **Node.js Compiler** | Renders template JSON into final HTML (local service, default: `http://localhost:3002`) |
