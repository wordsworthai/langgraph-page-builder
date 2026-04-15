from dataclasses import dataclass
from abc import ABC, abstractmethod
import os
import re
import json
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, List, Union, Dict, Any, Literal, Type
from wwai_agent_orchestration.prompt_builder import prompt_builder_dataclass
from pydantic import BaseModel
from wwai_agent_orchestration.utils.llm.model_utils import create_model
from wwai_agent_orchestration.utils.llm.schema_utils import json_schema_openai_strict
from langchain_core.prompts import PromptTemplate
from langchain_core.callbacks import get_usage_metadata_callback
from wwai_agent_orchestration.core.observability.logger import get_logger, get_request_context, is_perf_logging_enabled
from wwai_agent_orchestration.constants.prompt_trace import ENABLE_PROMPT_TRACE, PROMPT_TRACE_WRITE_TO_DB
from wwai_agent_orchestration.utils.landing_page_builder.db_utils import (
    append_prompt_trace,
    PROMPT_TRACES_COLLECTION,
    PROMPT_TRACES_DB_NAME,
)

# Load environment variables from .env file
load_dotenv()

logger = get_logger(__name__)

# Max size per field in trace (chars) to avoid huge documents
_TRACE_FIELD_MAX_CHARS = 50_000

@dataclass
class PromptBuilder(ABC):
    """
    Base class for building prompts and running LLMs using LangChain.
    This class should be inherited by specific prompt builder implementations.
    """
    
    def get_prompt_string(self) -> str:
        """
        Abstract method to get the prompt string.
        Must be implemented by subclasses.
        """
        pass
    
    def execute_llm_call(self) -> Union[str, dict]:
        """
        Abstract method to execute the LLM call.
        Must be implemented by subclasses.
        """
        pass

    def _track_prompt_usage(self, prompt_name: str, prompt_version: Optional[int] = None) -> None:
        """
        Track prompt usage by saving to a JSON file.
        
        Args:
            prompt_name: Name of the prompt being used
            prompt_version: Version of the prompt (None means "latest")
        """
        try:
            # Determine the tracking file path (in prompts directory within wwai_agent_orchestration package)
            package_root = Path(__file__).parent.parent  # wwai_agent_orchestration/
            prompts_dir = package_root / "prompts"
            prompts_dir.mkdir(exist_ok=True)
            tracking_file = prompts_dir / "prompt_usage_tracking.json"
            
            # Determine actual version used
            if prompt_version is None:
                actual_version = "latest"
            else:
                actual_version = str(prompt_version)
            
            # Load existing tracking data
            tracking_data = {}
            if tracking_file.exists():
                try:
                    with open(tracking_file, "r", encoding="utf-8") as f:
                        tracking_data = json.load(f)
                except (json.JSONDecodeError, IOError):
                    tracking_data = {}
            
            # Update tracking data
            if prompt_name not in tracking_data:
                tracking_data[prompt_name] = {}
            
            if actual_version not in tracking_data[prompt_name]:
                tracking_data[prompt_name][actual_version] = {
                    "first_seen": datetime.utcnow().isoformat(),
                    "last_seen": datetime.utcnow().isoformat(),
                    "usage_count": 0
                }
            
            # Update usage stats
            tracking_data[prompt_name][actual_version]["last_seen"] = datetime.utcnow().isoformat()
            tracking_data[prompt_name][actual_version]["usage_count"] += 1
            
            # Save updated tracking data
            with open(tracking_file, "w", encoding="utf-8") as f:
                json.dump(tracking_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            # Silently fail tracking to not break the main functionality
            # Could optionally log this error
            pass

    def get_prompt(self, prompt_name: str, prompt_version: Optional[int] = None, track_prompt_usage: bool = False) -> str:
        """
        Get prompt string from local text file.

        Reads the prompt from a text file in the prompts directory.

        Args:
            prompt_name: Name of the prompt to retrieve
            prompt_version: Optional; reserved for future use.
            track_prompt_usage: If True, track prompt usage via _track_prompt_usage.

        Returns:
            Prompt template string from local file

        Raises:
            FileNotFoundError: If the prompt file doesn't exist
            IOError: If there's an error reading the file
        """
        # Determine the prompts directory path
        package_root = Path(__file__).parent  # wwai_agent_orchestration/
        prompts_dir = package_root / "prompts"

        # Path-based prompt names (e.g. "landing_page_builder/data_preparation/trade_classification")
        if "/" in prompt_name:
            segments = prompt_name.split("/")
            sanitized_segments = []
            for seg in segments:
                if seg in ("", "..") or seg.startswith("/"):
                    raise ValueError(f"Invalid path segment in prompt_name: {seg!r}")
                sanitized_segments.append(re.sub(r'[<>:"/\\|?*]', '_', seg))
            prompt_file = prompts_dir.joinpath(*sanitized_segments).with_suffix(".txt")
        else:
            sanitized_name = re.sub(r'[<>:"/\\|?*]', '_', prompt_name)
            prompt_file = prompts_dir / f"{sanitized_name}.txt"
        
        # Check if file exists
        if not prompt_file.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {prompt_file}. "
                f"Make sure the prompt '{prompt_name}' has been backed up and the text file exists."
            )
        
        # Read prompt content from file
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                prompt_content = f.read()

            if track_prompt_usage:
                self._track_prompt_usage(prompt_name, prompt_version)

            return prompt_content

        except IOError as e:
            raise IOError(f"Error reading prompt file {prompt_file}: {str(e)}")

    def get_all_templated_fields_from_templated_prompt(self, prompt_template: str) -> List[str]:
        """
        Extract all templated fields from a prompt template.
        
        Args:
            prompt_template: The prompt template string containing variables
            
        Returns:
            List of variable names found in the template
        """
        
        # Try both single and double brace patterns
        double_brace_vars = re.findall(r'\{\{(\w+)\}\}', prompt_template)
        single_brace_vars = re.findall(r'\{(\w+)\}', prompt_template)
        
        # Return whichever pattern found variables
        if double_brace_vars:
            return list(set(double_brace_vars))
        elif single_brace_vars:
            return list(set(single_brace_vars))
        else:
            return []

    def _normalize_structured_output(self, response: Any, provider: str) -> Dict[str, Any]:
        """
        Normalize LLM structured output response to a dictionary.
        
        Different providers/configurations return different types:
        - Pydantic class passed: Returns Pydantic instance (all providers)
        - Dict schema passed: Returns dict (OpenAI) or may vary (Gemini)
        
        Args:
            response: The raw response from with_structured_output
            provider: The LLM provider name (for error messages)
            
        Returns:
            Dictionary representation of the response
            
        Raises:
            ValueError: If response is None or cannot be converted to dict
        """
        if response is None:
            raise ValueError(
                f"LLM ({provider}) returned None for structured output. "
                "This typically means the model failed to generate output matching the schema."
            )
        
        # If it's already a dict, return it
        if isinstance(response, dict):
            return response
        
        # If it's a Pydantic model (most common when passing Pydantic class)
        if isinstance(response, BaseModel):
            return response.model_dump()
        
        # Duck typing for Pydantic-like objects
        if hasattr(response, 'model_dump') and callable(response.model_dump):
            return response.model_dump()
        
        # Older Pydantic v1 style
        if hasattr(response, 'dict') and callable(response.dict):
            return response.dict()
        
        # Try to convert to dict
        try:
            return dict(response)
        except (TypeError, ValueError):
            pass
        
        # Last resort: JSON string parsing
        if isinstance(response, str):
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                pass
        
        raise ValueError(
            f"LLM ({provider}) returned unexpected type {type(response).__name__} "
            f"that cannot be converted to dict. Response preview: {str(response)[:200]}"
        )

    def _truncate_for_trace(self, obj: Any) -> Any:
        """Truncate large strings in trace payload to avoid huge documents."""
        if isinstance(obj, str):
            return obj[: _TRACE_FIELD_MAX_CHARS] + ("..." if len(obj) > _TRACE_FIELD_MAX_CHARS else "")
        if isinstance(obj, dict):
            return {k: self._truncate_for_trace(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._truncate_for_trace(v) for v in obj]
        return obj

    def _record_prompt_trace(
        self,
        task_name: prompt_builder_dataclass.PromptModules,
        prompt_name: str,
        invoke_input: Dict[str, Any],
        result: Any,
        duration_ms: float,
        mode: Literal["text", "image"] = "text",
        model: Optional[str] = None,
        provider: Optional[str] = None,
        formatted_prompt: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
    ) -> None:
        """
        Record a prompt trace for the current generation_version_id when enabled.

        Reads ENABLE_PROMPT_TRACE and PROMPT_TRACE_WRITE_TO_DB from constants.
        Uses request_id from get_request_context() as generation_version_id.
        """
        if not ENABLE_PROMPT_TRACE:
            return
        ctx = get_request_context()
        generation_version_id = ctx.get("request_id")
        if not generation_version_id:
            return
        if not PROMPT_TRACE_WRITE_TO_DB:
            return
        try:
            task_name_value = getattr(task_name, "value", str(task_name))
            trace = {
                "prompt_name": prompt_name,
                "task_name": task_name_value,
                "invoke_input": self._truncate_for_trace(invoke_input),
                "result": self._truncate_for_trace(result),
                "timestamp_iso": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                "duration_ms": round(duration_ms, 2),
                "mode": mode,
            }
            if model is not None:
                trace["model"] = model
            if provider is not None:
                trace["provider"] = provider
            if formatted_prompt is not None:
                trace["formatted_prompt"] = self._truncate_for_trace(formatted_prompt)
            if input_tokens is not None:
                trace["input_tokens"] = input_tokens
            if output_tokens is not None:
                trace["output_tokens"] = output_tokens
            append_prompt_trace(
                generation_version_id=generation_version_id,
                trace=trace,
                db_name=PROMPT_TRACES_DB_NAME,
                collection_name=PROMPT_TRACES_COLLECTION,
            )
        except Exception as e:
            logger.warning(f"Failed to record prompt trace: {e}")

    def _execute_llm_locally(
        self, 
        task_name: prompt_builder_dataclass.PromptModules, 
        prompt_string: str, 
        invoke_input: Dict[str, Any], 
        model_config: Dict[str, Any],
        output_model: Optional[Type[BaseModel]] = None,
        bypass_cache: bool = False,
        prompt_name: Optional[str] = None,
    ) -> prompt_builder_dataclass.PromptResponse:
        """
        Execute LLM task locally using LangChain.
        
        Args:
            task_name: The extractor module task name
            prompt_string: The prompt template string with variables
            invoke_input: Dictionary of variables to fill in the prompt
            model_config: Dictionary with model configuration parameters
            output_model: Optional Pydantic model class for structured output
            bypass_cache: Skip cache entirely if True

        Returns:
            PromptResponse with the LLM response
        """
        cfg = model_config or {}
        provider = (cfg.get("provider") or "openai").lower()
        model_name = cfg.get('model', 'gpt-4.1')
        temperature = cfg.get('temperature', 0.7)
        model = create_model(
            model=model_name,
            temperature=temperature,
            provider=provider
        )

        prompt_template = PromptTemplate.from_template(prompt_string)
        formatted_prompt = prompt_template.format(**invoke_input)

        start = time.perf_counter()
        start_time_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        input_tokens = output_tokens = None
        if output_model is not None:
            # Different providers need different handling:
            # - OpenAI requires additionalProperties:false on all nested objects. We use a patched
            #   schema (json_schema_openai_strict) + method="json_schema" so the same Pydantic
            #   models work without changing template_json_builder.
            # - Gemini: default method. Anthropic: default method.
            if provider == "openai":
                strict_schema = json_schema_openai_strict(output_model.model_json_schema())
                structured_model = model.with_structured_output(strict_schema, method="json_schema")
            elif provider in ("google", "gemini"):
                # Gemini: let SDK handle schema conversion
                structured_model = model.with_structured_output(output_model)
            else:
                # Anthropic and others: use default
                structured_model = model.with_structured_output(output_model)
            
            chain = prompt_template | structured_model
            with get_usage_metadata_callback() as usage_cb:
                raw_response = chain.invoke(invoke_input)
                if usage_cb.usage_metadata:
                    input_tokens = sum(m.get("input_tokens", 0) for m in usage_cb.usage_metadata.values())
                    output_tokens = sum(m.get("output_tokens", 0) for m in usage_cb.usage_metadata.values())
            
            # Normalize to dict (handles Pydantic instances, dicts, None, etc.)
            response = self._normalize_structured_output(raw_response, provider)
            
            # Validate against Pydantic model to catch missing/invalid fields early
            try:
                validated = output_model.model_validate(response)
                response = validated.model_dump()
            except Exception as validation_error:
                logger.error(
                    f"LLM response failed Pydantic validation",
                    output_model=output_model.__name__,
                    validation_error=str(validation_error),
                    raw_response_keys=list(response.keys()) if isinstance(response, dict) else type(response).__name__
                )
                raise ValueError(
                    f"LLM response failed validation against {output_model.__name__}: {validation_error}"
                )
        else:
            # No structured output - get raw string
            chain = prompt_template | model
            with get_usage_metadata_callback() as usage_cb:
                raw_result = chain.invoke(invoke_input)
                if usage_cb.usage_metadata:
                    input_tokens = sum(m.get("input_tokens", 0) for m in usage_cb.usage_metadata.values())
                    output_tokens = sum(m.get("output_tokens", 0) for m in usage_cb.usage_metadata.values())
            response = raw_result.content if hasattr(raw_result, 'content') else str(raw_result)

        duration_ms = (time.perf_counter() - start) * 1000
        end_time_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        prompt_name_value = getattr(task_name, "value", str(task_name))
        if is_perf_logging_enabled():
            logger.info(
                "LLM call completed",
                metric_type="perf_llm",
                provider=provider,
                prompt_name=prompt_name_value,
                start_time=start_time_iso,
                end_time=end_time_iso,
                duration_ms=round(duration_ms, 2),
            )

        effective_prompt_name = prompt_name or prompt_name_value
        self._record_prompt_trace(
            task_name=task_name,
            prompt_name=effective_prompt_name,
            invoke_input=invoke_input,
            result=response,
            duration_ms=duration_ms,
            mode="text",
            model=model_name,
            provider=provider,
            formatted_prompt=formatted_prompt,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        return prompt_builder_dataclass.PromptResponse(
            task_name=task_name,
            status=prompt_builder_dataclass.Status.SUCCESS,
            result=response
        )


    def run_llm_on_text(
        self, 
        task_name: prompt_builder_dataclass.PromptModules, 
        prompt_string: str, 
        invoke_input: Dict[str, Any],
        model_config: Optional[Dict[str, Any]] = None,
        output_model: Optional[Type[BaseModel]] = None,
        output_dataclass_schema_json: Optional[Dict[str, Any]] = None,  # DEPRECATED - kept for backward compat
        priority: str = "high",
        service_name: str = "default-service",
        run_on_worker: bool = True,
        bypass_cache: bool = False,
        prompt_name: Optional[str] = None,
    ) -> prompt_builder_dataclass.PromptResponse:
        """
        Run LLM on text with optional structured output.
                
        Args:
            task_name: The extractor module task name
            prompt_string: The prompt template string with variables
            invoke_input: Dictionary of variables to fill in the prompt
            model_config: Optional dictionary with model configuration parameters
            output_model: Pydantic model class for structured output (RECOMMENDED)
            output_dataclass_schema_json: DEPRECATED - use output_model instead
            priority: Task priority level (default: "high")
            service_name: Service name for metadata (default: "default-service")
            run_on_worker: Whether to run on worker (kept for compatibility, always runs locally)
            bypass_cache: Skip cache entirely if True
                    
        Returns:
            Either raw string response or structured dict based on output_model
        """
        # Handle backward compatibility: if old param used, log warning
        if output_dataclass_schema_json is not None and output_model is None:
            logger.warning(
                "output_dataclass_schema_json is deprecated. Pass the Pydantic class via output_model instead. "
                "This provides better compatibility across all LLM providers including Gemini."
            )
                
        try:
            result = self._execute_llm_locally(
                task_name=task_name, 
                prompt_string=prompt_string, 
                invoke_input=invoke_input,
                model_config=model_config or {},
                output_model=output_model,
                bypass_cache=bypass_cache,
                prompt_name=prompt_name,
            )
            
            return result
                        
        except Exception as e:
            raise Exception(f"LLM execution failed: {str(e)}")


    def run_llm_on_image(
        self, 
        task_name: prompt_builder_dataclass.PromptModules, 
        prompt_string: str, 
        invoke_input: Dict[str, Any], 
        image_labels: Dict[str, str],
        model_config: Optional[Dict[str, Any]] = None,
        output_model: Optional[Type[BaseModel]] = None,
        output_dataclass_schema_json: Optional[Dict[str, Any]] = None,  # DEPRECATED
        priority: str = "high",
        service_name: str = "default-service",
        run_on_worker: bool = True,
        prompt_name: Optional[str] = None,
    ) -> prompt_builder_dataclass.PromptResponse:
        """
        Run LLM on images with text prompt and optional structured output.
        
        Args:
            task_name: The extractor module task name
            prompt_string: The prompt template string with variables
            invoke_input: Dictionary of variables to fill in the prompt
            image_labels: Dictionary with image URLs as keys and labels as values
            model_config: Optional dictionary with model configuration parameters
            output_model: Pydantic model class for structured output (RECOMMENDED)
            output_dataclass_schema_json: DEPRECATED - use output_model instead
            priority: Task priority level (default: "high")
            service_name: Service name for metadata (default: "default-service")
            run_on_worker: Whether to run on worker (kept for compatibility, always runs locally)
            
        Returns:
            Either raw string response or structured dict based on output_model
        """
        # Handle backward compatibility
        if output_dataclass_schema_json is not None and output_model is None:
            logger.warning(
                "output_dataclass_schema_json is deprecated. Pass the Pydantic class via output_model instead."
            )
        
        try:
            cfg = model_config or {}
            provider = (cfg.get("provider") or "openai").lower()
            model_name = cfg.get('model', 'gpt-4o')
            temperature = cfg.get('temperature', 0.7)
            model = create_model(
                model=model_name,
                temperature=temperature,
                provider=provider
            )

            prompt_template = PromptTemplate.from_template(prompt_string)

            # Prepare messages with images
            image_content = []
            for image_url, label in image_labels.items():
                image_content.append({
                    "type": "text",
                    "text": label
                })
                image_content.append({
                    "type": "image_url",
                    "image_url": {"url": image_url}
                })

            # Format the prompt with invoke_input
            formatted_prompt = prompt_template.format(**invoke_input)

            # Add the formatted prompt text at the beginning
            image_content.insert(0, {
                "type": "text",
                "text": formatted_prompt
            })

            start = time.perf_counter()
            start_time_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

            input_tokens = output_tokens = None
            if output_model is not None:
                # Same OpenAI strict-schema handling as _execute_llm_locally
                if provider == "openai":
                    strict_schema = json_schema_openai_strict(output_model.model_json_schema())
                    structured_model = model.with_structured_output(strict_schema, method="json_schema")
                elif provider in ("google", "gemini"):
                    structured_model = model.with_structured_output(output_model)
                else:
                    structured_model = model.with_structured_output(output_model)
                
                with get_usage_metadata_callback() as usage_cb:
                    raw_response = structured_model.invoke([{
                        "role": "user",
                        "content": image_content
                    }])
                    if usage_cb.usage_metadata:
                        input_tokens = sum(m.get("input_tokens", 0) for m in usage_cb.usage_metadata.values())
                        output_tokens = sum(m.get("output_tokens", 0) for m in usage_cb.usage_metadata.values())
                
                # Normalize to dict
                response = self._normalize_structured_output(raw_response, provider)
                
                # Validate against Pydantic model to catch missing/invalid fields early
                try:
                    validated = output_model.model_validate(response)
                    response = validated.model_dump()
                except Exception as validation_error:
                    logger.error(
                        f"LLM response failed Pydantic validation",
                        output_model=output_model.__name__,
                        validation_error=str(validation_error),
                        raw_response_keys=list(response.keys()) if isinstance(response, dict) else type(response).__name__
                    )
                    raise ValueError(
                        f"LLM response failed validation against {output_model.__name__}: {validation_error}"
                    )
            else:
                # No structured output - get raw string
                with get_usage_metadata_callback() as usage_cb:
                    raw_result = model.invoke([{
                        "role": "user",
                        "content": image_content
                    }])
                    if usage_cb.usage_metadata:
                        input_tokens = sum(m.get("input_tokens", 0) for m in usage_cb.usage_metadata.values())
                        output_tokens = sum(m.get("output_tokens", 0) for m in usage_cb.usage_metadata.values())
                response = raw_result.content if hasattr(raw_result, 'content') else str(raw_result)

            duration_ms = (time.perf_counter() - start) * 1000
            end_time_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            prompt_name_value = getattr(task_name, "value", str(task_name))
            if is_perf_logging_enabled():
                logger.info(
                    "LLM call completed",
                    metric_type="perf_llm",
                    provider=provider,
                    prompt_name=prompt_name_value,
                    start_time=start_time_iso,
                    end_time=end_time_iso,
                    duration_ms=round(duration_ms, 2),
                )

            effective_prompt_name = prompt_name or prompt_name_value
            self._record_prompt_trace(
                task_name=task_name,
                prompt_name=effective_prompt_name,
                invoke_input=invoke_input,
                result=response,
                duration_ms=duration_ms,
                mode="image",
                model=model_name,
                provider=provider,
                formatted_prompt=formatted_prompt,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

            result = prompt_builder_dataclass.PromptResponse(
                task_name=task_name,
                status=prompt_builder_dataclass.Status.SUCCESS,
                result=response
            )

            return result

        except Exception as e:
            raise Exception(f"LLM execution failed: {str(e)}")
    


class PromptSpec:
    """
    Base class for prompt specifications.
    
    Subclasses define:
    - PROMPT_NAME: Name of the prompt file
    - TASK: The prompt module enum value
    - InputModel: Pydantic model for input validation
    - OutputModel: Pydantic model for output structure
    """
    PROMPT_NAME: str
    PROMPT_VERSION: Optional[int | str] = None
    TASK: prompt_builder_dataclass.PromptModules
    MODE: Literal["text", "image"] = "text"
    MODEL_CONFIG: Dict[str, any] = {"model": "gpt-4.1", "temperature": 0.7, "provider": "openai"}

    InputModel: Type[BaseModel]
    OutputModel: Type[BaseModel]

    @classmethod
    def prepare_input(cls, inp: BaseModel) -> BaseModel:
        """Override to transform input before LLM call. Default: pass-through."""
        return inp

    @classmethod
    def execute(
        cls,
        builder: PromptBuilder,  
        inp: BaseModel,
        model_config: Optional[Dict] = None,
        run_on_worker: bool = True,
        bypass_prompt_cache: bool = False
    ) -> prompt_builder_dataclass.PromptResponse:
        """
        Execute the prompt with the given input.
        
        Args:
            builder: PromptBuilder instance
            inp: Input data as Pydantic model
            model_config: Optional LLM configuration override
            run_on_worker: Kept for compatibility (always runs locally)
            bypass_prompt_cache: Skip prompt cache if True
            
        Returns:
            PromptResponse with validated output
        """
        try:
            inp = cls.prepare_input(inp)
            prompt = builder.get_prompt(
                cls.PROMPT_NAME,
                prompt_version=cls.PROMPT_VERSION
            )

            # Verify placeholders vs InputModel fields
            vars_in_tmpl = set(builder.get_all_templated_fields_from_templated_prompt(prompt))
            vars_expected = set(inp.model_dump().keys())
            
            # Check that all template variables are available in input data
            missing_vars = vars_in_tmpl - vars_expected
            if missing_vars:
                raise ValueError(f"Template variables {missing_vars} are missing from input data. Available fields: {vars_expected}")
            
            # Only include template variables in payload to avoid passing extra data
            inp_dump = inp.model_dump()
            payload = {key: value for key, value in inp_dump.items() if key in vars_in_tmpl}

            if cls.MODE == "text":
                res = builder.run_llm_on_text(
                    task_name=cls.TASK,
                    prompt_string=prompt,
                    invoke_input=payload,
                    model_config=model_config,
                    output_model=cls.OutputModel,  # Pass Pydantic class directly
                    run_on_worker=run_on_worker,
                    bypass_cache=bypass_prompt_cache,
                    prompt_name=cls.PROMPT_NAME,
                )
            else:
                # For image prompts, get image_labels from input (required)
                image_labels = inp_dump.get("image_labels")
                if not image_labels:
                    raise ValueError("image_labels required in InputModel for image mode prompts")
                res = builder.run_llm_on_image(
                    task_name=cls.TASK,
                    prompt_string=prompt,
                    invoke_input=payload,
                    image_labels=image_labels,
                    model_config=model_config,
                    output_model=cls.OutputModel,  # Pass Pydantic class directly
                    run_on_worker=run_on_worker,
                    prompt_name=cls.PROMPT_NAME,
                )

            # The result is already a dict from _normalize_structured_output
            # Validate it against OutputModel for extra safety
            if res.status == prompt_builder_dataclass.Status.SUCCESS:
                parsed = cls.OutputModel.model_validate(res.result)
                return prompt_builder_dataclass.PromptResponse(
                    task_name=cls.TASK,
                    status=prompt_builder_dataclass.Status.SUCCESS,
                    result=parsed.model_dump()
                )
            return res
        except Exception as e:
            return prompt_builder_dataclass.PromptResponse(
                task_name=cls.TASK,
                status=prompt_builder_dataclass.Status.FAILURE,
                error=f"Error in {cls.__name__}.execute: {str(e)}"
            )