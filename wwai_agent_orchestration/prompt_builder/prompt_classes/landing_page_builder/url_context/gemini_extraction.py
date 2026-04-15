from dataclasses import dataclass
from wwai_agent_orchestration.prompt_builder.prompt_builder import PromptBuilder
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from google.genai.types import GenerateContentConfig
from google import genai
import os
from wwai_agent_orchestration.prompt_builder import prompt_builder_dataclass
from wwai_agent_orchestration.utils.landing_page_builder.url_context_cache import (
    generate_url_context_cache_key,
    get_cached_url_context,
    save_url_context_cache,
)
from wwai_agent_orchestration.constants import prompt_versions
from dotenv import load_dotenv
load_dotenv()

METHOD_GEMINI = "gemini"


class GeminiContext(BaseModel):
    """
    Pydantic model for Gemini URL context extraction results
    """
    query_used: str = Field(
        description="The full prompt/query sent to Gemini"
    )
    response_text: str = Field(
        description="The extracted and organized content from the URL"
    )
    url_context_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metadata about URL retrieval from Gemini"
    )
    extraction_timestamp: datetime = Field(
        description="Timestamp when the extraction was performed"
    )
@dataclass
class GeminiURLContextExtractor(PromptBuilder):
    """
    A dataclass for extracting semantic content from URLs using Gemini's url_context tool.
    Inherits from PromptBuilder to retrieve prompts from Langfuse.
    """
    def __init__(self):
        """Initialize the GeminiURLContextExtractor with Gemini client and prompt configuration."""
        super().__init__()
        self.prompt_name = prompt_versions.GEMINI_URL_CONTEXT_PROMPT_NAME
        # Initialize Gemini client
        gemini_key = os.getenv('GEMINI_API_KEY')
        if not gemini_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        self.gemini_client = genai.Client(api_key=gemini_key)
        self.gemini_model = "gemini-2.5-flash"  # Hardcoded for now

    def get_prompt_string(self, prompt_version: Optional[str] = None) -> str:
        """
        Get the prompt string from Langfuse using the gemini_url_context_extraction name.
        Args:
            prompt_version: Optional specific version of the prompt to retrieve
        Returns:
            str: The prompt template string for URL context extraction
        """
        return self.get_prompt(self.prompt_name, prompt_version=prompt_version)
    
    def execute_gemini_url_call(
        self,
        url: str,
        prompt_version: Optional[str] = None,
        invoke_input: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> GeminiContext:
        """
        Execute Gemini URL context extraction call.
        Args:
            url: The URL to analyze and extract content from
            prompt_version: Optional specific version of the prompt to use
            invoke_input: Optional dictionary of variables to fill in the prompt template
            use_cache: If True, check cache before calling API and save successful results. If False, bypass cache.
        Returns:
            GeminiContext: Structured URL context extraction results
        """
        if use_cache:
            cache_key = generate_url_context_cache_key(url, METHOD_GEMINI)
            cached = get_cached_url_context(cache_key)
            if cached and cached.get("response_text") and "Error occurred" not in cached.get("response_text", ""):
                return GeminiContext(
                    query_used=cached.get("query_used", ""),
                    response_text=cached["response_text"],
                    url_context_metadata=cached.get("url_context_metadata"),
                    extraction_timestamp=datetime.utcnow(),
                )
        try:
            # Get the LangChain PromptTemplate from Langfuse
            prompt_template = self.get_prompt(
                self.prompt_name,
                prompt_version=prompt_version or prompt_versions.GEMINI_URL_CONTEXT_PROMPT_VERSION,
            )
            # Format the template with invoke_input if provided
            if invoke_input:
                custom_query = prompt_template.format(**invoke_input)
            else:
                custom_query = prompt_template  # Get raw template string
            # Prepare the full prompt with URL prefix
            full_prompt = f"Analyze this URL: {url}\n\n{custom_query}"
            # Configure Gemini with url_context tool
            tools = [{"url_context": {}}]
            # Execute Gemini call
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=full_prompt,
                config=GenerateContentConfig(tools=tools)
            )
            # Extract response text
            response_text = ""
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text'):
                    response_text += part.text
            # Extract URL context metadata
            url_context_metadata = {}
            if hasattr(response.candidates[0], 'url_context_metadata'):
                metadata_obj = response.candidates[0].url_context_metadata
                if metadata_obj:
                    if isinstance(metadata_obj, dict):
                        url_context_metadata = metadata_obj
                    elif hasattr(metadata_obj, '__iter__'):
                        url_context_metadata = {
                            "url_metadata": [
                                {
                                    "retrieved_url": getattr(item, 'retrieved_url', ''),
                                    "url_retrieval_status": getattr(item, 'url_retrieval_status', '')
                                }
                                for item in metadata_obj
                            ]
                        }
                    else:
                        url_context_metadata = {
                            "retrieved_url": getattr(metadata_obj, 'retrieved_url', ''),
                            "url_retrieval_status": getattr(metadata_obj, 'url_retrieval_status', '')
                        }
            # Save to cache on success (no "Error occurred")
            if use_cache and "Error occurred" not in response_text:
                cache_key = generate_url_context_cache_key(url, METHOD_GEMINI)
                save_url_context_cache(
                    cache_key,
                    url,
                    METHOD_GEMINI,
                    {"response_text": response_text, "query_used": full_prompt, "url_context_metadata": url_context_metadata},
                )
            # Return structured GeminiContext
            return GeminiContext(
                query_used=full_prompt,
                response_text=response_text,
                url_context_metadata=url_context_metadata,
                extraction_timestamp=datetime.utcnow()
            )
        except Exception as e:
            # Log the error for debugging purposes
            print(f"Error in execute_gemini_url_call: {str(e)}")
            # Return GeminiContext with error information
            return GeminiContext(
                query_used=f"Analyze this URL: {url}\n\n[Error retrieving prompt]",
                response_text=f"Error occurred during URL context extraction: {str(e)}",
                url_context_metadata={},
                extraction_timestamp=datetime.utcnow()
            )