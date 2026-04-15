# nodes/landing_page_builder/template_selection/generate_template_structures.py
"""
Generate Template Structures Node.

Generates 3 templates with L0/L1 section structure via LLM.

Features:
- Validates ALL L0/L1 combinations against section_repo_result.allowed_section_types
- Retries up to 3 times if invalid combinations detected
- Supports reflection with past_context
- Streams tokens automatically via LangGraph
- Uses SMB-specific campaign intent (not page URL)

Flow:
- Iteration 0: Initial generation → returns 'templates'
- Iteration 1+: Refined generation → returns 'refined_templates'

"""

import time
import json
import hashlib
from typing import Dict, Any, List, Optional
from langgraph.types import RunnableConfig

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import (
    LandingPageWorkflowState,
    TemplateResult
)
from wwai_agent_orchestration.nodes.landing_page_builder.template_selection.node_utils.template_structures_utils import (
    validate_templates_l0_l1,
    transform_to_template_format,
)

from wwai_agent_orchestration.prompt_builder.prompt_builder import PromptBuilder
from wwai_agent_orchestration.prompt_builder.prompt_classes.landing_page_builder.template_selection.template_section_structure_generation import (
    TemplateSectionStructureGenerationSpec,
    TemplateSectionStructureGenerationInput,
)
from wwai_agent_orchestration.utils.landing_page_builder.ui_logs import (
    template_list_html,
    make_ui_execution_log_entry_from_registry,
)

logger = get_logger(__name__)


def _normalize_raw_l0_l1_result(raw_l0_l1_result: Any) -> Dict[str, Any]:
    """Normalize LLM result to dict; parse string as JSON or raise if empty/None/invalid."""
    if raw_l0_l1_result is None:
        raise Exception("LLM returned None - structured output failed")
    if isinstance(raw_l0_l1_result, str):
        if not raw_l0_l1_result or not raw_l0_l1_result.strip():
            raise Exception("LLM returned empty string - structured output failed")
        try:
            raw_l0_l1_result = json.loads(raw_l0_l1_result)
            logger.warning(
                "LLM returned string instead of dict - parsed as JSON",
                node="generate_template_structures"
            )
        except json.JSONDecodeError as e:
            logger.error(
                f"LLM returned unparseable string: {raw_l0_l1_result[:500]}",
                node="generate_template_structures"
            )
            raise Exception(f"LLM returned invalid JSON string: {e}") from e
    return raw_l0_l1_result


def _handle_validation_failure(
    invalid_sections: List[Dict[str, Any]],
    attempt: int,
    max_retries: int,
    iteration: int,
) -> None:
    """Log invalid sections (debug), then retry log or raise AssertionError on final attempt."""
    for invalid in invalid_sections:
        logger.debug(
            f"Invalid L0/L1: {invalid['template']}, Section {invalid['section_index']}: "
            f"{invalid['section_l0']} - {invalid['section_l1']}",
            node="generate_template_structures"
        )
    if attempt < max_retries - 1:
        logger.info(
            f"⟳ Retrying generation (attempt {attempt + 2}/{max_retries})...",
            node="generate_template_structures"
        )
    else:
        error_msg = (
            f"Failed to generate valid L0/L1 combinations after {max_retries} attempts. "
            f"Found {len(invalid_sections)} invalid combinations. "
            f"Invalid L0/L1 combinations: {invalid_sections}"
        )
        logger.error(
            "❌ Validation failed after all retry attempts",
            node="generate_template_structures",
            iteration=iteration,
            total_attempts=max_retries,
            invalid_sections_count=len(invalid_sections),
            invalid_sections=invalid_sections,
            metrics_type="validation_failure"
        )
        raise AssertionError(error_msg)


