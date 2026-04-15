# SMB Recommendation Workflow - Graph Documentation

## Overview

The SMB Recommendation Workflow is a LangGraph-based orchestration system that generates website recommendations for small and medium businesses. It supports multiple execution paths (preset/forms vs. agent-generated) and includes optional reflection loops for template refinement.

---

## Function Return Types & State Management

### Node Functions vs Conditional Edge Functions

LangGraph uses two different function types with different return value expectations:

#### 1. **Node Functions** (Return State Updates)
- **Signature**: `def node_function(state: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]`
- **Return Type**: `Dict[str, Any]` - State updates to merge into workflow state
- **Purpose**: Execute business logic and update workflow state
- **Example**:
  ```python
  def business_data_extractor_node(state, config):
      return {
          "business_info": {...},
          "google_data_valid": True
      }
  ```
- **Behavior**: Returned dict is merged with current state using state schema reducers

#### 2. **Conditional Edge Functions** (Return Route Names)
- **Signature**: `def routing_function(state: StateType) -> str`
- **Return Type**: `str` - Route name that maps to a node in the routing dictionary
- **Purpose**: Make routing decisions based on current state
- **Example**:
  ```python
  def finalize_template_generation_reflect_or_section_retrieval(state):
      if not state.enable_reflection:
          return "section_retrieval"  # Route name (not state update!)
      return "evaluation"
  ```
- **Behavior**: 
  - State is **automatically passed** to the next node (no need to return it)
  - Returns a string key that maps to the next node name
  - Used in `graph.add_conditional_edges()` routing dictionary

### Send() and Parallel Execution (Fan-Out)

When using `Send()` for parallel execution (fan-out pattern), state handling works differently:

#### Initial Dispatch (Map Phase)
- **Behavior**: When you return `Send("node_name", {"key": "value"})`, the target node receives **ONLY that dictionary** as its input state
- **Important**: The dictionary you provide is **NOT merged** with the global state - it becomes the node's entire state
- **Implication**: If you want the node to have access to parts of the global state, you must manually include them:
  ```python
  # ✅ Correct: Include needed state fields manually
  Send("resolve_template_sections_from_repo", {
      "template": template,
      "section_repo": section_repo,  # ← Included manually
      "campaign_intent": campaign_intent,  # ← Included manually
      "business_name": business_name,
      "industry": sector
  })
  
  # ❌ Wrong: Node won't have access to section_repo
  Send("resolve_template_sections_from_repo", {"template": template})
  ```

#### Parallel Isolation
- Each node instance runs in its own isolated "branch" with its own version of the state
- Updates made by one parallel node are **NOT visible** to others during parallel execution
- Each parallel execution is completely independent

#### Re-merging (Reduce Phase)
- After all parallel nodes finish, LangGraph uses **Reducers** defined in your state schema to merge results
- Reducers are specified using `Annotated` types in the state schema:
  ```python
  # In LandingPageWorkflowState
  resolved_template_recommendations: Annotated[List[Dict[str, Any]], operator.add] = Field(
      default_factory=list,
      description="Results from parallel section_retriever nodes"
  )
  ```
- The `operator.add` reducer concatenates lists from all parallel executions
- Final state merge happens automatically after all parallel nodes complete

#### Example Flow (Fan-Out/Fan-In)
```
section_retrieval (router node)
    ↓
fan_out_to_section_retrievers() returns:
    [
        Send("resolve_template_sections_from_repo", {template: t1, section_repo: repo, ...}),
        Send("resolve_template_sections_from_repo", {template: t2, section_repo: repo, ...}),
        Send("resolve_template_sections_from_repo", {template: t3, section_repo: repo, ...})
    ]
    ↓
[Parallel Execution - 3 isolated branches]
    ↓
Each resolve_template_sections_from_repo returns:
    {"resolved_template_recommendations": [result1]}
    {"resolved_template_recommendations": [result2]}
    {"resolved_template_recommendations": [result3]}
    ↓
[Reduce Phase - Automatic merging]
    ↓
Final state: {"resolved_template_recommendations": [result1, result2, result3]}
    ↓
cache_template_recommendations (fan-in target)
```

---

## Nodes

### 1. Entry & Routing Nodes

#### `planner`
- **Purpose**: Entry point that determines workflow path
- **Function**: `planner_node`
- **Caching**: None (always executes)
- **Description**: Analyzes execution config and routes to either preset/forms handler or full agent workflow

