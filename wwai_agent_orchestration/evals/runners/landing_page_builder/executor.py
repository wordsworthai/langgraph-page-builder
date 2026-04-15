"""Landing page workflow execution for preset_sections, landing_page, and template_selection modes."""

import sys
from typing import Any

from wwai_agent_orchestration.evals.types.eval_case import EvalCase

def _eval_log(msg: str) -> None:
    """Print eval progress to stderr (always visible, bypasses log config)."""
    print(f"[Eval] {msg}", file=sys.stderr, flush=True)


async def _stream_workflow(workflow: Any, workflow_input: Any) -> None:
    """Build stream kwargs from workflow input and run workflow.stream to completion."""
    from wwai_agent_orchestration.contracts.landing_page_builder.workflow_inputs import (
        build_stream_kwargs,
    )

    stream_kwargs = build_stream_kwargs(workflow_input)
    async for _ in workflow.stream(**stream_kwargs):
        pass


def _prepare_preset_sections_input(eval_case: EvalCase, thread_id: str) -> Any:
    """Deserialize and fill runtime fields for preset_sections workflow."""
    from wwai_agent_orchestration.contracts.landing_page_builder.workflow_inputs import (
        preset_sections_input_from_dict,
    )
    from wwai_agent_orchestration.utils.landing_page_builder.execution_config_utils import (
        create_execution_config,
    )

    psi_dict = eval_case.workflow_inputs["preset_sections_input"]
    psi = preset_sections_input_from_dict(psi_dict)
    psi.business_name = psi.business_name or ""
    psi.request_id = thread_id
    exec_config = create_execution_config(
        section_ids=psi.section_ids,
        use_mock_autopopulation=False
    )
    psi.execution_config = exec_config.model_dump() if hasattr(exec_config, "model_dump") else exec_config
    return psi


def _prepare_landing_page_input(eval_case: EvalCase, thread_id: str) -> Any:
    """Deserialize and fill runtime fields for landing_page workflow."""
    from wwai_agent_orchestration.contracts.landing_page_builder.workflow_inputs import (
        landing_page_input_from_dict,
    )
    from wwai_agent_orchestration.utils.landing_page_builder.execution_config_utils import (
        create_execution_config,
    )

    lpi_dict = eval_case.workflow_inputs["landing_page_input"]
    lpi = landing_page_input_from_dict(lpi_dict)
    lpi.business_name = lpi.business_name or ""
    lpi.request_id = thread_id
    exec_config = create_execution_config()
    lpi.execution_config = exec_config.model_dump() if hasattr(exec_config, "model_dump") else exec_config
    return lpi


def _prepare_template_selection_input(eval_case: EvalCase, thread_id: str) -> Any:
    """Deserialize and fill runtime fields for template_selection workflow."""
    from wwai_agent_orchestration.contracts.landing_page_builder.workflow_inputs import (
        template_selection_input_from_dict,
    )
    from wwai_agent_orchestration.utils.landing_page_builder.execution_config_utils import (
        create_execution_config,
    )

    tsi_dict = eval_case.workflow_inputs["template_selection_input"]
    tsi = template_selection_input_from_dict(tsi_dict)
    tsi.business_name = tsi.business_name or ""
    tsi.request_id = thread_id
    exec_config = create_execution_config()
    tsi.execution_config = exec_config.model_dump() if hasattr(exec_config, "model_dump") else exec_config
    return tsi


async def execute_landing_page_workflow(
    eval_case: EvalCase,
    thread_id: str,
    workflow_config: dict[str, Any],
) -> Any:
    """Execute landing page workflow based on workflow_mode."""
    from wwai_agent_orchestration.agent_workflows.landing_page_builder.workflows.workflow_factory import (
        LandingPageWorkflowFactory,
    )

    _eval_log(
        f"Starting workflow case_id={eval_case.case_id} thread_id={thread_id} mode={eval_case.workflow_mode}"
    )
    workflow = LandingPageWorkflowFactory.create(eval_case.workflow_mode, workflow_config)

    if eval_case.workflow_mode == "preset_sections":
        psi = _prepare_preset_sections_input(eval_case, thread_id)
        await _stream_workflow(workflow, psi)
        return workflow

    if eval_case.workflow_mode == "landing_page":
        lpi = _prepare_landing_page_input(eval_case, thread_id)
        await _stream_workflow(workflow, lpi)
        return workflow

    if eval_case.workflow_mode == "template_selection":
        tsi = _prepare_template_selection_input(eval_case, thread_id)
        await _stream_workflow(workflow, tsi)
        return workflow

    raise ValueError(f"Unsupported workflow_mode: {eval_case.workflow_mode}")
