"""Typed schemas for template eval LLM judge outputs."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, ValidationError, model_validator


class TemplateScore(BaseModel):
    template_index: int
    score: float = Field(ge=1, le=10)
    reasoning: str
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)


class RequiredCheck(BaseModel):
    l0: str
    expected: bool = True
    present_in_templates: List[bool] = Field(default_factory=list)
    notes: Optional[str] = None


class RecommendedCheck(BaseModel):
    l0: str
    present_in_templates: List[bool] = Field(default_factory=list)
    notes: Optional[str] = None


class AntiPatternCheck(BaseModel):
    pattern: str
    violated_in_templates: List[bool] = Field(default_factory=list)
    severity: Literal["critical", "high", "medium", "low"]
    notes: Optional[str] = None


class RequiredCompliance(BaseModel):
    total: int
    passed: int
    checks: List[RequiredCheck] = Field(default_factory=list)


class RecommendedCompliance(BaseModel):
    total: int
    present: int
    checks: List[RecommendedCheck] = Field(default_factory=list)


class AntiPatternCompliance(BaseModel):
    total: int
    violations: int
    checks: List[AntiPatternCheck] = Field(default_factory=list)


class GuidelinesCompliance(BaseModel):
    required: RequiredCompliance
    recommended: RecommendedCompliance
    anti_patterns: AntiPatternCompliance


class TemplateEvalJudgeResult(BaseModel):
    template_scores: List[TemplateScore] = Field(default_factory=list)
    guidelines_compliance: GuidelinesCompliance
    overall_assessment: str
    best_template_index: int
    average_score: Optional[float] = None
    compliance_score: Optional[float] = None
    parse_error: bool = False
    parse_error_reason: Optional[str] = None
    raw_response: Optional[str] = None

    @model_validator(mode="after")
    def validate_best_template_index(self) -> "TemplateEvalJudgeResult":
        if self.template_scores and self.best_template_index not in [
            score.template_index for score in self.template_scores
        ]:
            raise ValueError("best_template_index must reference one of template_scores entries")
        return self


def parse_template_eval_result(payload: dict, raw_response: str | None = None) -> TemplateEvalJudgeResult:
    """Strictly validate template eval result payload into typed schema."""
    try:
        return TemplateEvalJudgeResult.model_validate(payload)
    except ValidationError as exc:
        return TemplateEvalJudgeResult(
            template_scores=[],
            guidelines_compliance=GuidelinesCompliance(
                required=RequiredCompliance(total=0, passed=0, checks=[]),
                recommended=RecommendedCompliance(total=0, present=0, checks=[]),
                anti_patterns=AntiPatternCompliance(total=0, violations=0, checks=[]),
            ),
            overall_assessment="parse_error",
            best_template_index=0,
            average_score=None,
            compliance_score=None,
            parse_error=True,
            parse_error_reason=str(exc),
            raw_response=raw_response,
        )
