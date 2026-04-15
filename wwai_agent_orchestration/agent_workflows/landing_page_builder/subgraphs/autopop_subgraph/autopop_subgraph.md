# Autopopulation Subgraph Documentation

## Overview

The autopopulation subgraph handles the autopopulation workflow within the SMB recommendation graph. It processes template sections through multiple stages: color autopopulation, semantic naming, and content generation (text, images, videos).

## Graph Structure

### High-Level Flow

After `autopopulation_input_builder`, three pipelines run **in parallel**:

```
autopop_start → autopopulation_input_builder
  ├─→ [Styles Pipeline - Sequential]
  │     S1_agent_container_color → S1_materialize
  │     → S2_agent_element_colors → S2_materialize
  │     → S3_agent_semantic_names → S3_materialize
  │     → final_materialize
  │
  └─→ [Content Planning]
        content_planner
        ├─→ [Content Text Pipeline - Parallel Sections]
        │     S4_agent_content_text_router
        │     → [FAN-OUT: parallel S4_agent_content_text_section nodes]
        │     → S4_agent_content_text_collect → S4_materialize
        │     → final_materialize
        │
        └─→ [Content Media Pipeline - Parallel Sections]
              S5_agent_content_media_router
              → [FAN-OUT: parallel S5_agent_content_media_section nodes]
              → S5_agent_content_media_collect → S5_materialize
              → final_materialize
              → autopop_end
```

**Note**: 
- Styles pipeline and content planner run in parallel after `autopopulation_input_builder`
- Content text and media pipelines run in parallel after `content_planner`
- All pipelines converge at `final_materialize`, which waits for all pipelines to complete before creating the final snapshot

### Key Design Decisions

