from wwai_agent_orchestration.evals.judges.tasks.landing_page_builder.template_eval.task import (
    TemplateEvalJudgeTask,
    TemplateEvalJudgeTaskInstance,
)


def test_template_task_loads_system_user_prompt():
    task = TemplateEvalJudgeTask(prompt_version="v1")
    prompt = task.load_prompt_template()
    assert "system" in prompt and "user" in prompt
    assert "BUSINESS CONTEXT" in prompt["user"]


def test_template_instance_fills_prompt_placeholders():
    task = TemplateEvalJudgeTask()
    instance = TemplateEvalJudgeTaskInstance(
        task=task,
        run={"business_id": "biz_1", "inputs": {"website_intention": "lead_generation"}},
        state={"business_name": "Test Biz"},
        output={"raw_output": {"templates": []}},
    )
    prompt = instance.get_filled_prompt()
    assert "{{input}}" not in prompt["user"]
    assert "{{output}}" not in prompt["user"]
    assert "{{guidelines}}" not in prompt["user"]

