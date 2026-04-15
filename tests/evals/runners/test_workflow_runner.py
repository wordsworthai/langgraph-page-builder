import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from wwai_agent_orchestration.evals.checkpoints.checkpoint_reader import CheckpointReader
from wwai_agent_orchestration.evals.runners.run_output_writer import EvalRunOutputWriter
from wwai_agent_orchestration.evals.graph_output_extractors.output_extractor_base import (
    BaseOutputExtractor,
    ExtractorRegistry,
)
from wwai_agent_orchestration.evals.runners.workflow_runner import (
    RunnerDependencies,
    run_case,
)
from wwai_agent_orchestration.evals.types.eval_case import EvalCase
from wwai_agent_orchestration.evals.types.landing_page_builder import TemplateSelectionOutput


class _NoopExtractor(BaseOutputExtractor):
    def extract(self, final_state, history=None):
        return TemplateSelectionOutput(
            template_id=final_state.get("template_id"),
            raw_output=final_state,
        )


class _WorkflowState:
    def __init__(self, values):
        self.values = values


class _WorkflowGraph:
    def __init__(self, values):
        self._values = values

    def get_state(self, _config):
        return _WorkflowState(self._values)


class _Workflow:
    def __init__(self, values):
        self.config = {}
        self.graph = _WorkflowGraph(values)


async def _success_executor(_case, _thread_id, _cfg):
    return _Workflow({"generation_version_id": "gen_1", "template_id": "tpl_1"})


async def _failing_executor(_case, _thread_id, _cfg):
    raise RuntimeError("executor failed")


def _build_case():
    return EvalCase(
        case_id="case_1",
        eval_set_id="set_1",
        eval_type="template_selection",
        workflow_mode="template_selection",
        set_inputs={
            "business_id": "biz_1",
            "business_index": 0,
            "website_intention": "lead_generation",
            "website_tone": "professional",
        },
        workflow_inputs={
            "template_selection_input": {
                "business_name": "",
                "business_id": "biz_1",
                "request_id": "",
                "generic_context": {"query": ""},
                "website_context": {"website_intention": "lead_generation", "website_tone": "professional"},
                "external_data_context": {"yelp_url": ""},
            },
        },
    )


def _build_registry():
    registry = ExtractorRegistry()
    registry.register("template_selection", _NoopExtractor())
    return registry


def test_run_case_success():
    deps = RunnerDependencies(
        checkpoint_reader=CheckpointReader(history_fetcher=lambda _: []),
        extractor_registry=_build_registry(),
        workflow_executor=_success_executor,
    )
    result = asyncio.run(run_case(_build_case(), deps))
    assert result.run_record.status == "completed"
    assert result.run_record.generation_version_id == "gen_1"
    assert result.output.template_id == "tpl_1"


def test_run_case_failure():
    deps = RunnerDependencies(
        checkpoint_reader=CheckpointReader(history_fetcher=lambda _: []),
        extractor_registry=_build_registry(),
        workflow_executor=_failing_executor,
    )
    result = asyncio.run(run_case(_build_case(), deps))
    assert result.run_record.status == "failed"
    assert "executor failed" in (result.run_record.error_message or "")


def test_run_case_with_run_output_writer_writes_file():
    """When run_output_writer is set, run_case writes final state to file on success."""
    with TemporaryDirectory() as tmpdir:
        writer = EvalRunOutputWriter(tmpdir)
        deps = RunnerDependencies(
            checkpoint_reader=CheckpointReader(history_fetcher=lambda _: []),
            extractor_registry=_build_registry(),
            workflow_executor=_success_executor,
            run_output_writer=writer,
        )
        result = asyncio.run(run_case(_build_case(), deps))
        assert result.run_record.status == "completed"
        out_path = Path(tmpdir) / "final_state_{}_{}.json".format(
            result.run_record.run_id, _build_case().case_id
        )
        assert out_path.exists()
        payload = json.loads(out_path.read_text())
        assert payload["case_id"] == "case_1"
        assert payload["workflow_mode"] == "template_selection"
        assert payload["extractor_output"]["template_id"] == "tpl_1"

