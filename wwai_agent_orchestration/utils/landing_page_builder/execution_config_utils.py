"""Execution config creation utilities for the landing page builder."""

from wwai_agent_orchestration.contracts.landing_page_builder.execution_config import (
    ExecutionConfig,
    RoutingConfig,
    CompilationConfig,
    AutopopConfig,
    ReflectionConfig,
)


def create_execution_config(
    section_ids: list = None,
    enable_screenshot_compilation: bool = False,
    enable_html_compilation: bool = True,
    use_mock_autopopulation: bool = True,
    enable_reflection: bool = False,
    max_iterations: int = 1,
) -> ExecutionConfig:
    """
    Create execution config.

    Args:
        section_ids: Optional list of section IDs (used by PresetSectionsLandingPageWorkflow)
        enable_screenshot_compilation: If True, captures screenshots from compiled HTML.
        enable_html_compilation: If True, runs HTML compilation.
        use_mock_autopopulation: If True, uses mock data in autopopulation.
    """
    return ExecutionConfig(
        routing=RoutingConfig(section_ids=section_ids or None),
        compilation=CompilationConfig(
            enable_html_compilation=enable_html_compilation,
            enable_screenshot_compilation=enable_screenshot_compilation,
        ),
        autopop=AutopopConfig(use_mock_autopopulation=use_mock_autopopulation),
        reflection=ReflectionConfig(
            enable_reflection=enable_reflection,
            max_iterations=max_iterations,
        ),
    )
