# nodes/smb/autopop/style_nodes/text_color.py
"""
Text color autopopulation node.

Contains:
- text_color_agent: Autopopulates text element colors based on background colors
"""

from typing import Any, Dict, Optional
from langgraph.types import RunnableConfig

from template_json_builder.autopopulation.autopopulators.graph_state import AutopopulationImmutableState
from template_json_builder.models.schema_and_code import AutopopulationModuleTypes
from template_json_builder.ipsum_lorem_agents.agent_utils import element_color_agent_utils
from template_json_builder.ipsum_lorem_agents.default_content_provider.background_conditioned_text_color_recommendation import (
    autopopulate_text_variants_for_backgrounds,
)
from template_json_builder.models.autopop_dataclasses.prompt_spec.prompt_dataclasses import (
    BackgroundConditionedTextColorAutopopSectionInputModel,
    BackgroundConditionedTextColorOutputModel,
)

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils import autopop_helpers
from wwai_agent_orchestration.prompt_builder import prompt_builder_dataclass
from wwai_agent_orchestration.prompt_builder.prompt_builder import PromptBuilder
from wwai_agent_orchestration.prompt_builder.prompt_classes.landing_page_builder.autopop import text_color_autopop
from wwai_agent_orchestration.utils.llm.model_utils import get_model_config_from_configurable


def _execute_text_color_prompt(
    inp: BackgroundConditionedTextColorAutopopSectionInputModel,
    bypass_prompt_cache: bool = False,
    model_config: Optional[Dict[str, Any]] = None,
) -> BackgroundConditionedTextColorOutputModel:
    spec = text_color_autopop.TextColorAutoPopSpec()
    response = spec.execute(
        builder=PromptBuilder(),
        inp=inp,
        model_config=model_config or spec.MODEL_CONFIG,
        run_on_worker=False,
        bypass_prompt_cache=bypass_prompt_cache,
    )
    assert response.status.value == prompt_builder_dataclass.Status.SUCCESS.value
    return BackgroundConditionedTextColorOutputModel(**response.result)


def text_color_agent_module(
    imm: AutopopulationImmutableState,
    agents_output: Dict[str, Any],
    use_mock: bool = False,
    bypass_prompt_cache: bool = False,
    is_dev_mode: bool = False,
    model_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Autopopulate text element colors based on background colors.
    
    Args:
        imm: The immutable state containing template and section information
        agents_output: Output from previous agents (e.g., container colors)
        use_mock: Whether to use mock data instead of calling the actual agent
        bypass_prompt_cache: Whether to bypass prompt cache
        is_dev_mode: Whether to allow random colors in dev mode
        
    Returns:
        Dict containing agent_input and agent_output with module_name as key
    """
    module_name = AutopopulationModuleTypes.ELEMENT_TEXT_COLOR.value
    inp = element_color_agent_utils.build_element_color_agent_input(
        imm=imm, 
        module_name=module_name, 
        agents_output=agents_output,
        allow_random_color=is_dev_mode
    )
    
    if use_mock:
        output = autopopulate_text_variants_for_backgrounds(inp)
    else:
        output = _execute_text_color_prompt(
            inp, bypass_prompt_cache, model_config=model_config
        )

    return {
        "agent_input": {module_name: inp.model_dump()},
        "agent_output": {module_name: output.model_dump()}
    }


@NodeRegistry.register(
    name="text_color_agent",
    description="Autopopulate text colors based on background colors using LLM",
    max_retries=1,
    timeout=150,
    tags=["autopopulation", "style", "color", "text"],
    display_name="Choosing text colors",
    show_node=False,
    show_output=False,
)
async def text_color_agent(state: LandingPageWorkflowState, config: RunnableConfig = None) -> Dict[str, Any]:
    """Process text color autopopulation (runs in parallel with button and misc color agents)."""
    autopop_state = autopop_helpers.get_autopop_state(state)
    imm = await autopop_helpers.resolve_imm(autopop_state, config, full_state=state)
    agent_outputs = autopop_state.get("agent_outputs", {})
    use_mock_flag = autopop_helpers.use_mock(autopop_state)
    configurable = (config or {}).get("configurable", {})
    model_config = get_model_config_from_configurable(configurable)
    res = text_color_agent_module(
        imm,
        agent_outputs,
        use_mock=use_mock_flag,
        bypass_prompt_cache=autopop_state.get("bypass_prompt_cache", False),
        is_dev_mode=autopop_state.get("is_dev_mode", False),
        model_config=model_config
    )
    
    delta = {
        "agent_inputs": res["agent_input"],
        "agent_outputs": res["agent_output"],
        "logs": [{"level": "info", "msg": "text_color_agent: completed"}],
    }
    return autopop_helpers.update_autopop_state(state, delta)