def _build_past_context_for_reflection(
    t: Any,
    iteration: int,
) -> Optional[Dict[str, Any]]:
    """Build past_context from template evaluations when iteration >= 1 for reflection."""
    past_context = None
    if iteration < 1:
        return past_context

    template_evaluations = t.template_evaluations if t else None
    templates = (t.templates or []) if t else []
    if not template_evaluations or not templates:
        return past_context
    logger.info(
        f"Iteration {iteration}: Building past_context from evaluations",
        node="generate_template_structures"
    )
    past_context = {}
    for template in templates:
        template_name = template['template_name']
        eval_data = template_evaluations.get(template_name)
        if eval_data:
            past_context[template_name] = {
                'previous_recommendation': template['section_info'],
                'evaluation': eval_data
            }
    logger.info(
        f"Past context prepared for {len(past_context)} templates",
        node="generate_template_structures",
        usability_scores={
            name: data['evaluation'].get('usability_score')
            for name, data in past_context.items()
        }
    )
    return past_context


def _call_llm_for_template_structures(
    campaign_intent: Any,
    allowed_section_types: List[Dict[str, Any]],
    past_context: Optional[Dict[str, Any]],
    run_on_worker: bool,
) -> Any:
    """Call LLM to get L0/L1 template recommendations; returns raw result (dict/str/None)."""
    result = TemplateSectionStructureGenerationSpec.execute(
        builder=PromptBuilder(),
        inp=TemplateSectionStructureGenerationInput(
            campaign_query=campaign_intent.campaign_query,
            type_details=allowed_section_types,
            past_context=past_context,
        ),
        run_on_worker=run_on_worker,
        bypass_prompt_cache=True,
    )
    if result.status.value != "success":
        raise Exception(f"LLM call failed: {result.error}")
    raw_l0_l1_result = result.result
    logger.info(
        f"Raw LLM result type: {type(raw_l0_l1_result).__name__}, "
        f"content preview: {str(raw_l0_l1_result)[:200] if raw_l0_l1_result else 'EMPTY'}",
        node="generate_template_structures"
    )
    return raw_l0_l1_result


