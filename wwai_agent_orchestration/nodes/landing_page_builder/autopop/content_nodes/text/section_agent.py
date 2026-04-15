# nodes/smb/autopop/content_nodes/text/section_agent.py
"""
Content text section agent node.

Processes content text for a single section (runs in parallel for each section).
"""

from typing import Any, Dict, Optional
from langgraph.types import RunnableConfig
import time
from template_json_builder.autopopulation.autopopulators.graph_state import (
    AutopopulationLangGraphAgentsState,
    AutopopulationImmutableState,
)
from template_json_builder.models.schema_and_code import AutopopulationModuleTypes
from template_json_builder.ipsum_lorem_agents.agent_utils import content_agent_utils
from template_json_builder.ipsum_lorem_agents.default_content_provider import content_generator

from template_json_builder.models.autopop_dataclasses.prompt_spec.prompt_dataclasses import (
    ContentAgentInputModel,
    ContentAgentOutputModel,
)

from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.core.registry.node_registry import NodeRegistry
from wwai_agent_orchestration.nodes.landing_page_builder.autopop.utils import autopop_helpers
from wwai_agent_orchestration.prompt_builder import prompt_builder_dataclass
from wwai_agent_orchestration.prompt_builder.prompt_builder import PromptBuilder
from wwai_agent_orchestration.prompt_builder.prompt_classes.landing_page_builder.autopop import content_agent
from wwai_agent_orchestration.utils.llm.model_utils import get_model_config_from_configurable

logger = get_logger(__name__)


def _execute_content_prompt(
    inp: ContentAgentInputModel,
    bypass_prompt_cache: bool = False,
    model_config: Optional[Dict[str, Any]] = None,
) -> ContentAgentOutputModel:
    spec = content_agent.ContentAgentPromptSpec()
    response = spec.execute(
        builder=PromptBuilder(),
        inp=inp,
        model_config=model_config or spec.MODEL_CONFIG,
        run_on_worker=False,
        bypass_prompt_cache=bypass_prompt_cache,
    )
    assert response.status.value == prompt_builder_dataclass.Status.SUCCESS.value
    return ContentAgentOutputModel(**response.result)


def content_text_agent_module_single_section(
    imm: AutopopulationImmutableState,
    section_id: str,
    data_context: str = "",
    use_mock: bool = False,
    bypass_prompt_cache: bool = False,
    model_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Autopopulate text content for a single section (for parallel processing).
    
    Args:
        imm: The immutable state containing template and section information
        section_id: The section ID to process
        brand_url: URL of the brand for context
        entity_url: URL of the entity for context
        content_providers_tools_response: Response from content provider tools
        data_context: String containing all business context data (tone, business info, reviews, etc.)
        use_mock: Whether to use mock data instead of calling the actual agent
        bypass_prompt_cache: Whether to bypass prompt cache
        
    Returns:
        Dict containing agent_input and agent_output for the single section
    """
    module_name = AutopopulationModuleTypes.CONTENT_TEXT.value
    
    # data_context should be a string, not a dict
    # Use provided data_context (from content_data_context_fetcher) or empty string as fallback
    agent_input = content_agent_utils.section_specific_content_text_module(
        imm, 
        section_id=section_id,
        data_context=data_context
    )
    
    if use_mock:
        import random
        time.sleep(random.random() * 3)
        agent_output = content_generator.build_content_from_lorem(agent_input)
    else:
        agent_output = _execute_content_prompt(
            agent_input, bypass_prompt_cache, model_config=model_config
        )
    
    return {
        "agent_input": {module_name: {section_id: agent_input.model_dump()}},
        "agent_output": {module_name: {section_id: agent_output.model_dump()}}
    }


@NodeRegistry.register(
    name="content_text_section_agent",
    description="Autopopulate text content for a specific section using LLM (runs in parallel per section)",
    max_retries=1,
    timeout=150,
    tags=["autopopulation", "content", "text", "section"],
    display_name="Writing section text",
    show_node=False,
    show_output=False,
)
async def content_text_section_agent(state: Dict[str, Any], config: RunnableConfig = None) -> Dict[str, Any]:
    """Process content text for a single section (runs in parallel for each section).
    
    According to GRAPH_DOCUMENTATION.md, when using Send(), the payload becomes the node's
    entire state. So state here is the Send payload dict.
    """
    # When using Send(), the payload becomes the entire state
    # So state here is the Send payload dict
    if hasattr(state, 'model_dump'):
        state_dict = state.model_dump()
    else:
        state_dict = state
    
    # Extract data from Send payload (which is now the state)
    section_id = state_dict.get("section_id")
    if not section_id:
        raise ValueError("section_id not found in Send payload for content_text_section_agent")
    
    use_mock = state_dict.get("use_mock", False)
    bypass_prompt_cache = state_dict.get("bypass_prompt_cache", False)
    
    # Extract data_context from meta (passed in Send payload from fanout)
    # The data_context is stored by content_data_context_fetcher_node in autopopulation_langgraph_state.meta
    # The fanout function passes meta directly in the Send payload
    meta = state_dict.get("meta", {})
    data_context = meta.get("data_context", "")
    
    if not data_context:
        logger.warning(f"No data_context found in meta for section {section_id}, using empty string")
    
    # Reconstruct autopop_state from Send payload to resolve imm
    immutable_ref = state_dict.get("immutable_ref", {})
    meta = state_dict.get("meta", {})
    if not (immutable_ref.get("run_id") or meta.get("run_id")):
        raise ValueError("No run_id found in Send payload for content_text_section_agent")

    autopop_state_for_imm = AutopopulationLangGraphAgentsState(
        immutable_ref=immutable_ref,
        meta=meta
    )
    imm = await autopop_helpers.resolve_imm(autopop_state_for_imm, config)
    configurable = (config or {}).get("configurable", {})
    model_config = get_model_config_from_configurable(configurable)
    res = content_text_agent_module_single_section(
        imm=imm,
        section_id=section_id,
        data_context=data_context,
        use_mock=use_mock,
        bypass_prompt_cache=bypass_prompt_cache,
        model_config=model_config
    )
    
    # Return delta that will be merged by LangGraph's state reducer
    # Since we're in a subgraph with LandingPageWorkflowState, we need to return results
    # that update autopopulation_langgraph_state
    # The agent_inputs and agent_outputs will be merged across all parallel sections
    return {
        "autopopulation_langgraph_state": {
            "agent_inputs": res["agent_input"],
            "agent_outputs": res["agent_output"],
            "logs": [{"level": "info", "msg": f"content_text_section_agent: completed for section {section_id}"}],
        }
    }