#### `preset_forms_handler`
- **Purpose**: Handles preset and form-based recommendations
- **Function**: `preset_forms_handler_node`
- **Caching**: None (fetches from MongoDB)
- **Description**: Retrieves pre-defined templates from MongoDB based on preset category or form ID

### 2. Data Extraction Nodes

#### `business_data_extractor`
- **Purpose**: Extracts business information from external sources
- **Function**: `business_data_extractor_node`
- **Caching**: Plumbed (CachePolicy via `create_node_cache_policy`), **off by default** via `execution_config.cache_strategy.use_cache=False`
- **Cache Key**: `business_data_extractor_cache_key`
- **Description**: Fetches business data from Google Places API and Yelp scraping

#### `trade_classifier`
- **Purpose**: Classifies business into trade categories (background task)
- **Function**: `trade_classifier_node`
- **Caching**: None
- **Description**: Fire-and-forget background task that runs in parallel with main workflow

### 3. Intent & Planning Nodes

#### `campaign_intent_synthesizer`
- **Purpose**: Synthesizes campaign intent from business data
- **Function**: `campaign_intent_synthesizer_node`
- **Caching**: Plumbed (CachePolicy via `create_node_cache_policy`), **off by default** via `use_cache=False`
- **Cache Key**: `campaign_intent_cache_key`
- **Description**: Uses LLM to generate campaign brief from business information

#### `section_repo_fetcher`
- **Purpose**: Fetches section repository from MongoDB
- **Function**: `section_repo_fetcher_node`
- **Caching**: Plumbed (CachePolicy via `create_node_cache_policy`), **off by default** via `use_cache=False`
- **Cache Key**: `section_repo_cache_key`
- **Description**: Retrieves available sections and builds allowed_section_types (L0/L1 type details) from section repo for template generation

### 4. Template Generation Nodes

#### `generate_template_structures`
- **Purpose**: Generates template structure (L0/L1 hierarchy)
- **Function**: `generate_template_structures_node`
- **Caching**: Plumbed (CachePolicy via `create_node_cache_policy`), **off by default** via `use_cache=False`
- **Cache Key**: `template_generation_cache_key`
- **Description**: Uses LLM to generate template recommendations with section mappings

#### `template_evaluator_smb`
- **Purpose**: Evaluates template quality for reflection loop
- **Function**: `template_evaluator_smb_node`
- **Caching**: None (used in reflection loop)
- **Description**: Scores templates and provides feedback for refinement

### 5. Section Retrieval Nodes

#### `section_retrieval_start`
- **Purpose**: Dummy router node for fan-out pattern
- **Function**: `section_retrieval_start_node` (module-level function)
- **Caching**: None
- **Description**: Pass-through node that triggers parallel section retrieval. This router just adds a node to mark the start of fan-out and does nothing else.

#### `resolve_template_sections_from_repo`
- **Purpose**: Retrieves sections for a specific template
- **Function**: `resolve_template_sections_from_repo_node`
- **Caching**: Plumbed (CachePolicy via `create_node_cache_policy`), **off by default** via `use_cache=False`
- **Cache Key**: `section_retrieval_cache_key`
- **Description**: Matches template sections to actual sections from repository. Created in parallel (one per template) and cached. The `section_retrieval_start` node above just marks the start of fan-out.

### 6. Persistence Nodes (after section retrieval)

#### `save_template_sections`
- **Purpose**: Saves generation template sections (ordered section IDs) to MongoDB
- **Function**: `save_generation_template_sections_node`
- **Caching**: None (database write)
- **Description**: Extracts section IDs from first recommendation and persists to generation_template_sections collection

---

## Graph Structure

### Visual Representation

