"""
Centralized Gemini LLM Wrapper (Single Point of Contact for Gemini API)

All agents and multi-agent workflows interact with Google Gemini exclusively through this wrapper.
If the underlying Gemini API/SDK changes, ONLY THIS FILE requires modification.

Supported Capabilities:
- Exponential Backoff Retries (Tenacity)
- Async Streaming Output (generate_stream)
- Structured Pydantic Model Output (generate_structured)
- JSON Dict Output (generate_json)
- Dynamic Temperature Tuning
- Response Caching (SHA-256 keyed cache)
- Parameterized Prompt Templates (PromptTemplate)
"""

import json
import time
import hashlib
import asyncio
from typing import Type, TypeVar, Optional, Dict, Any, AsyncGenerator
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config.settings import settings
from utils.logger import app_logger
from utils.exceptions import AgentExecutionError

# Try importing google.genai SDK
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


T = TypeVar("T", bound=BaseModel)


class PromptTemplate:
    """Prompt template engine for compiling parameterized system & user instructions."""

    def __init__(self, template: str):
        self.template = template

    def render(self, **kwargs: Any) -> str:
        """Renders prompt template by substituting variable placeholders."""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            app_logger.warning(f"[PromptTemplate] Missing template variable: {e}")
            return self.template


class GeminiLLMWrapper:
    """
    Unified Google Gemini LLM API Wrapper Class.
    Single interface for all specialized agents, providing structured outputs,
    JSON responses, streaming, retries, caching, and temperature control.
    """

    _instance: Optional["GeminiLLMWrapper"] = None

    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.default_model = default_model or settings.DEFAULT_GEMINI_MODEL
        self.client = None
        self._cache: Dict[str, Any] = {}

        if GENAI_AVAILABLE and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
                app_logger.info(f"[GeminiLLMWrapper] Gemini Client initialized with model '{self.default_model}'.")
            except Exception as e:
                app_logger.warning(f"[GeminiLLMWrapper] Failed to initialize Gemini Client: {e}. Fallback mode active.")

    @classmethod
    def get_instance(cls) -> "GeminiLLMWrapper":
        """Singleton accessor for GeminiLLMWrapper."""
        if cls._instance is None:
            cls._instance = GeminiLLMWrapper()
        return cls._instance

    def _compute_cache_key(
        self,
        prompt: str,
        system_instruction: Optional[str],
        temperature: float,
        model_name: str,
        schema_name: Optional[str] = None
    ) -> str:
        """Computes SHA-256 cache key for prompt request."""
        raw_key = f"{model_name}|{system_instruction or ''}|{prompt}|{temperature}|{schema_name or ''}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def clear_cache(self):
        """Clears in-memory response cache."""
        self._cache.clear()
        app_logger.info("[GeminiLLMWrapper] Response cache cleared.")

    # =========================================================================
    # Internal Retried Gemini API Call
    # =========================================================================

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry_error_callback=lambda state: app_logger.warning("[GeminiLLMWrapper] Retry attempt triggered for API call.")
    )
    async def _call_gemini_raw(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        response_mime_type: str = "application/json",
        model_name: Optional[str] = None
    ) -> str:
        """Internal retried call to Gemini API using google.genai SDK."""
        if not self.client:
            raise AgentExecutionError("Gemini API client is uninitialized or API key is absent.")

        target_model = model_name or self.default_model
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type=response_mime_type,
            temperature=temperature
        )

        app_logger.info(f"[GeminiLLMWrapper] Invoking Gemini model '{target_model}' (temp={temperature})...")
        start_time = time.time()

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.models.generate_content(
                model=target_model,
                contents=prompt,
                config=config
            )
        )

        elapsed = time.time() - start_time
        app_logger.info(f"[GeminiLLMWrapper] Gemini response returned in {elapsed:.2f}s.")
        return response.text

    # =========================================================================
    # Public Wrapper APIs
    # =========================================================================

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        use_cache: bool = True,
        model_name: Optional[str] = None
    ) -> T:
        """
        Generates structured Pydantic model output from Gemini.
        Returns validated instance of response_schema.
        """
        target_model = model_name or self.default_model
        cache_key = self._compute_cache_key(prompt, system_instruction, temperature, target_model, response_schema.__name__)

        if use_cache and cache_key in self._cache:
            app_logger.info(f"[GeminiLLMWrapper] Cache HIT for structured output '{response_schema.__name__}'.")
            cached_data = self._cache[cache_key]
            return response_schema.model_validate_json(cached_data)

        if not self.client:
            raise AgentExecutionError("Gemini client uninitialized.")

        raw_json_str = await self._call_gemini_raw(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            response_mime_type="application/json",
            model_name=target_model
        )

        parsed_json = json.loads(raw_json_str)
        validated_obj = response_schema.model_validate(parsed_json)

        if use_cache:
            self._cache[cache_key] = validated_obj.model_dump_json()

        return validated_obj

    async def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        use_cache: bool = True,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates raw JSON dictionary response from Gemini.
        """
        target_model = model_name or self.default_model
        cache_key = self._compute_cache_key(prompt, system_instruction, temperature, target_model, "JSON_DICT")

        if use_cache and cache_key in self._cache:
            app_logger.info("[GeminiLLMWrapper] Cache HIT for JSON output.")
            return json.loads(self._cache[cache_key])

        if not self.client:
            raise AgentExecutionError("Gemini client uninitialized.")

        raw_json_str = await self._call_gemini_raw(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            response_mime_type="application/json",
            model_name=target_model
        )

        parsed_dict = json.loads(raw_json_str)
        if use_cache:
            self._cache[cache_key] = json.dumps(parsed_dict)

        return parsed_dict

    async def generate_vision_json(
        self,
        image_bytes: bytes,
        prompt: str,
        system_instruction: Optional[str] = None,
        mime_type: str = "image/jpeg",
        temperature: float = 0.2,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Invokes Gemini Multimodal Vision API on raw image bytes.
        Returns parsed JSON dictionary with vision analysis results.
        """
        if not self.client:
            raise AgentExecutionError("Gemini client uninitialized or API key not configured.")

        target_model = model_name or self.default_model
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            temperature=temperature
        )

        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        contents = [image_part, prompt]

        app_logger.info(f"[GeminiLLMWrapper] Invoking Gemini Vision model '{target_model}' (bytes={len(image_bytes)})...")
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.models.generate_content(
                model=target_model,
                contents=contents,
                config=config
            )
        )

        return json.loads(response.text)

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        model_name: Optional[str] = None
    ) -> str:
        """
        Generates plain text response from Gemini.
        """
        if not self.client:
            raise AgentExecutionError("Gemini client uninitialized.")

        return await self._call_gemini_raw(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            response_mime_type="text/plain",
            model_name=model_name
        )

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        model_name: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Streams response chunks asynchronously from Gemini.
        Yields text chunks as they arrive.
        """
        if not self.client:
            raise AgentExecutionError("Gemini client uninitialized.")

        target_model = model_name or self.default_model
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature
        )

        app_logger.info(f"[GeminiLLMWrapper] Initiating Gemini stream from '{target_model}'...")
        response_stream = self.client.models.generate_content_stream(
            model=target_model,
            contents=prompt,
            config=config
        )

        for chunk in response_stream:
            if chunk.text:
                yield chunk.text


# Global Singleton Instance
gemini_wrapper = GeminiLLMWrapper.get_instance()
