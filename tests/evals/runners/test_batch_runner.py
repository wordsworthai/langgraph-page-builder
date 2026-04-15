import asyncio
from collections import defaultdict

from wwai_agent_orchestration.evals.checkpoints.checkpoint_reader import CheckpointReader
from wwai_agent_orchestration.evals.graph_output_extractors.output_extractor_base import (
    BaseOutputExtractor,
    ExtractorRegistry,
)
from wwai_agent_orchestration.evals.runners.batch_runner import run_eval_set
from wwai_agent_orchestration.evals.runners.workflow_runner import RunnerDependencies
from wwai_agent_orchestration.evals.types.eval_case import EvalCase
from wwai_agent_orchestration.evals.types.eval_set import EvalSet
from wwai_agent_orchestration.evals.types.landing_page_builder import LandingPageOutput


class _Extractor(BaseOutputExtractor):
    def extract(self, final_state, history=None):
        return LandingPageOutput(
            generation_version_id=final_state.get("generation_version_id"),
            raw_output=final_state,
        )


class _State:
    def __init__(self, values):
        self.values = values


class _Graph:
    def __init__(self, values):
        self._values = values

    def get_state(self, _config):
        return _State(self._values)


class _Workflow:
    def __init__(self, values):
        self.config = {}
        self.graph = _Graph(values)


def _build_eval_set():
    cases = []
    for i in range(3):
        cases.append(
            EvalCase(
                case_id=f"case_{i}",
                eval_set_id="set_batch",
                eval_type="landing_page",
                workflow_mode="landing_page",
                set_inputs={
                    "business_id": f"biz_{i}",
                    "business_index": i,
                    "website_intention": "lead_generation",
                },
                workflow_inputs={"website_intention": "lead_generation"},
            )
        )
    return EvalSet(
        eval_set_id="set_batch",
        eval_type="landing_page",
        version="v1",
        seed=1,
        cases=cases,
    )


def test_batch_runner_retries_and_completes():
    attempts = defaultdict(int)

    async def flaky_executor(eval_case, _thread_id, _cfg):
        attempts[eval_case.case_id] += 1
        if eval_case.case_id == "case_1" and attempts[eval_case.case_id] == 1:
            raise RuntimeError("transient failure")
        return _Workflow({"generation_version_id": f"gen_{eval_case.case_id}"})

    registry = ExtractorRegistry()
    registry.register("landing_page", _Extractor())

    deps = RunnerDependencies(
        checkpoint_reader=CheckpointReader(history_fetcher=lambda _: []),
        extractor_registry=registry,
        workflow_executor=flaky_executor,
    )
    summary = asyncio.run(
        run_eval_set(
            _build_eval_set(),
            deps,
            max_concurrency=2,
            max_attempts=2,
        )
    )
    assert summary["total_cases"] == 3
    assert summary["completed"] == 3
    assert summary["failed"] == 0
    assert attempts["case_1"] == 2