```
                    ┌─────────┐
                    │  START  │
                    └────┬────┘
                         │
                         ▼
                    ┌─────────┐
                    │ planner │
                    └────┬────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
    [preset/forms]                  [agent]
         │                               │
         ▼                               ▼
┌──────────────────┐      ┌──────────────────────────┐
│preset_forms_     │      │business_data_extractor   │
│handler           │      └──────┬───────────────────┘
└────────┬─────────┘             │
         │                       ├──────────────────┐
         │                       │                  │
         │                       ▼                  │
         │              ┌──────────────────┐        │
         │              │campaign_intent_  │        │
         │              │synthesizer       │        │
         │              └────────┬──────────┘        │
         │                       │                  │
         │                       ▼                  │
         │              ┌──────────────────┐        │
         │              │section_repo_     │        │
         │              │fetcher_smb       │        │
         │              └────────┬──────────┘        │
         │                       │                  │
         │                       ▼                  │
         │              ┌──────────────────┐        │
         │              │type_details_     │        │
         │              │filter_smb        │        │
         │              └────────┬──────────┘        │
         │                       │                  │
         │                       ▼                  │
         │              ┌──────────────────────────┐│
         │              │template_l0_l1_generation_││
         │              │smb                        ││
         │              └────────┬──────────────────┘│
         │                       │                  │
         │         ┌─────────────┴─────────────┐   │
         │         │                           │   │
         │    [reflection]              [no reflection]│
         │         │                           │   │
         │         ▼                           ▼   │
         │  ┌──────────────────┐      ┌──────────────────┐
         │  │template_evaluator│      │section_retrieval_│
         │  │_smb             │      │start             │
         │  └────────┬────────┘      └──────┬───────────┘
         │           │                       │
         │           └───────────┐           │
         │                       │           │
         │                       ▼           │
         │              ┌──────────────────┐ │
         │              │template_l0_l1_   │ │
         │              │generation_smb    │ │
         │              └────────┬──────────┘ │
         │                       │           │
         │                       ▼           │
         │              ┌──────────────────┐ │
         │              │section_retrieval_│ │
         │              │start             │ │
         │              └────────┬──────────┘ │
         │                       │           │
         │                       │           │
         │                       ▼           │
         │         ┌─────────────────────────┐
         │         │  FAN-OUT (parallel)    │
         │         │  resolve_template_sections_from_repo  │
         │         │  (one per template)     │
         │         └────────┬────────────────┘
         │                  │
         │                  ▼
         │         ┌─────────────────────────┐
         │         │cache_template_recommendations      │
         │         │  (fan-in target)        │
         │         └────────┬────────────────┘
         │                  │
         │                  ▼
         │         ┌─────────────────────────┐
         │         │save_template_sections  │
         │         └────────┬────────────────┘
         │                  │
         └──────────────────┼──────────────────┐
                            │                  │
                            ▼                  ▼
                       ┌─────────┐      ┌─────────┐
                       │  END    │      │  END    │
                       └─────────┘      └─────────┘
                    (preset/forms)    (trade_classifier)
```

### Execution Paths

#### Path 1: Preset/Forms Path (Fast Path)
```
START → planner → preset_forms_handler → END
```
- **Trigger**: `execution_config.recommendation_type` in `["preset", "forms"]`
- **Duration**: Fast (MongoDB lookup only)
- **Use Case**: Pre-defined templates for common business types

#### Path 2: Agent Path (Full Workflow)
```
START → planner → business_data_extractor → campaign_intent_synthesizer → 
section_repo_fetcher → generate_template_structures → [reflection?] → section_retrieval_start → 
[FAN-OUT: resolve_template_sections_from_repo × N] → cache_template_recommendations → save_template_sections → END
```
- **Trigger**: `execution_config.recommendation_type == "agent"` or no execution_config
- **Duration**: Longer (multiple LLM calls)
- **Use Case**: Custom AI-generated recommendations

#### Path 3: Reflection Loop (Optional, within Agent Path)
```
generate_template_structures → template_evaluator_smb → 
generate_template_structures → [repeat until max_iterations]
```
- **Trigger**: `enable_reflection=True` and `iteration <= max_iterations`
- **Purpose**: Refines templates based on evaluation feedback

