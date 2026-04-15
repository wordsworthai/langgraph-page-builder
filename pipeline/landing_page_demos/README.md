# SMB Workflow Demos

This directory contains demonstration scripts for all SMB workflow types. All demos use the factory pattern and workflow input dataclasses for consistency and type safety.

## Overview

The demos showcase different workflow types available in the SMB recommendation system:

1. **Full Workflow** - Complete end-to-end recommendation with HTML compilation
2. **Trade Classification** - Quick trade/industry classification
3. **Template Selection** - Template generation without autopopulation
4. **Preset Sections** - Build template from preset section IDs (bypass template selection)
5. **Partial Autopop** - Re-run specific parts of autopop (styles, text, or media)

## Prerequisites

- Python 3.8+
- Poetry (for dependency management)
- MongoDB running (configure `MONGO_CONNECTION_URI` in your `.env` — see `.env.example`)
- Required environment variables set (see `pipeline/env_utils.py`)

## Running Demos

All demos can be run using Poetry:

```bash
# Landing page workflow
poetry run python pipeline/landing_page_demos/landing_page_demo.py

# Trade classification demo
poetry run python pipeline/landing_page_demos/trade_classification_demo.py

# Template selection demo
poetry run python pipeline/landing_page_demos/template_selection_demo.py

# Preset sections demo
poetry run python pipeline/landing_page_demos/preset_sections_demo.py

# Partial autopop demo
poetry run python pipeline/landing_page_demos/partial_autopop_demo.py
```

## Demo Details

### Landing Page Demo (`landing_page_demo.py`)

Demonstrates the complete SMB recommendation workflow:
- Business data extraction
- Template generation
- Section retrieval
- Autopopulation
- HTML compilation

**Expected Output:**
- Generated templates
- Retrieved sections
- Compiled HTML URL

### Trade Classification Demo (`trade_classification_demo.py`)

Demonstrates quick trade/industry classification:
- Business data extraction
- Trade classification

**Expected Output:**
- Trade classification results
- Sector information

### Template Selection Demo (`template_selection_demo.py`)

Demonstrates template generation without autopopulation:
- Business data extraction
- Template generation
- Section retrieval
- Stops before autopopulation

**Expected Output:**
- Generated templates
- Retrieved sections
- No HTML compilation (stops before autopop)

### Preset Sections Demo (`preset_sections_demo.py`)

Demonstrates building a landing page from preset section IDs:
1. Takes a list of section IDs directly
2. Fetches sections from the repo
3. Runs autopopulation and post-processing
4. Outputs HTML URL

**Expected Output:**
- Compiled HTML URL from preset sections

### Partial Autopop Demo (`partial_autopop_demo.py`)

Demonstrates partial regeneration of specific components:
1. Runs a full workflow to create a base template
2. Runs PartialAutopopWorkflow in 3 modes:
   - **styles**: Regenerate styles only (with different palette)
   - **text**: Regenerate text content only
   - **media**: Regenerate images/media only
3. Outputs HTML URLs for all 4 versions for comparison

**Expected Output:**
- Four HTML URLs (base + 3 partial regenerations)
- Validation checklist for each mode

## Shared Utilities

All demos use shared utilities from `pipeline/demo/utils.py`:

### Configuration Helpers
- `setup_environment()` - Environment variable setup
- `setup_workflow_config()` - Workflow configuration creation
- `get_default_business_config()` - Default business settings
- `get_default_mongo_config()` - Default MongoDB settings
- `create_default_execution_config()` - Execution config creation

### Workflow State Helpers
- `get_html_url_from_state()` - Extract HTML URL from state
- `get_workflow_state()` - Get full workflow state

### Printing Helpers
- `print_workflow_header()` - Consistent header printing
- `print_workflow_results()` - Display workflow results

### Execution Helpers
- `run_workflow_stream()` - Generic workflow streaming with progress

### Partial Autopop Helpers
- `get_id_idx_to_unique_section_id_map()` - Extract section ID mapping

## Common Patterns

All demos follow a consistent structure:

1. **Environment Setup** - Using `setup_environment()`
2. **Configuration Setup** - Using `setup_workflow_config()` and config helpers
3. **Workflow Creation** - Using `LandingPageWorkflowFactory.create()`
4. **Input Creation** - Using workflow input dataclasses
5. **Stream Kwargs** - Using `build_stream_kwargs()`
6. **Workflow Execution** - Using `run_workflow_stream()`
7. **Results Display** - Using `print_workflow_results()`

### Example Pattern

```python
# 1. Setup
setup_environment()
workflow_config = setup_workflow_config()
business_config = get_default_business_config()

# 2. Create workflow using factory
workflow = LandingPageWorkflowFactory.create("landing_page", config=workflow_config)

# 3. Create input using dataclass
workflow_input = LandingPageInput(
    business_name=business_config["business_name"],
    # ... other fields
)

# 4. Build stream kwargs
stream_kwargs = build_stream_kwargs(workflow_input)

# 5. Run workflow
await run_workflow_stream(workflow, stream_kwargs)

# 6. Display results
print_workflow_results(workflow, request_id, workflow_config)
```

## Customization

To customize demos:

1. **Change Business**: Modify `get_default_business_config()` in `utils.py` or pass custom config
2. **Change Palette/Font**: Modify the index in `get_color_palette_and_font(index=X)`
3. **Change MongoDB**: Modify `get_default_mongo_config()` in `utils.py` or pass custom config

## Troubleshooting

- **No state found**: Ensure MongoDB is running and checkpointing is enabled
- **Import errors**: Ensure all dependencies are installed via `poetry install`
- **Environment errors**: Check that required environment variables are set (see `pipeline/env_utils.py`)
