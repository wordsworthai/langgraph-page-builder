# utils/llm/model_utils.py
from typing import Any, Dict, Optional, Union

import os
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from wwai_agent_orchestration.core.observability.logger import get_logger
from wwai_agent_orchestration.utils.secrets.secret_manager_util import get_secret

logger = get_logger(__name__)


def get_model_config_from_configurable(configurable: Dict[str, Any]) -> Dict[str, Any]:
    """Build model_config dict from workflow configurable."""
    model = configurable.get("model_name", "gpt-4.1")
    provider = configurable.get("llm_provider", "openai")
    out = {"model": model, "provider": provider}
    temp = configurable.get("temperature")
    if temp is not None:
        out["temperature"] = temp
    return out


def create_model(
    model: str = "gpt-4.1",
    temperature: Optional[float] = 0.7,
    provider: str = "openai",
    disabled_params: Optional[dict] = None
) -> Union[ChatOpenAI, ChatAnthropic, ChatGoogleGenerativeAI]:
    """Create and return a model instance based on the configuration."""
    if disabled_params is None:
        disabled_params = {}

    model_kwargs = {}
    if temperature is not None:
        model_kwargs["temperature"] = temperature
    if disabled_params:
        model_kwargs["disabled_params"] = disabled_params

    provider_lower = provider.lower()
    environment = os.getenv('ENVIRONMENT', 'local').lower()

    try:
        if provider_lower == "openai":
            if environment == 'local':
                api_key = os.getenv('OPENAI_API_KEY')
                if not api_key:
                    raise ValueError("No OpenAI API key found. Set OPENAI_API_KEY.")
            else:
                api_key = get_secret("OPENAI_API_KEY")
            return ChatOpenAI(model=model, openai_api_key=api_key, **model_kwargs)

        elif provider_lower == "anthropic":
            if environment == 'local':
                api_key = os.getenv('ANTHROPIC_API_KEY')
                if not api_key:
                    raise ValueError("No Anthropic API key found. Set ANTHROPIC_API_KEY.")
            else:
                api_key = get_secret("ANTHROPIC_API_KEY")
            return ChatAnthropic(model=model, anthropic_api_key=api_key, **model_kwargs)

        elif provider_lower in ("google", "gemini"):
            if environment == 'local':
                api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
                if not api_key:
                    raise ValueError("No Google/Gemini API key found. Set GOOGLE_API_KEY or GEMINI_API_KEY.")
            else:
                api_key = get_secret("GOOGLE_API_KEY") or get_secret("GEMINI_API_KEY")
                if not api_key:
                    raise ValueError("No Google/Gemini API key in Secret Manager.")
            gemini_kwargs = dict(model_kwargs)
            if "gemini-3" in model.lower():
                gemini_kwargs["temperature"] = 1.0
            return ChatGoogleGenerativeAI(model=model, api_key=api_key, **gemini_kwargs)

        else:
            raise ValueError(f"Unsupported provider: {provider}. Supported: openai, anthropic, google")
    except Exception as e:
        logger.error(f"Failed to create model for {provider}: {str(e)}")
        raise


def get_available_models() -> dict:
    """Get dictionary of available models by provider."""
    return {
        "openai": ["gpt-5", "gpt-5-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
        "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
        "google": ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-3-flash-preview", "gemini-pro"],
    }


def validate_model_config(model: str, provider: str) -> bool:
    """Validate if the model is available for the given provider."""
    available_models = get_available_models()
    provider_lower = provider.lower()
    if provider_lower == "gemini":
        provider_lower = "google"
    if provider_lower not in available_models:
        return False
    return model in available_models[provider_lower]


def create_model_with_validation(
    model: str = "gpt-4.1",
    temperature: Optional[float] = 0.7,
    provider: str = "openai",
    disabled_params: Optional[dict] = None
) -> Union[ChatOpenAI, ChatAnthropic, ChatGoogleGenerativeAI]:
    """Create model with validation of model-provider combination."""
    if not validate_model_config(model, provider):
        available = get_available_models()
        provider_models = available.get(provider.lower(), [])
        raise ValueError(f"Model '{model}' is not available for provider '{provider}'. Available: {provider_models}")
    return create_model(model, temperature, provider, disabled_params)
