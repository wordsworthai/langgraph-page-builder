"""Deterministic fixtures for metrics policy tests."""


def template_selection_bundle():
    return {
        "eval_set_id": "set_tpl",
        "task_type": "template_selection",
        "runs": [
            {
                "run_id": "run_s1",
                "status": "completed",
                "task_type": "template_selection",
                "workflow_mode": "template_selection",
            },
            {
                "run_id": "run_s2",
                "status": "failed",
                "task_type": "template_selection",
                "workflow_mode": "template_selection",
            },
        ],
        "human_feedback": [
            {
                "run_id": "run_s1",
                "task_type": "template_selection",
                "feedback": {
                    "template_structure_issue": False,
                    "section_selection_issue": False,
                    "section_ordering_issue": False,
                    "section_count_issue": False,
                    "intent_fit_issue": False,
                },
            },
            {
                "run_id": "run_s2",
                "task_type": "template_selection",
                "feedback": {
                    "template_structure_issue": True,
                    "section_selection_issue": False,
                    "section_ordering_issue": False,
                    "section_count_issue": False,
                    "intent_fit_issue": False,
                },
            },
        ],
        "judge_results": [
            {"run_id": "run_s1", "result": {"average_score": 0.82, "parse_error": None}},
            {"run_id": "run_s2", "result": {"average_score": 0.76, "parse_error": None}},
        ],
    }


def landing_page_bundle():
    return {
        "eval_set_id": "set_lp",
        "task_type": "landing_page",
        "runs": [
            {
                "run_id": "run_l1",
                "status": "completed",
                "task_type": "landing_page",
                "workflow_mode": "landing_page_builder",
            },
            {
                "run_id": "run_l2",
                "status": "completed",
                "task_type": "landing_page",
                "workflow_mode": "landing_page_builder",
            },
        ],
        "human_feedback": [
            {
                "run_id": "run_l1",
                "task_type": "landing_page",
                "feedback": {"overall_readiness": "pass", "widget_code_issue": False},
            },
            {
                "run_id": "run_l2",
                "task_type": "landing_page",
                "feedback": {"overall_readiness": "fail", "widget_code_issue": True},
            },
        ],
        "judge_results": [
            {"run_id": "run_l1", "result": {"average_score": 0.91, "parse_error": None}},
            {"run_id": "run_l2", "result": {"average_score": 0.4, "parse_error": None}},
        ],
    }


def section_coverage_bundle():
    return {
        "eval_set_id": "set_sc",
        "task_type": "section_coverage",
        "runs": [
            {
                "run_id": "run_sc1",
                "status": "completed",
                "task_type": "section_coverage",
                "workflow_mode": "preset_sections",
            },
            {
                "run_id": "run_sc2",
                "status": "completed",
                "task_type": "section_coverage",
                "workflow_mode": "preset_sections",
            },
        ],
        "human_feedback": [
            {
                "run_id": "run_sc1",
                "task_type": "section_coverage",
                "feedback": {"has_breaking_section": False},
            },
            {
                "run_id": "run_sc2",
                "task_type": "section_coverage",
                "feedback": {"has_breaking_section": True},
            },
        ],
        "judge_results": [
            {"run_id": "run_sc1", "result": {"average_score": 0.9, "parse_error": None}},
            {"run_id": "run_sc2", "result": {"average_score": 0.5, "parse_error": None}},
        ],
    }
