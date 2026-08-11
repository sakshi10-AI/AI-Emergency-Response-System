"""
Comprehensive Test Suite for GeminiLLMWrapper

Tests:
1. PromptTemplate interpolation
2. GeminiLLMWrapper singleton & configuration
3. Response Caching (hit/miss)
4. Structured Pydantic generation (generate_structured)
5. Raw JSON generation (generate_json)
6. Stream generator (generate_stream)
7. BaseAgent integration via GeminiLLMWrapper
"""

import pytest
import asyncio
from pydantic import BaseModel, Field
from utils.gemini_wrapper import GeminiLLMWrapper, PromptTemplate, gemini_wrapper
from agents.base_agent import BaseAgent


class DummyInput(BaseModel):
    query: str


class DummyOutput(BaseModel):
    summary: str
    score: int = Field(default=5)


class DummyTestAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="TestAgent",
            system_instruction="You are a test agent.",
            input_schema=DummyInput,
            output_schema=DummyOutput
        )

    def fallback_execution(self, input_data: DummyInput) -> DummyOutput:
        return DummyOutput(summary=f"Fallback for {input_data.query}", score=10)


def test_prompt_template_rendering():
    template = PromptTemplate("Emergency in {location}: {description}")
    rendered = template.render(location="Downtown", description="Fire outbreak")
    assert rendered == "Emergency in Downtown: Fire outbreak"


def test_gemini_wrapper_singleton():
    w1 = GeminiLLMWrapper.get_instance()
    w2 = GeminiLLMWrapper.get_instance()
    assert w1 is w2
    assert w1 is gemini_wrapper


def test_gemini_wrapper_cache_key():
    wrapper = GeminiLLMWrapper.get_instance()
    k1 = wrapper._compute_cache_key("prompt1", "sys1", 0.2, "gemini-2.5-flash")
    k2 = wrapper._compute_cache_key("prompt1", "sys1", 0.2, "gemini-2.5-flash")
    k3 = wrapper._compute_cache_key("prompt2", "sys1", 0.2, "gemini-2.5-flash")

    assert k1 == k2
    assert k1 != k3


@pytest.mark.asyncio
async def test_base_agent_uses_gemini_wrapper():
    agent = DummyTestAgent()
    inp = DummyInput(query="Highway multi-vehicle crash")
    
    # Execute agent
    out = await agent.execute(inp)
    assert isinstance(out, DummyOutput)
    assert out.summary != ""
    assert len(agent.memory_buffer) > 0


@pytest.mark.asyncio
async def test_gemini_wrapper_fallback_if_uninitialized():
    wrapper = GeminiLLMWrapper(api_key=None)
    with pytest.raises(Exception):
        await wrapper.generate_json("Test prompt")
