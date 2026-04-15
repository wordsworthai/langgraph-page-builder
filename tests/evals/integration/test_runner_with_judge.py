import asyncio

from wwai_agent_orchestration.evals.checkpoints.checkpoint_reader import CheckpointReader
from wwai_agent_orchestration.evals.graph_output_extractors.output_extractor_base import (
    BaseOutputExtractor,
    ExtractorRegistry,
)
from wwai_agent_orchestration.evals.judges.integration import make_template_judge_evaluator
from wwai_agent_orchestration.evals.judges.runner import JudgeRunner
from wwai_agent_orchestration.evals.runners.batch_runner import run_eval_set
from wwai_agent_orchestration.evals.runners.workflow_runner import RunnerDependencies
from wwai_agent_orchestration.evals.types.eval_case import EvalCase
from wwai_agent_orchestration.evals.types.eval_set import EvalSet
from wwai_agent_orchestration.evals.types.landing_page_builder import TemplateSelectionOutput


class _FakeJudgeProvider:
    async def invoke(self, **_kwargs):
        return """
        {
          "template_scores": [
            {"template_index": 0, "score": 8, "reasoning": "good", "strengths": [], "weaknesses": []}
          ],
          "guidelines_compliance": {
            "required": {"total": 1, "passed": 1, "checks": []},
            "recommended": {"total": 1, "present": 1, "checks": []},
            "anti_patterns": {"total": 1, "violations": 0, "checks": []}
          },
          "overall_assessment": "good",
          "best_template_index": 0
        }
        """


class _Extractor(BaseOutputExtractor):
    def extract(self, final_state, history=None):
        return TemplateSelectionOutput(
            template_id="tpl_1",
            selected_template_index=0,
            raw_output={"templates": [{"template_name": "template_1", "section_info": []}]},
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


async def _executor(_case, _thread_id, _cfg):
    return _Workflow(
        {
            "business_name": "Biz",
            "derived_sector": "services",
            "refined_templates": [{"template_name": "template_1", "section_info": []}],
        }
    )


def test_batch_runner_with_optional_judge():
    case = EvalCase(
        case_id="case_j1",
        eval_set_id="set_j1",
        eval_type="template_selection",
        workflow_mode="template_selection",
        set_inputs={
            "business_id": "biz_1",
            "business_index": 0,
            "website_intention": "lead_generation",
        },
        workflow_inputs={
            "template_selection_input": {
                "business_id": "biz_1",
                "website_context": {"website_intention": "lead_generation", "website_tone": "professional"},
                "external_data_context": {},
            },
        },
    )
    eval_set = EvalSet(
        eval_set_id="set_j1",
        eval_type="template_selection",
        version="v1",
        seed=1,
        cases=[case],
    )

    registry = ExtractorRegistry()
    registry.register("template_selection", _Extractor())

    judge_runner = JudgeRunner(openai_provider=_FakeJudgeProvider())
    deps = RunnerDependencies(
        checkpoint_reader=CheckpointReader(history_fetcher=lambda _: []),
        extractor_registry=registry,
        workflow_executor=_executor,
        judge_evaluator=make_template_judge_evaluator(judge_runner=judge_runner),
    )
    summary = asyncio.run(run_eval_set(eval_set, deps, max_attempts=1))
    assert summary["completed"] == 1
    assert summary["judge_completed"] == 1
    assert summary["judge_failed"] == 0

