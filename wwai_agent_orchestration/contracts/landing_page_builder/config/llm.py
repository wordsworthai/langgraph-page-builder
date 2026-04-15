"""
LLM and prompt-version configuration for Landing Page Builder Workflow.
"""

from dataclasses import dataclass

@dataclass
class LLMConfig:
    """Model and prompt versions for all LLM nodes."""

    run_on_worker: bool = False
    model_name: str = "gpt-4.1"
    llm_provider: str = "openai"
    temperature: float = 0.7