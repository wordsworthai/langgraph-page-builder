# nodes/smb/template_evaluator_smb.py

"""
Template Evaluator Node (SMB-specific) - BOILERPLATE.

Evaluates generated templates for quality (used in reflection loop).

For now, this is a simple boilerplate that returns mock evaluations.
Can be enhanced later with actual LLM-based evaluation logic.
"""

import time
from typing import Dict, Any, Optional
from langgraph.types import RunnableConfig

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import (
    LandingPageWorkflowState,
    TemplateResult,
)
from wwai_agent_orchestration.prompt_builder.prompt_builder import PromptBuilder
from wwai_agent_orchestration.prompt_builder.prompt_classes.landing_page_builder.template_selection.template_evaluation import (
    TemplateEvaluationSpec,
    TemplateEvaluationInput,
)
from wwai_agent_orchestration.utils.llm.model_utils import get_model_config_from_configurable


logger = get_logger(__name__)


@NodeRegistry.register(
    name="template_evaluator_smb",
    description="Evaluate SMB templates for quality (boilerplate for reflection)",
    max_retries=1,
    timeout=120,
    tags=["smb", "llm", "evaluation", "boilerplate"],
    display_name="Evaluating designs",
    show_node=False,
    show_output=False,
)
def template_evaluator_smb_node(
    state: LandingPageWorkflowState,
    config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """
    Evaluate templates against campaign intent (BOILERPLATE).
    
    For now, returns mock evaluations with fixed scores.
    Only runs if enable_reflection=True.
    
    Future enhancement: Call LLM to evaluate templates based on:
    - Campaign intent alignment
    - SMB best practices
    - Section flow and coherence
    
    Args:
        state: LandingPageWorkflowState with templates, campaign_intent
        config: Node configuration
        
    Returns:
        Dict with template_evaluations (via .model_dump())
    """
    start_time = time.time()
    
    config = config or {}
    t = state.template
    data = state.data
    templates = (t.templates or []) if t else []
    campaign_intent = data.campaign_intent if data else None

    if not templates:
        raise ValueError("templates required for template_evaluator_smb")
    
    if not campaign_intent:
        raise ValueError("campaign_intent required for template_evaluator_smb")
    
    logger.info(
        "Starting SMB template evaluation (BOILERPLATE)",
        node="template_evaluator_smb",
        template_count=len(templates)
    )

    configurable = config.get("configurable", {}) if config else {}
    model_config = get_model_config_from_configurable(configurable)
    evaluations = {}

    for template in templates:
        template_name = template['template_name']
        section_info = template['section_info']
        
        logger.info(
            f"Evaluating template: {template_name}",
            node="template_evaluator_smb"
        )
        
        try:
            result = TemplateEvaluationSpec.execute(
                builder=PromptBuilder(),
                inp=TemplateEvaluationInput(
                    generator_response=section_info,
                    page_query=campaign_intent.campaign_query,
                    type_details=(t.section_repo_result.allowed_section_types or []) if t and t.section_repo_result else [],
                ),
                model_config=model_config,
                run_on_worker=configurable.get('run_on_worker', False),
                bypass_prompt_cache=True,
            )
            
            if result.status.value != "success":
                logger.error(
                    f"Evaluation failed for {template_name}: {result.error}",
                    node="template_evaluator_smb"
                )
                evaluations[template_name] = {
                    "error": result.error,
                    "score": 0
                }
                continue
            
            # Extract evaluation
            evaluations[template_name] = result.result
            
            logger.info(
                f"✅ {template_name} evaluated",
                node="template_evaluator_smb",
                score=result.result.get('score', 0)
            )
            
        except Exception as e:
            logger.error(
                f"Exception during evaluation: {str(e)}",
                node="template_evaluator_smb"
            )
            evaluations[template_name] = {"error": str(e), "score": 0}

    # Calculate average score
    avg_score = sum(e.get('score', 0) for e in evaluations.values()) / len(evaluations) if evaluations else 0
    
    duration_ms = (time.time() - start_time) * 1000
    
    logger.info(
        "✅ Template evaluation complete (BOILERPLATE)",
        node="template_evaluator_smb",
        templates_evaluated=len(evaluations),
        average_usability_score=round(avg_score, 2),
        duration_ms=round(duration_ms, 2),
        note="Using mock evaluations - enhance with LLM later"
    )
    
    # ========================================================================
    # RETURN: nested template stage
    # ========================================================================
    return {
        "template": TemplateResult(template_evaluations=evaluations),
    }