@NodeRegistry.register(
    name="generate_template_structures",
    description="Generate 3 SMB templates with L0/L1 structure via LLM (with validation + retry)",
    max_retries=1,
    timeout=180,
    tags=["smb", "llm", "planning", "streaming", "validation"],
    display_name="Generating page layouts",
    show_node=True,
    show_output=True,
)
def generate_template_structures_node(
    state: LandingPageWorkflowState,
    config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """
    Call LLM to generate 3 templates with L0/L1 section structure.
    
    NEW FEATURES:
    - Uses SMB campaign intent (not page URL)
    - Validates ALL L0/L1 combinations against section_repo_result.allowed_section_types
    - Retries up to 3 times if invalid combinations detected
    - Supports reflection with past_context
    
    This streams tokens automatically via LangGraph.
    
    Args:
        state: LandingPageWorkflowState with campaign_intent, section_repo_result.allowed_section_types
        config: Node configuration
        
    Returns:
        Dict with templates (iteration 0) or refined_templates (iteration 1+)
        
    Raises:
        AssertionError: If validation fails after 3 retry attempts
    """
    start_time = time.time()
    
    config = config or {}
    
    # Extract inputs from nested state
    data = state.data
    t = state.template
    inp = state.input
    campaign_intent = data.campaign_intent if data else None
    allowed_section_types = (t.section_repo_result.allowed_section_types or []) if t and t.section_repo_result else []
    iteration = t.iteration if t is not None else 0
    business_name = inp.business_name if inp else ""

    if not campaign_intent:
        raise ValueError("campaign_intent required for generate_template_structures")
    
    if not allowed_section_types:
        raise ValueError(
            "section_repo_result.allowed_section_types required (from section_repo_fetcher). "
            "This is CRITICAL for L0/L1 validation."
        )
    
    # Config
    configurable = config.get("configurable", {})
    run_on_worker = configurable.get('run_on_worker', False)
    max_retries = 3  # Hardcoded retry limit
    
    logger.info(
        "Starting SMB template L0/L1 generation with validation",
        node="generate_template_structures",
        iteration=iteration,
        run_on_worker=run_on_worker,
        allowed_section_types_count=len(allowed_section_types),
        max_retries=max_retries
    )
    
    # ========================================================================
    # PREPARE PAST_CONTEXT (if iteration > 0 for reflection)
    # ========================================================================
    past_context = _build_past_context_for_reflection(t, iteration)

    # ========================================================================
    # RETRY LOOP WITH VALIDATION
    # ========================================================================
    for attempt in range(max_retries):
        attempt_start = time.time()

        logger.info(
            f"Generation attempt {attempt + 1}/{max_retries}",
            node="generate_template_structures",
            iteration=iteration,
            attempt=attempt + 1
        )

        try:
            # Call LLM for L0/L1 recommendations (streams tokens).
            raw_l0_l1_result = _call_llm_for_template_structures(
                campaign_intent=campaign_intent,
                allowed_section_types=allowed_section_types,
                past_context=past_context,
                run_on_worker=run_on_worker,
            )
            raw_l0_l1_result = _normalize_raw_l0_l1_result(raw_l0_l1_result)
            l0_l1_recommendations = raw_l0_l1_result.get('recommendations', {})
            
            logger.info(
                f"LLM returned {len(l0_l1_recommendations)} templates",
                node="generate_template_structures",
                attempt=attempt + 1
            )
            
            # ================================================================
            # VALIDATE L0/L1 COMBINATIONS
            # ================================================================
            # Ensure every template section L0/L1 is in the allowed set (whitelist built inside).
            is_valid, invalid_sections = validate_templates_l0_l1(
                l0_l1_recommendations,
                allowed_section_types,
            )
            
            attempt_duration = (time.time() - attempt_start) * 1000
            
            if is_valid:
                # ✅ ALL VALID - Break retry loop
                logger.info(
                    "✅ All L0/L1 combinations are VALID",
                    node="generate_template_structures",
                    iteration=iteration,
                    attempt=attempt + 1,
                    attempt_duration_ms=round(attempt_duration, 2),
                    metrics_type="validation_success"
                )
                break  # Exit retry loop
            
            else:
                # ❌ INVALID COMBINATIONS FOUND
                logger.warning(
                    f"⚠️ Found {len(invalid_sections)} invalid L0/L1 combinations",
                    node="generate_template_structures",
                    iteration=iteration,
                    attempt=attempt + 1,
                    invalid_sections_count=len(invalid_sections),
                    first_5_invalid=invalid_sections[:5],
                    attempt_duration_ms=round(attempt_duration, 2),
                    metrics_type="validation_retry"
                )
                
                _handle_validation_failure(
                    invalid_sections, attempt, max_retries, iteration
                )

        except AssertionError:
            # Re-raise validation failure
            raise
        except Exception as e:
            logger.error(
                f"Error during generation attempt {attempt + 1}",
                node="generate_template_structures",
                error=str(e),
                attempt=attempt + 1
            )
            if attempt < max_retries - 1:
                logger.info(f"⟳ Retrying after error...", node="generate_template_structures")
            else:
                raise
    
    # ========================================================================
    # TRANSFORM TO TEMPLATE FORMAT
    # ========================================================================
    # Generate query_hash from campaign intent + business name
    hash_input = f"{campaign_intent.campaign_query}_{business_name}"
    query_hash = hashlib.md5(hash_input.encode()).hexdigest()
    # Convert LLM recommendation dict to list of template dicts for state.
    templates = transform_to_template_format(
        l0_l1_recommendations=l0_l1_recommendations,
        query_hash=query_hash,
        business_name=business_name
    )
    
    total_duration = (time.time() - start_time) * 1000
    
    logger.info(
        "✅ SMB template L0/L1 generation complete with valid combinations",
        node="generate_template_structures",
        iteration=iteration,
        template_count=len(templates),
        total_duration_ms=round(total_duration, 2),
        metrics_type="generation_complete"
    )
    
    ui_output_html = template_list_html(templates=templates)

    if iteration == 0:
        return {
            "template": TemplateResult(
                templates=templates,
                iteration=1,
                raw_l0_l1_result=raw_l0_l1_result,
            ),
            "ui_execution_log": [
                make_ui_execution_log_entry_from_registry("generate_template_structures", ui_output_html)
            ],
        }
    else:
        return {
            "template": TemplateResult(
                templates=templates,
                refined_templates=templates,
                iteration=iteration + 1,
            ),
            "ui_execution_log": [
                make_ui_execution_log_entry_from_registry("generate_template_structures", ui_output_html)
            ],
        }
