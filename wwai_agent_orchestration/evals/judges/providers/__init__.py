"""LLM provider adapters for judge execution."""

from wwai_agent_orchestration.evals.judges.providers.anthropic_provider import (
    AnthropicJudgeProvider,
)
from wwai_agent_orchestration.evals.judges.providers.openai_provider import OpenAIJudgeProvider

__all__ = ["OpenAIJudgeProvider", "AnthropicJudgeProvider"]

