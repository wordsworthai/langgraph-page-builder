"""OpenAI provider adapter with timeout/retry behavior."""

from __future__ import annotations

import asyncio
from typing import Any, Optional


def _is_gpt5_model(model: str) -> bool:
    model_lower = (model or "").lower()
    return model_lower.startswith("gpt-5") or model_lower.startswith("gpt5") or model_lower.startswith("o1") or model_lower.startswith("o3")


class OpenAIJudgeProvider:
    """OpenAI provider wrapper for judge calls."""

    def __init__(self, *, api_key: Optional[str] = None, client: Any | None = None):
        if client is not None:
            self._client = client
        else:
            import openai

            self._client = openai.OpenAI(api_key=api_key)

    def _invoke_once(self, *, model: str, system: str, user: str, temperature: float) -> str:
        if _is_gpt5_model(model):
            prompt = f"{system}\n\n---\n\n{user}" if system else user
            response = self._client.responses.create(
                model=model,
                reasoning={"effort": "none"},
                input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
            )
            text = ""
            for item in getattr(response, "output", []) or []:
                for content_item in getattr(item, "content", []) or []:
                    text += getattr(content_item, "text", "") or ""
            return text.strip()

        response = self._client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system or "You are a concise evaluator."},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=4000,
        )
        return (response.choices[0].message.content or "").strip()

    async def invoke(
        self,
        *,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.3,
        timeout_s: float = 30.0,
        max_retries: int = 2,
    ) -> str:
        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(
                        self._invoke_once,
                        model=model,
                        system=system,
                        user=user,
                        temperature=temperature,
                    ),
                    timeout=timeout_s,
                )
            except Exception as exc:  # noqa: PERF203
                last_error = exc
                if attempt >= max_retries:
                    break
                await asyncio.sleep(0.2 * (2**attempt))
        raise RuntimeError(f"OpenAI judge invocation failed: {last_error}")

