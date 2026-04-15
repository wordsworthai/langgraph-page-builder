"""
LandingPageBuilderEnvConfig: composes five sub-configs and flattens to configurable dict.
Reflection (enable_reflection, max_iterations) is per-request via ExecutionConfig, not here.
"""

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Dict

from wwai_agent_orchestration.contracts.landing_page_builder.config.llm import LLMConfig
from wwai_agent_orchestration.contracts.landing_page_builder.config.api import ExternalAPIConfig
from wwai_agent_orchestration.contracts.landing_page_builder.config.section_repo import SectionRepoConfig
from wwai_agent_orchestration.contracts.landing_page_builder.config.database_save import DatabaseSaveConfig


@dataclass
class LandingPageBuilderEnvConfig:
    """
    Configuration for Landing Page Builder Workflow.
    Composes five sub-dataclasses; exposes flat dict via to_configurable_dict().
    """

    llm: LLMConfig = field(default_factory=LLMConfig)
    external_api: ExternalAPIConfig = field(default_factory=ExternalAPIConfig)
    section_repo: SectionRepoConfig = field(default_factory=SectionRepoConfig)
    database_save: DatabaseSaveConfig = field(default_factory=DatabaseSaveConfig)

    def to_configurable_dict(self) -> Dict[str, Any]:
        """
        Flatten all sub-configs into one dict for LangGraph configurable.
        Keys are disjoint across sub-dataclasses; merge order is fixed.
        """
        subs = [
            self.llm,
            self.external_api,
            self.section_repo,
            self.database_save,
        ]
        parts = [dataclasses.asdict(s) for s in subs]
        total_keys = sum(len(p) for p in parts)
        merged = {}
        for part in parts:
            merged.update(part)
        assert len(merged) == total_keys, (
            "Config key overlap: two sub-dataclasses share a key. "
            f"Expected {total_keys} keys, got {len(merged)}."
        )
        return merged


def get_dev_config() -> LandingPageBuilderEnvConfig:
    """Development configuration - fast, minimal; DB save off."""
    return LandingPageBuilderEnvConfig(
        section_repo=SectionRepoConfig(filter_type="ALL_TYPES"),
        database_save=DatabaseSaveConfig(enable_database_save=False),
    )


def get_staging_config() -> LandingPageBuilderEnvConfig:
    """Staging configuration - mirrors production."""
    return LandingPageBuilderEnvConfig(
        section_repo=SectionRepoConfig(filter_type="ALL_TYPES"),
        database_save=DatabaseSaveConfig(enable_database_save=True),
    )


def get_production_config() -> LandingPageBuilderEnvConfig:
    """Production configuration - full features."""
    return LandingPageBuilderEnvConfig(
        section_repo=SectionRepoConfig(filter_type="ALL_TYPES"),
        database_save=DatabaseSaveConfig(
            enable_database_save=True,
            fail_on_save_error=True,
        ),
    )
