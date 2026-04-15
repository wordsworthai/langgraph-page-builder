"""Anthropic provider adapter with timeout/retry behavior."""

from __future__ import annotations

import asyncio
from typing import Any, Optional


class AnthropicJudgeProvider:
    """Anthropic provider wrapper for judge calls."""

    def __init__(self, *, api_key: Optional[str] = None, client: Any | None = None):
        if client is not None:
            self._client = client
        else:
            import anthropic

            self._client = anthropic.Anthropic(api_key=api_key)

    def _invoke_once(self, *, model: str, system: str, user: str, temperature: float) -> str:
        response = self._client.messages.create(
            model=model,
            max_tokens=4000,
            system=system or "You are a concise evaluator.",
            messages=[{"role": "user", "content": user}],
            temperature=temperature,
        )
        if not response.content:
            return ""
        return (response.content[0].text or "").strip()

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
        raise RuntimeError(f"Anthropic judge invocation failed: {last_error}")

