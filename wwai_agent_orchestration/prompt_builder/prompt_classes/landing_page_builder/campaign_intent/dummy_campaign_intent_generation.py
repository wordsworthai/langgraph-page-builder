"""
Screenshot Intent Extraction Prompt Class.

Extracts campaign intent from full page screenshots using LLM analysis.
"""

from typing import Dict, Optional, Type
from pydantic import BaseModel, Field

from wwai_agent_orchestration.constants import prompt_versions
from wwai_agent_orchestration.prompt_builder import prompt_builder_dataclass
from wwai_agent_orchestration.prompt_builder.prompt_builder import PromptSpec


class TextQueryOutput(BaseModel):
    """Output model for screenshot intent extraction"""
    campaign_query: str = Field(
        description="Dummy Textual Query of the campaign for which this page has been created. "
        "Include important information such as offers, type of page (multi product, single product), "
        "page positioning, intent etc."
    )


class ScreenshotIntentExtractionInput(BaseModel):
    """Input for screenshot intent extraction - image only, no template variables"""
    image_labels: Dict[str, str] = Field(
        description="Dict mapping image URL to label. E.g. {url: '**Above image**: Full page screenshot for campaign intent analysis'}"
    )


class ScreenshotIntentExtractionSpec(PromptSpec):
    """PromptSpec for extracting campaign intent from full page screenshots."""
    PROMPT_NAME: str = prompt_versions.SCREENSHOT_INTENT_EXTRACTION_PROMPT_NAME
    PROMPT_VERSION: Optional[str] = prompt_versions.SCREENSHOT_INTENT_EXTRACTION_PROMPT_VERSION
    TASK: prompt_builder_dataclass.PromptModules = prompt_builder_dataclass.PromptModules.DUMMY_CAMPAIGN_INTENT_GENERATION
    MODE: str = "image"
    InputModel = ScreenshotIntentExtractionInput
    OutputModel: Type[BaseModel] = TextQueryOutput
