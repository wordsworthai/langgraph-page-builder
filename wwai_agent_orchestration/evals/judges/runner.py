"""Generic runner for judge task instances."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from wwai_agent_orchestration.evals.judges.base import BaseJudgeTask, BaseJudgeTaskInstance
from wwai_agent_orchestration.evals.judges.providers.anthropic_provider import (
    AnthropicJudgeProvider,
)
from wwai_agent_orchestration.evals.judges.providers.openai_provider import OpenAIJudgeProvider


@dataclass
class JudgeRunner:
    """Runs a judge task against one run + state + extracted output."""

    provider: str = "openai"
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.3
    timeout_s: float = 30.0
    max_retries: int = 2
    openai_provider: Optional[OpenAIJudgeProvider] = None
    anthropic_provider: Optional[AnthropicJudgeProvider] = None

    def _resolve_provider(self):
        if self.provider == "anthropic":
            return self.anthropic_provider or AnthropicJudgeProvider()
        return self.openai_provider or OpenAIJudgeProvider()

    async def run(
        self,
        *,
        task: BaseJudgeTask,
        task_instance_cls: type[BaseJudgeTaskInstance],
        run: Dict[str, Any],
        state: Dict[str, Any],
        output: Dict[str, Any],
    ) -> Dict[str, Any]:
        instance = task_instance_cls(run=run, state=state, output=output, task=task)
        prompt = instance.get_filled_prompt()
        provider = self._resolve_provider()
        response = await provider.invoke(
            model=self.model_name,
            system=prompt.get("system", ""),
            user=prompt.get("user", ""),
            temperature=self.temperature,
            timeout_s=self.timeout_s,
            max_retries=self.max_retries,
        )
        parsed = instance.parse_llm_response(response)
        parsed["prompt_version"] = instance.get_prompt_label()
        parsed["model_name"] = self.model_name
        return parsed

