"""
Base Abstract AI Agent Class

Provides foundation for all specialized emergency response agents.
Communicates with Google Gemini exclusively through GeminiLLMWrapper.
Handles memory buffer management, structured logging, and fallback execution.
"""

import time
import json
from abc import ABC, abstractmethod
from typing import Type, TypeVar, Optional, List, Dict, Any
from pydantic import BaseModel

from config.settings import settings
from memory.agent_memory_store import agent_memory_store
from utils.gemini_wrapper import gemini_wrapper, GeminiLLMWrapper
from utils.logger import app_logger
from utils.exceptions import AgentExecutionError


InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class BaseAgent(ABC):
    """
    Abstract Base Class for specialized emergency response agents.
    All LLM interaction is routed strictly through GeminiLLMWrapper.
    """

    def __init__(
        self,
        name: str,
        system_instruction: str,
        input_schema: Type[InputT],
        output_schema: Type[OutputT],
        model_name: Optional[str] = None
    ):
        self.name = name
        self.system_instruction = system_instruction
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.model_name = model_name or settings.DEFAULT_GEMINI_MODEL
        self.memory_buffer: List[Dict[str, Any]] = []
        self.wrapper: GeminiLLMWrapper = gemini_wrapper

    def add_memory(self, role: str, content: str):
        """Append interaction step to short-term agent memory buffer and sync to Redis."""
        self.memory_buffer.append({"role": role, "content": content, "timestamp": time.time()})
        # Keep last 10 messages
        if len(self.memory_buffer) > 10:
            self.memory_buffer = self.memory_buffer[-10:]

        try:
            agent_memory_store.add_message(self.name, role, content)
        except Exception as e:
            app_logger.warning(f"[{self.name}] Could not sync memory to Redis: {e}")

    def clear_memory(self):
        """Reset short-term memory buffer and Redis store."""
        self.memory_buffer.clear()
        try:
            agent_memory_store.clear_memory(self.name)
        except Exception as e:
            app_logger.warning(f"[{self.name}] Could not clear Redis agent memory: {e}")


    async def execute(self, input_data: InputT) -> OutputT:
        """
        Executes agent pipeline via GeminiLLMWrapper:
        Input validation -> GeminiLLMWrapper structured call -> Pydantic parsing -> Fallback handling.
        """
        start_time = time.time()
        app_logger.info(f"[{self.name}] Beginning execution...")
        self.add_memory("user", input_data.model_dump_json())

        try:
            if self.wrapper and self.wrapper.client:
                output = await self.wrapper.generate_structured(
                    prompt=input_data.model_dump_json(),
                    response_schema=self.output_schema,
                    system_instruction=self.system_instruction,
                    temperature=0.2,
                    model_name=self.model_name
                )
            else:
                app_logger.info(f"[{self.name}] Gemini client uninitialized. Running fallback solver.")
                output = self.fallback_execution(input_data)

            self.add_memory("model", output.model_dump_json())
            elapsed = time.time() - start_time
            app_logger.info(f"[{self.name}] Successfully executed in {elapsed:.2f}s")
            return output

        except Exception as e:
            app_logger.error(f"[{self.name}] Execution error: {e}. Triggering deterministic fallback response.")
            fallback_output = self.fallback_execution(input_data)
            self.add_memory("fallback", fallback_output.model_dump_json())
            return fallback_output

    @abstractmethod
    def fallback_execution(self, input_data: InputT) -> OutputT:
        """Deterministic fallback method executed if Gemini API is unreachable or fails."""
        pass
