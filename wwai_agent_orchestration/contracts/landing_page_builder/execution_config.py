# contracts/execution_config.py
"""
Execution configuration for SMB workflow routing and caching.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List


class CacheStrategy(BaseModel):
    """Cache control strategy"""
    use_cache: bool = False  # Enable/disable caching globally (off by default)
    use_template_cache: bool = Field(
        default=True,
        description="Enable/disable template/section cache checking and saving"
    )
    version: str = "v1"  # Version for cache invalidation
    node_overrides: Dict[str, bool] = Field(
        default_factory=dict,
        description="Per-node cache enable override. node_name -> enabled. Missing/True = use cache."
    )


class RoutingConfig(BaseModel):
    """Workflow routing configuration"""
    section_ids: Optional[List[str]] = Field(
        default=None,
        description="Direct section IDs (used by PresetSectionsLandingPageWorkflow - bypass template selection)"
    )


class CompilationConfig(BaseModel):
    """Post-processing compilation configuration"""
    enable_html_compilation: bool = Field(
        default=True,
        description="If True, runs HTML compilation and optional screenshot capture. If False, skips HTML compilation (but template compilation always runs). Useful for production where HTML compilation is not needed."
    )
    enable_screenshot_compilation: bool = Field(
        default=False,
        description="If True, captures screenshots from compiled HTML after HTML compilation. Only applies if enable_html_compilation=True."
    )


class ReflectionConfig(BaseModel):
    """Template refinement (reflection) configuration"""
    enable_reflection: bool = Field(
        default=False,
        description="If True, template evaluator can loop back to template generation for refinement."
    )
    max_iterations: int = Field(
        default=1,
        description="Maximum template generation iterations when reflection is enabled."
    )


class AutopopConfig(BaseModel):
    """Autopopulation configuration"""
    use_mock_autopopulation: bool = Field(
        default=True,
        description="If True, uses mock data in autopopulation input builder. If False, uses real data."
    )


class PageContextExtractionConfig(BaseModel):
    """Page context extraction (Gemini, ScrapingBee, screenshot intent) configuration"""
    enable_gemini_context: bool = True
    enable_scraping_bee_text: bool = False
    enable_screenshot_intent: bool = False
    screenshot_use_base64_for_llm: bool = True
    bypass_gemini_cache: bool = False
    bypass_scraping_bee_cache: bool = False


DEFAULT_PAGE_CONTEXT_EXTRACTION_CONFIG = PageContextExtractionConfig()


class ExecutionConfig(BaseModel):
    """Runtime execution configuration for routing and caching"""

    routing: RoutingConfig = Field(default_factory=RoutingConfig)
    cache_strategy: CacheStrategy = Field(default_factory=CacheStrategy)
    compilation: CompilationConfig = Field(default_factory=CompilationConfig)
    reflection: ReflectionConfig = Field(default_factory=ReflectionConfig)
    autopop: AutopopConfig = Field(default_factory=AutopopConfig)
    page_context_extraction: PageContextExtractionConfig = Field(
        default_factory=PageContextExtractionConfig
    )

    class Config:
        json_schema_extra = {
            "example": {
                "routing": {"section_ids": None},
                "cache_strategy": {
                    "use_cache": False,
                    "use_template_cache": True,
                    "version": "v1",
                    "node_overrides": {"campaign_intent_synthesizer": False}
                },
                "compilation": {
                    "enable_html_compilation": True,
                    "enable_screenshot_compilation": False,
                },
                "reflection": {"enable_reflection": False, "max_iterations": 1},
                "autopop": {"use_mock_autopopulation": True},
                "page_context_extraction": {
                    "enable_gemini_context": True,
                    "enable_scraping_bee_text": False,
                    "enable_screenshot_intent": False,
                    "screenshot_use_base64_for_llm": True,
                    "bypass_gemini_cache": False,
                    "bypass_scraping_bee_cache": False,
                },
            }
        }
