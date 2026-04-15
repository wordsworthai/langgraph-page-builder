"""
Landing Page Builder Workflow configuration.

Sub-dataclasses: LLMConfig, ExternalAPIConfig, SectionRepoConfig, DatabaseSaveConfig.
Top-level: LandingPageBuilderEnvConfig with to_configurable_dict().
Presets: get_dev_config, get_staging_config, get_production_config.
Reflection (enable_reflection, max_iterations) is per-request via ExecutionConfig, not here.
"""

from wwai_agent_orchestration.contracts.landing_page_builder.config.llm import LLMConfig
from wwai_agent_orchestration.contracts.landing_page_builder.config.api import ExternalAPIConfig
from wwai_agent_orchestration.contracts.landing_page_builder.config.section_repo import SectionRepoConfig
from wwai_agent_orchestration.contracts.landing_page_builder.config.database_save import DatabaseSaveConfig
from wwai_agent_orchestration.contracts.landing_page_builder.config.main import (
    LandingPageBuilderEnvConfig,
    get_dev_config,
    get_staging_config,
    get_production_config,
)

__all__ = [
    "LLMConfig",
    "ExternalAPIConfig",
    "SectionRepoConfig",
    "DatabaseSaveConfig",
    "LandingPageBuilderEnvConfig",
    "get_dev_config",
    "get_staging_config",
    "get_production_config",
]
