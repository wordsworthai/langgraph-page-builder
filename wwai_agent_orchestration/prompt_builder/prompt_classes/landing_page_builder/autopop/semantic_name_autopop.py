from typing import Literal, Type
from pydantic import BaseModel
from wwai_agent_orchestration.constants import prompt_versions
from wwai_agent_orchestration.prompt_builder import prompt_builder_dataclass
from wwai_agent_orchestration.prompt_builder.prompt_builder import PromptSpec
from template_json_builder.models.autopop_dataclasses.prompt_spec.prompt_dataclasses import SectionElementSemanticNameInferenceInputModel, SectionElementSemanticNameInferenceOutputModel


class SemanticNameMappingSpec(PromptSpec):
    PROMPT_NAME: str = prompt_versions.SEMANTIC_NAME_MAPPING_PROMPT_NAME
    PROMPT_VERSION: int | str = prompt_versions.SEMANTIC_NAME_MAPPING_PROMPT_VERSION
    TASK: prompt_builder_dataclass.PromptModules = prompt_builder_dataclass.PromptModules.SEMANTIC_NAME_MAPPING
    MODE: Literal["text", "image"] = "text"
    
    InputModel = SectionElementSemanticNameInferenceInputModel
    OutputModel: Type[BaseModel] = SectionElementSemanticNameInferenceOutputModel