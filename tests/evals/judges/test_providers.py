import asyncio

from wwai_agent_orchestration.evals.judges.providers.anthropic_provider import (
    AnthropicJudgeProvider,
)
from wwai_agent_orchestration.evals.judges.providers.openai_provider import (
    OpenAIJudgeProvider,
)


class _FakeMessage:
    def __init__(self, text):
        self.text = text


class _FakeChoice:
    def __init__(self, text):
        self.message = type("Message", (), {"content": text})()


class _FakeOpenAIClient:
    def __init__(self, fail_first=False):
        self.fail_first = fail_first
        self.calls = 0
        self.chat = type("Chat", (), {"completions": self})()
        self.responses = self

    def create(self, **_kwargs):
        self.calls += 1
        if self.fail_first and self.calls == 1:
            raise RuntimeError("transient openai error")
        if "reasoning" in _kwargs:
            return type(
                "Resp",
                (),
                {"output": [type("Item", (), {"content": [type("Content", (), {"text": '{"ok":true}'})()]})()]},
            )()
        return type("Resp", (), {"choices": [_FakeChoice('{"ok":true}')]})()


class _FakeAnthropicClient:
    def __init__(self, fail_first=False):
        self.fail_first = fail_first
        self.calls = 0
        self.messages = self

    def create(self, **_kwargs):
        self.calls += 1
        if self.fail_first and self.calls == 1:
            raise RuntimeError("transient anthropic error")
        return type("Resp", (), {"content": [_FakeMessage('{"ok":true}') ]})()


def test_openai_provider_retries_and_returns_text():
    provider = OpenAIJudgeProvider(client=_FakeOpenAIClient(fail_first=True))
    text = asyncio.run(
        provider.invoke(
            model="gpt-4o-mini",
            system="sys",
            user="user",
            max_retries=2,
            timeout_s=5,
        )
    )
    assert '"ok":true' in text


def test_anthropic_provider_retries_and_returns_text():
    provider = AnthropicJudgeProvider(client=_FakeAnthropicClient(fail_first=True))
    text = asyncio.run(
        provider.invoke(
            model="claude-sonnet",
            system="sys",
            user="user",
            max_retries=2,
            timeout_s=5,
        )
    )
    assert '"ok":true' in text