#### Path 4: Trade Classifier (Parallel Background Task)
```
business_data_extractor → trade_classifier → END
```
- **Trigger**: Always runs after `business_data_extractor`
- **Purpose**: Classifies business in background (doesn't block main flow)
- **Note**: This is a fire-and-forget task that runs independently

---

## Edge Types

### 1. Direct Edges (Sequential)
- `START → planner`
- `preset_forms_handler → END`
- `business_data_extractor → campaign_intent_synthesizer`
- `campaign_intent_synthesizer → section_repo_fetcher`
- `section_repo_fetcher → generate_template_structures`
- `template_evaluator_smb → generate_template_structures` (reflection loop)
- `resolve_template_sections_from_repo → cache_template_recommendations`
- `cache_template_recommendations → save_template_sections`
- `save_template_sections → END`
- `trade_classifier → END`

### 2. Conditional Edges

#### Planner Routing
- **From**: `planner`
- **Condition**: `router_select_execution_path_on_recommendation_type(state)`
- **Routes**:
  - `"preset_forms"` → `preset_forms_handler`
  - `"agent"` → `business_data_extractor`

#### Reflection Routing
- **From**: `generate_template_structures`
- **Condition**: `router_select_section_retrieval_or_evaluation(state)`
- **Routes**:
  - `"evaluation"` → `template_evaluator_smb` (if reflection enabled and iteration <= max_iterations)
  - `"section_retrieval_start"` → `section_retrieval_start` (if no reflection or max iterations reached)

### 3. Fan-Out (Parallel Execution)
- **From**: `section_retrieval_start`
- **Function**: `router_fan_out_parallel_section_retrievers(state)`
- **Behavior**: Creates one `Send("resolve_template_sections_from_repo", {...})` per template
- **Result**: Multiple parallel `resolve_template_sections_from_repo` executions

### 4. Fan-In (Aggregation)
- **From**: All `resolve_template_sections_from_repo` instances (parallel)
- **To**: `cache_template_recommendations`
- **Behavior**: LangGraph merges state from parallel executions; cache_template_recommendations runs after fan-in

---

## Caching Strategy

Node-level caching is **plumbed but off by default** (`execution_config.cache_strategy.use_cache=False`). Enable per run via `execution_config.cache_strategy.use_cache=True`.

### Cache Structure
- **Shared utils**: `core/cache/` — `hash_dict`, `get_value_from_langgraph_state`, `should_use_cache`, `create_cache_policy`
- **Workflow-specific keys**: `agent_workflows/landing_page_builder/cache/keys.py` — `*_cache_key` functions
- **Policy wiring**: `agent_workflows/landing_page_builder/cache/__init__.py` — `create_node_cache_policy(node_name)`

### Cached Nodes (when use_cache=True)
1. **business_data_extractor** - Cache key: business_name, google_places_id, yelp_url
2. **campaign_intent_synthesizer** - Cache key: business data, website context, google/yelp hashes
3. **section_repo_fetcher** - Cache key: static repo filter
4. **generate_template_structures** - Cache key: campaign query, type details count, iteration
5. **resolve_template_sections_from_repo** - Cache key: template_id, campaign_query, section_repo size

### Non-Cached Nodes
- **planner** - Always needs to run (routing decision)
- **preset_forms_handler** - MongoDB lookup (fast)
- **template_evaluator_smb** - Used in reflection loop (needs fresh evaluation)
- **save_*** nodes** - Database writes (should not cache)
- **trade_classifier** - Background task (no caching needed)

### Cache TTL
- Default: 60 days (5,184,000 seconds) — `core/cache/policy.py` `DEFAULT_CACHE_TTL`

---

## State Management

### State Persistence
- **Checkpointer**: `MemorySaver()` (in-memory state persistence)
- **Cache**: Redis-based caching via `smb_workflow_cache`

### State Schema
- **Type**: `LandingPageWorkflowState` (Pydantic model)
- **Key Fields**:
  - `execution_config`: Determines routing path
  - `enable_reflection`: Controls reflection loop
  - `iteration`: Tracks reflection iterations
  - `templates` / `refined_templates`: Template results
  - `resolved_template_recommendations`: Final recommendations

---

## Streaming

The workflow supports streaming via `stream()` method:
- **Stream Modes**: `["updates", "messages"]`
- **Updates**: Node completion events
- **Messages**: LLM token events (for streaming responses)

---

## Error Handling

- Graph uses LangGraph's built-in error handling
- State includes `error` and `failed_node` fields for error tracking
- Checkpointer allows resuming from failures

---

## Performance Considerations

1. **Caching**: Reduces redundant LLM calls for repeated inputs
2. **Parallel Execution**: Section retrieval runs in parallel for multiple templates
3. **Fast Path**: Preset/forms path bypasses expensive LLM calls
4. **Background Tasks**: Trade classifier doesn't block main workflow
5. **Reflection**: Optional refinement loop (disabled by default for speed)
