# nodes/smb/autopop/style_nodes/container_color.py
"""
Container color autopopulation nodes.

Contains:
- container_color_agent: Autopopulates container/section background colors
- container_color_snapshot: Creates snapshot after container color autopopulation
"""

from typing import Any, Dict, Optional
from langgraph.types import RunnableConfig

from template_json_builder.autopopulation.autopopulators.graph_state import AutopopulationImmutableState
from template_json_builder.models.schema_and_code import AutopopulationModuleTypes
from template_json_builder.ipsum_lorem_agents.agent_utils import container_color_agent_utils
from template_json_builder.ipsum_lorem_agents.default_content_provider.container_color_recommendation import (
    autopopulate_section_backgrounds,
)
from template_json_builder.models.autopop_dataclasses.prompt_spec.prompt_dataclasses import (
    BackgroundColorAutopopInputModel,
    BackgroundColorAutopopOutputModel,
)

from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.contracts.landing_page_builder.workflow_state import LandingPageWorkflowState
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils import autopop_helpers
from wwai_agent_orchestration.utils.landing_page_builder.ui_logs import (
    container_color_html,
    make_ui_execution_log_entry_from_registry,
)
from wwai_agent_orchestration.prompt_builder import prompt_builder_dataclass
from wwai_agent_orchestration.prompt_builder.prompt_builder import PromptBuilder
from wwai_agent_orchestration.prompt_builder.prompt_classes.landing_page_builder.autopop import bg_color_autopop
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils.template_materialize_utils import materialize_node
from wwai_agent_orchestration.utils.llm.model_utils import get_model_config_from_configurable


def _execute_background_color_prompt(
    inp: BackgroundColorAutopopInputModel,
    bypass_prompt_cache: bool = False,
    model_config: Optional[Dict[str, Any]] = None,
) -> BackgroundColorAutopopOutputModel:
    spec = bg_color_autopop.BackgroundColorAutoPopSpec()
    response = spec.execute(
        builder=PromptBuilder(),
        inp=inp,
        model_config=model_config or spec.MODEL_CONFIG,
        run_on_worker=False,
        bypass_prompt_cache=bypass_prompt_cache,
    )
    assert response.status.value == prompt_builder_dataclass.Status.SUCCESS.value
    return BackgroundColorAutopopOutputModel(**response.result)


def container_color_agent_module(
    imm: AutopopulationImmutableState,
    use_mock: bool = False,
    bypass_prompt_cache: bool = False,
    model_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Autopopulate container/section background colors.

    Args:
        imm: The immutable state containing template and section information
        use_mock: Whether to use mock data instead of calling the actual agent
        bypass_prompt_cache: Whether to bypass prompt cache
        model_config: Optional LLM model config (model, provider, temperature)

    Returns:
        Dict containing agent_input and agent_output with module_name as key
    """
    module_name = AutopopulationModuleTypes.CONTAINER_COLOR.value
    inp = container_color_agent_utils.build_container_color_agent_input(imm=imm)

    if use_mock:
        import random
        import time
        time.sleep(random.randint(2, 5))
        output = autopopulate_section_backgrounds(inp)
    else:
        output = _execute_background_color_prompt(
            inp, bypass_prompt_cache, model_config=model_config
        )
        
    return {
        "agent_input": {module_name: inp.model_dump()},
        "agent_output": {module_name: output.model_dump()}
    }


@NodeRegistry.register(
    name="container_color_agent",
    description="Autopopulate container/section background colors using LLM",
    max_retries=1,
    timeout=150,
    tags=["autopopulation", "style", "color", "container"],
    display_name="Choosing background colors",
    show_node=True,
    show_output=False,
)
async def container_color_agent(state: LandingPageWorkflowState, config: RunnableConfig = None) -> Dict[str, Any]:
    """Autopopulate container/section background colors."""
    autopop_state = autopop_helpers.get_autopop_state(state)
    imm = await autopop_helpers.resolve_imm(autopop_state, config, full_state=state)
    configurable = (config or {}).get("configurable", {})
    model_config = get_model_config_from_configurable(configurable)
    res = container_color_agent_module(
        imm=imm,
        use_mock=autopop_helpers.use_mock(autopop_state),
        bypass_prompt_cache=autopop_state.get("bypass_prompt_cache", False),
        model_config=model_config
    )
    delta = {
        "agent_inputs": res["agent_input"],
        "agent_outputs": res["agent_output"],
        "logs": [{"level": "info", "msg": "container_color_agent: completed"}],
        "meta": {"last_node": "container_color_agent"},
    }
    result = autopop_helpers.update_autopop_state(state, delta)
    result["ui_execution_log"] = [
        make_ui_execution_log_entry_from_registry("container_color_agent", container_color_html())
    ]
    return result


@NodeRegistry.register(
    name="container_color_snapshot",
    description="Create snapshot after container color autopopulation",
    max_retries=1,
    timeout=90,
    tags=["autopopulation", "snapshot", "style"],
    display_name="Saving color choices",
    show_node=False,
    show_output=False,
)
async def container_color_snapshot(state: LandingPageWorkflowState, config: RunnableConfig = None) -> Dict[str, Any]:
    """Create snapshot after container color autopopulation."""
    autopop_state = autopop_helpers.get_autopop_state(state)
    materialize_config = autopop_helpers.build_materialize_config(
        state=state,
        config=config,
        autopop_state=autopop_state,
        label="container_color"
    )
    delta = await materialize_node(
        autopop_state,
        config=materialize_config,
    )
    delta.setdefault("logs", []).append({"level": "info", "msg": "container_color_snapshot: snapshot created"})
    delta.setdefault("meta", {}).update({"last_node": "container_color_snapshot"})
    return autopop_helpers.update_autopop_state(state, delta)
