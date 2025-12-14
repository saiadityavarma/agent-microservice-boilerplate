"""
Example: LangGraph agent implementation.

Install: uv add langgraph langchain-openai

Claude Code: Use this as a template for LangGraph-based agents.
"""
from typing import AsyncGenerator

from agent_service.interfaces import IAgent, AgentInput, AgentOutput, StreamChunk


class LangGraphAgent(IAgent):
    """
    LangGraph-based agent.

    Requirements:
        - langgraph
        - langchain-openai (or langchain-anthropic)
    """

    def __init__(self, model: str = "gpt-4o-mini"):
        self._model = model
        self._graph = None  # Initialized in setup()

    @property
    def name(self) -> str:
        return "langgraph"

    @property
    def description(self) -> str:
        return f"LangGraph agent using {self._model}"

    async def setup(self) -> None:
        """Initialize the LangGraph workflow."""
        # TODO (Claude Code): Build your graph here
        # from langgraph.graph import StateGraph
        # from langchain_openai import ChatOpenAI
        #
        # llm = ChatOpenAI(model=self._model)
        # graph = StateGraph(...)
        # self._graph = graph.compile()
        pass

    async def invoke(self, input: AgentInput) -> AgentOutput:
        """Execute graph synchronously."""
        if not self._graph:
            await self.setup()

        # TODO: Implement
        # result = await self._graph.ainvoke({"messages": [...]})
        # return AgentOutput(content=result["messages"][-1].content)
        raise NotImplementedError("Implement with LangGraph")

    async def stream(self, input: AgentInput) -> AsyncGenerator[StreamChunk, None]:
        """Execute graph with streaming."""
        if not self._graph:
            await self.setup()

        # TODO: Implement
        # async for event in self._graph.astream_events(...):
        #     yield StreamChunk(type="text", content=event["data"])
        raise NotImplementedError("Implement with LangGraph")
        yield
