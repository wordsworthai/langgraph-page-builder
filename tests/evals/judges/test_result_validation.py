from wwai_agent_orchestration.evals.types.landing_page_builder.judge import parse_template_eval_result


def test_result_validation_accepts_valid_payload():
    payload = {
        "template_scores": [
            {"template_index": 0, "score": 7.5, "reasoning": "ok", "strengths": [], "weaknesses": []}
        ],
        "guidelines_compliance": {
            "required": {"total": 1, "passed": 1, "checks": []},
            "recommended": {"total": 1, "present": 1, "checks": []},
            "anti_patterns": {"total": 1, "violations": 0, "checks": []},
        },
        "overall_assessment": "good",
        "best_template_index": 0,
    }
    result = parse_template_eval_result(payload, raw_response="{}")
    assert result.parse_error is False


def test_result_validation_flags_invalid_payload():
    payload = {
        "template_scores": [{"template_index": 0, "score": 99, "reasoning": "bad"}],
    }
    result = parse_template_eval_result(payload, raw_response="bad")
    assert result.parse_error is True
    assert result.raw_response == "bad"

