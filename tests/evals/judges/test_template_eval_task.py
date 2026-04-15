from wwai_agent_orchestration.evals.judges.tasks.landing_page_builder.template_eval.task import (
    TemplateEvalJudgeTask,
    TemplateEvalJudgeTaskInstance,
)


def _instance():
    return TemplateEvalJudgeTaskInstance(
        task=TemplateEvalJudgeTask(),
        run={
            "business_id": "biz_1",
            "website_intention": "lead_generation",
            "inputs": {"website_intention": "lead_generation", "website_tone": "professional"},
        },
        state={
            "business_name": "Biz Name",
            "derived_sector": "services",
            "refined_templates": [
                {
                    "template_name": "template_a",
                    "section_info": [{"section_l0": "Hero", "section_l1": "Text Overlay"}],
                }
            ],
        },
        output={},
    )


def test_parse_valid_template_eval_response():
    response = """
    {
      "template_scores": [
        {"template_index": 0, "score": 8, "reasoning": "good", "strengths": [], "weaknesses": []}
      ],
      "guidelines_compliance": {
        "required": {"total": 2, "passed": 1, "checks": []},
        "recommended": {"total": 2, "present": 1, "checks": []},
        "anti_patterns": {"total": 2, "violations": 0, "checks": []}
      },
      "overall_assessment": "solid",
      "best_template_index": 0
    }
    """
    parsed = _instance().parse_llm_response(response)
    assert parsed["parse_error"] is False
    assert parsed["average_score"] == 8.0
    assert parsed["compliance_score"] is not None


def test_parse_invalid_response_sets_parse_error():
    parsed = _instance().parse_llm_response("not-json")
    assert parsed["parse_error"] is True
    assert parsed["raw_response"] == "not-json"

