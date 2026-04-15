"""Base contracts for output extractors."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseOutputExtractor(ABC):
    """Base extractor contract for workflow-mode-specific final output mapping."""

    @abstractmethod
    def extract(self, final_state: Dict[str, Any], history: list[Dict[str, Any]] | None = None) -> Any:
        """Map final state and optional checkpoint history into typed output."""


class ExtractorRegistry:
    """Simple workflow_mode to extractor registry."""

    def __init__(self) -> None:
        self._registry: dict[str, BaseOutputExtractor] = {}

    def register(self, workflow_mode: str, extractor: BaseOutputExtractor) -> None:
        self._registry[workflow_mode] = extractor

    def resolve(self, workflow_mode: str) -> BaseOutputExtractor:
        if workflow_mode not in self._registry:
            raise ValueError(f"No extractor registered for workflow_mode={workflow_mode}")
        return self._registry[workflow_mode]

