"""
Example: Simple LLM agent (no framework).

Install: uv add openai  # or anthropic

Claude Code: Use this for simple LLM-based agents without a framework.
"""
from typing import AsyncGenerator

from agent_service.interfaces import IAgent, AgentInput, AgentOutput, StreamChunk


class SimpleLLMAgent(IAgent):
    """
    Direct LLM agent without a framework.

    Good for simple use cases without complex workflows.
    """

    def __init__(self, provider: str = "openai", model: str = "gpt-4o-mini"):
        self._provider = provider
        self._model = model
        self._client = None

    @property
    def name(self) -> str:
        return "simple-llm"

    @property
    def description(self) -> str:
        return f"Simple {self._provider} agent"

    async def setup(self) -> None:
        """Initialize LLM client."""
        if self._provider == "openai":
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI()
        # Add other providers as needed

    async def invoke(self, input: AgentInput) -> AgentOutput:
        if not self._client:
            await self.setup()

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": input.message}],
        )
        return AgentOutput(content=response.choices[0].message.content)

    async def stream(self, input: AgentInput) -> AsyncGenerator[StreamChunk, None]:
        if not self._client:
            await self.setup()

        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": input.message}],
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield StreamChunk(type="text", content=chunk.choices[0].delta.content)
