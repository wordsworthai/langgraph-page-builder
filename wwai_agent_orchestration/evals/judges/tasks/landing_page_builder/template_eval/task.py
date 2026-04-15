"""Template eval judge task and instance."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict

from wwai_agent_orchestration.evals.judges.base import BaseJudgeTask, BaseJudgeTaskInstance
from wwai_agent_orchestration.evals.judges.tasks.landing_page_builder.template_eval.guidelines import (
    format_guidelines_for_prompt,
)
from wwai_agent_orchestration.evals.types.landing_page_builder.judge import parse_template_eval_result


class TemplateEvalJudgeTask(BaseJudgeTask):
    TASK_NAME = "template_eval"
    PROMPT_VERSION = "v1"

    def get_prompt_dir(self) -> Path:
        return Path(__file__).resolve().parent / "prompts"


class TemplateEvalJudgeTaskInstance(BaseJudgeTaskInstance):
    """Judge instance for template selection style outputs."""

    def _get_website_context_from_inputs(self, inputs: Dict[str, Any]) -> tuple[str, str]:
        """Extract website_intention and website_tone from workflow_inputs (nested or flat)."""
        for key in ("template_selection_input", "landing_page_input", "preset_sections_input"):
            nested = inputs.get(key) or {}
            wc = nested.get("website_context") or {}
            if wc:
                return (
                    wc.get("website_intention") or "",
                    wc.get("website_tone") or "",
                )
        return (
            inputs.get("website_intention") or "",
            inputs.get("website_tone") or "",
        )

    def build_input(self) -> Dict[str, Any]:
        run = self.run
        state = self.state
        inputs = run.get("inputs") or {}
        intention, tone = self._get_website_context_from_inputs(inputs)
        task_details = run.get("task_details") or {}
        business_context: Dict[str, Any] = {
            "business_id": task_details.get("business_id"),
            "business_name": state.get("business_name") or "",
            "sector": state.get("derived_sector") or state.get("sector") or "",
            "website_intention": intention or task_details.get("website_intention") or "",
            "website_tone": tone,
        }
        google_data = state.get("google_maps_data")
        if google_data:
            business_context["google_data"] = {
                "display_name": google_data.get("display_name"),
                "primary_type": google_data.get("primary_type_display") or google_data.get("primary_type"),
                "rating": google_data.get("rating"),
                "review_count": google_data.get("review_count"),
            }
        yelp_data = state.get("yelp_data")
        if yelp_data:
            business_context["yelp_data"] = {
                "business_name": yelp_data.get("business_name"),
                "categories": yelp_data.get("categories", [])[:5],
                "rating": yelp_data.get("rating"),
            }
        return business_context

    def build_output_for_eval(self) -> Dict[str, Any]:
        state = self.state
        templates = (
            state.get("refined_templates")
            or state.get("templates")
            or self.output.get("raw_output", {}).get("templates")
            or []
        )
        formatted_templates = []
        for i, template in enumerate(templates):
            sections = template.get("section_info") or template.get("sections") or []
            formatted_sections = []
            for j, section in enumerate(sections):
                formatted_sections.append(
                    {
                        "order": section.get("section_index", j + 1),
                        "section_l0": section.get("section_l0"),
                        "section_l1": section.get("section_l1"),
                        "reasoning": section.get("reasoning", ""),
                    }
                )
            formatted_templates.append(
                {
                    "template_index": i,
                    "template_name": template.get("template_name", f"template_{i+1}"),
                    "section_count": len(formatted_sections),
                    "sections": formatted_sections,
                }
            )
        return {"templates": formatted_templates, "template_count": len(formatted_templates)}

    def get_filled_prompt(self) -> Dict[str, str]:
        template = self.task.load_prompt_template()
        input_data = self.build_input()
        output_data = self.build_output_for_eval()
        intent = input_data.get("website_intention", "lead_generation")
        try:
            guidelines_str = format_guidelines_for_prompt(intent)
        except ValueError:
            guidelines_str = format_guidelines_for_prompt("lead_generation")

        user = template.get("user", "")
        user = user.replace("{{input}}", json.dumps(input_data, indent=2, default=str))
        user = user.replace("{{output}}", json.dumps(output_data, indent=2, default=str))
        user = user.replace("{{guidelines}}", guidelines_str)
        return {"system": template.get("system", ""), "user": user}

    def parse_llm_response(self, response: str) -> Dict[str, Any]:
        try:
            payload = json.loads(response)
        except json.JSONDecodeError:
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
            if json_match:
                try:
                    payload = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    payload = {"parse_error": True}
            else:
                object_match = re.search(r"\{[\s\S]*\}", response)
                if object_match:
                    try:
                        payload = json.loads(object_match.group(0))
                    except json.JSONDecodeError:
                        payload = {"parse_error": True}
                else:
                    payload = {"parse_error": True}

        if payload.get("parse_error"):
            validated = parse_template_eval_result({}, raw_response=response)
            return validated.model_dump()

        template_scores = payload.get("template_scores", [])
        if template_scores:
            scores = [item.get("score") for item in template_scores if isinstance(item.get("score"), (int, float))]
            payload["average_score"] = round(sum(scores) / len(scores), 2) if scores else None
            compliance = payload.get("guidelines_compliance", {})
            required = compliance.get("required", {})
            anti_patterns = compliance.get("anti_patterns", {})
            req_total = required.get("total", 0) or 1
            req_passed = required.get("passed", 0)
            anti_total = anti_patterns.get("total", 0) or 1
            anti_violations = anti_patterns.get("violations", 0)
            required_score = req_passed / req_total
            anti_score = 1 - (anti_violations / anti_total)
            payload["compliance_score"] = round((required_score * 0.6 + anti_score * 0.4) * 10, 2)

        validated = parse_template_eval_result(payload, raw_response=response)
        return validated.model_dump()