1. **Styles Pipeline (S1→S2→S3)**: Runs sequentially because:
   - S2 depends on S1 (element colors need container colors)
   - S3 can run after S2 (semantic names don't strictly need colors, but keeps styles together)
   - These are style-related and logically grouped

2. **Content Planner**: Sits above both content pipelines because:
   - Provides unified planning for text and media content
   - Allows shared context and strategy between text and media generation
   - Currently a placeholder for future implementation

3. **Content Pipelines (S4, S5)**: Run in parallel with each other after content planner because:
   - Both receive planning context from `content_planner`
   - Text and media content generation are independent operations
   - Maximum parallelization for better performance

4. **Convergence**: All pipelines converge at `final_materialize`, which creates a complete snapshot before `autopop_end`

## Node Details

### Entry/Exit Nodes

#### `autopop_start`
- **Type**: Entry node (dummy pass-through)
- **Purpose**: Entry point for the autopopulation subgraph
- **Returns**: Empty dict (pass-through)

#### `autopopulation_input_builder`
- **Type**: Transform node
- **Purpose**: Builds LangGraph input state from LandingPageWorkflowState
- **Key Operations**:
  - Extracts autopopulation context from LandingPageWorkflowState
  - Initializes AutopopulationLangGraphAgentsState
  - Stores immutable state reference

#### `autopop_end`
- **Type**: Exit node (dummy pass-through)
- **Purpose**: Exit point for the autopopulation subgraph
- **Returns**: Empty dict (pass-through)

### Stage 1: Container Color (S1)

#### `S1_agent_container_color`
- **Type**: Agent node
- **Purpose**: Autopopulate container/section background colors
- **Module**: `CONTAINER_COLOR`
- **Processing**: Template-level (all sections at once)
- **Output**: Background color recommendations for all sections

#### `S1_materialize`
- **Type**: Materialize node
- **Purpose**: Create snapshot of container color autopopulation results
- **Label**: `S1_container_color`

### Stage 2: Element Colors (S2)

#### `S2_agent_element_colors`
- **Type**: Agent node (sequential processing)
- **Purpose**: Autopopulate element colors (text, button, misc) based on background colors
- **Modules**: 
  - `ELEMENT_TEXT_COLOR`
  - `ELEMENT_BUTTON_COLOR`
  - `ELEMENT_MISC_COLOR`
- **Processing**: Sequential calls to three agent modules, then merge results
- **Dependencies**: Requires `S1` output (container colors)
- **Output**: Color recommendations for text, button, and misc elements

#### `S2_materialize`
- **Type**: Materialize node
- **Purpose**: Create snapshot of element color autopopulation results
- **Label**: `S2_element_colors`

### Stage 3: Semantic Names (S3)

#### `S3_agent_semantic_names`
- **Type**: Agent node
- **Purpose**: Autopopulate semantic names for elements
- **Module**: `SEMANTIC_NAME`
- **Processing**: Template-level (all sections at once)
- **Output**: Semantic name mappings for all elements

#### `S3_materialize`
- **Type**: Materialize node
- **Purpose**: Create snapshot of semantic name autopopulation results
- **Label**: `S3_semantic_names`

### Content Planning Stage

#### `content_planner`
- **Type**: Planning node (currently pass-through)
- **Purpose**: Plans content generation strategy for both text and media pipelines
- **Current Implementation**: Empty pass-through node (placeholder for future implementation)
- **Future**: Will implement content planning logic that feeds into both S4 and S5
- **Output**: Will provide planning context for content generation

### Stage 4: Content Text (S4) - Parallelized

#### `S4_agent_content_text_router`
- **Type**: Router node (dummy pass-through)
- **Purpose**: Entry point before fan-out to parallel section nodes
- **Returns**: Empty dict

#### `S4_agent_content_text_fanout`
- **Type**: Conditional edge function
- **Purpose**: Spawns parallel section content text nodes
- **Behavior**:
  - Resolves immutable state
  - Gets list of section IDs
  - Creates a `Send()` for each section with all necessary data
  - Returns list of `Send` objects for parallel execution

#### `S4_agent_content_text_section`
- **Type**: Agent node (runs in parallel, one per section)
- **Purpose**: Autopopulate text content for a single section
- **Module**: `CONTENT_TEXT`
- **Processing**: Section-level (one section at a time, multiple sections in parallel)
- **State Handling**: 
  - Receives Send payload as entire state (per GRAPH_DOCUMENTATION.md)
  - Extracts section_id and shared data from payload
  - Reconstructs immutable state from payload
- **Output**: Text content for the specific section
- **Parallel Execution**: Multiple instances run simultaneously, one per section

#### `S4_agent_content_text_collect`
- **Type**: Collect node
- **Purpose**: Aggregates results from all parallel section nodes
- **Behavior**: 
  - Results are automatically merged by LangGraph's state reducer
  - Updates metadata to indicate completion

#### `S4_materialize`
- **Type**: Materialize node
- **Purpose**: Create snapshot of content text autopopulation results
- **Label**: `S4_content_text`

### Stage 5: Content Media (S5) - Parallelized

#### `S5_agent_content_media_router`
- **Type**: Router node (dummy pass-through)
- **Purpose**: Entry point before fan-out to parallel section nodes
- **Returns**: Empty dict

#### `S5_agent_content_media_fanout`
- **Type**: Conditional edge function
- **Purpose**: Spawns parallel section media content nodes
- **Behavior**:
  - Resolves immutable state
  - Gets list of section IDs
  - Creates a `Send()` for each section with all necessary data
  - Returns list of `Send` objects for parallel execution

#### `S5_agent_content_media_section`
- **Type**: Agent node (runs in parallel, one per section)
- **Purpose**: Autopopulate both image and video content for a single section
- **Modules**: 
  - `CONTENT_IMAGE`
  - `CONTENT_VIDEO`
- **Processing**: Section-level (one section at a time, multiple sections in parallel)
- **State Handling**: 
  - Receives Send payload as entire state (per GRAPH_DOCUMENTATION.md)
  - Extracts section_id and shared data from payload
  - Reconstructs immutable state from payload
- **Output**: Both image and video content for the specific section
- **Parallel Execution**: Multiple instances run simultaneously, one per section

#### `S5_agent_content_media_collect`
- **Type**: Collect node
- **Purpose**: Aggregates results from all parallel section nodes
- **Behavior**: 
  - Results are automatically merged by LangGraph's state reducer
  - Updates metadata to indicate completion

#### `S5_materialize`
- **Type**: Materialize node
- **Purpose**: Create snapshot of content media autopopulation results
- **Label**: `S5_content_media`

### Final Materialize Node

#### `final_materialize`
- **Type**: Materialize node
- **Purpose**: Create final complete snapshot after all pipelines (styles, text, media) have converged
- **Label**: `final_autopopulation`
- **Behavior**:
  - Waits for all three pipelines to complete (S3_materialize, S4_materialize, S5_materialize)
  - Creates a complete snapshot with all autopopulation results merged
  - Runs just before `autopop_end`

## Parallel Execution Patterns

### Three-Level Parallelization

The subgraph achieves maximum parallelization through three independent pipelines:

1. **Styles Pipeline** (S1→S2→S3): Sequential within pipeline, but runs in parallel with content pipelines
2. **Content Text Pipeline** (S4): Parallel sections, runs in parallel with styles and media
3. **Content Media Pipeline** (S5): Parallel sections, runs in parallel with styles and text

### Fan-Out Pattern (S4 and S5)

Both S4 (content text) and S5 (content media) use the same parallel execution pattern:

1. **Router Node**: Dummy node that passes through
2. **Fan-Out Function**: Conditional edge that returns list of `Send()` objects
3. **Parallel Section Nodes**: Multiple instances run simultaneously
4. **Collect Node**: Aggregates results from all parallel nodes

### Pipeline Independence

- **Styles Pipeline**: Independent - doesn't need content results
- **Content Text Pipeline**: Independent - doesn't need styles or media
- **Content Media Pipeline**: Independent - doesn't need styles or text

This allows all three pipelines to start simultaneously after `autopopulation_input_builder`.

### State Handling with Send()

According to `GRAPH_DOCUMENTATION.md`, when using `Send()`:
- The Send payload becomes the node's **entire state**
- All necessary data must be included in each `Send()` payload
- No access to global state - only what's in the payload

**Key Data Included in Send Payloads**:
- `section_id`: The section to process
- `brand_url`: Brand context
- `entity_url`: Entity context
- `content_providers_tools_response` / `media_providers_tools_response`: Provider data
- `use_mock`: Mock flag
- `bypass_prompt_cache`: Cache bypass flag
- `immutable_ref`: Reference to immutable state
- `meta`: Metadata

## State Management

### State Structure

The subgraph works with `LandingPageWorkflowState` which contains:
- `autopopulation_langgraph_state`: The autopopulation-specific state

### State Updates

Each node returns updates in the format:
```python
{
    "autopulation_langgraph_state": {
        "agent_inputs": {...},
        "agent_outputs": {...},
        "logs": [...],
        "meta": {...}
    }
}
```

### State Merging

- **Sequential nodes**: Updates are merged sequentially
- **Parallel nodes**: LangGraph's state reducer automatically merges results from all parallel section nodes
- **Agent inputs/outputs**: Merged by module name and section ID

## Module Types

The subgraph processes the following autopopulation modules:

1. **CONTAINER_COLOR**: Section background colors
2. **ELEMENT_TEXT_COLOR**: Text element colors
3. **ELEMENT_BUTTON_COLOR**: Button element colors
4. **ELEMENT_MISC_COLOR**: Miscellaneous element colors
5. **SEMANTIC_NAME**: Element semantic names
6. **CONTENT_TEXT**: Text content for sections
7. **CONTENT_IMAGE**: Image content for sections
8. **CONTENT_VIDEO**: Video content for sections

## Performance Characteristics

### Pipeline-Level Parallelization

After `autopopulation_input_builder`, two main paths run simultaneously:
- **Styles Pipeline**: S1 (5s) → S2 (8s) → S3 (3s) = **16s total**
- **Content Planning Path**: content_planner → [S4 and S5 in parallel]
  - **Content Text Pipeline**: Max of all section processing times
  - **Content Media Pipeline**: Max of all section processing times

**Overall time**: `max(styles_pipeline_time, content_planner_time + max(text_pipeline_time, media_pipeline_time))`

### Section-Level Parallelization (S4 and S5)

Within the content pipelines, sections are processed in parallel:
- **Sequential (old)**: 10s + 10s + 10s = 30s total
- **Parallel (new)**: max(10s, 10s, 10s) = 10s total

### Combined Performance Improvement

**Example with 3 sections:**
- **Old Structure** (fully sequential):
  - S1 (5s) + S2 (8s) + S3 (3s) + S4 (30s) + S5 (30s) = **76s total**
  
- **New Structure** (pipeline + section parallelization):
  - Styles: 16s
  - Text: 10s (parallel sections)
  - Media: 10s (parallel sections)
  - **Total: max(16s, 10s, 10s) = 16s**

**Performance gain: ~4.75x faster** (76s → 16s)

## Dependencies

### Pipeline Dependencies

**Styles Pipeline (Sequential)**:
- S2 depends on S1 (element colors need container colors)
- S3 can run after S2 (keeps styles logically grouped)

**Content Pipelines (Independent)**:
- S4 (text) and S5 (media) are **independent** of styles and each other
- Both can start immediately after `autopopulation_input_builder`
- No dependencies between content pipelines

### Data Dependencies
- All pipelines depend on `autopopulation_input_builder` for immutable state
- Parallel section nodes depend on router nodes for shared data preparation
- All pipelines converge at `autopop_end` (no data dependencies between pipelines)

## Error Handling

- Missing immutable state: Raises `ValueError` or `RuntimeError`
- Missing section_id in Send payload: Raises `ValueError`
- Store not found: Raises `RuntimeError` with helpful message

## Materialization

Each stage has a materialize node that:
- Creates a snapshot of the current state
- Stores results in the immutable store
- Updates metadata for tracking
- Includes a 2-second delay for frontend observation
