# src/agent_service/interfaces/agent.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator
from dataclasses import dataclass


@dataclass
class AgentInput:
    """Standard input to any agent."""
    message: str
    session_id: str | None = None
    context: dict[str, Any] | None = None


@dataclass
class AgentOutput:
    """Standard output from any agent."""
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class StreamChunk:
    """Chunk emitted during streaming."""
    type: str  # "text", "tool_start", "tool_end", "error"
    content: str = ""
    metadata: dict[str, Any] | None = None


class IAgent(ABC):
    """
    Interface for any agent implementation.

    Claude Code: Implement this interface to add a new agent framework.

    Example:
        class LangGraphAgent(IAgent):
            async def invoke(self, input: AgentInput) -> AgentOutput:
                # Your LangGraph implementation
                ...
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this agent."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        pass

    @abstractmethod
    async def invoke(self, input: AgentInput) -> AgentOutput:
        """
        Execute agent synchronously.

        Args:
            input: Standardized agent input

        Returns:
            Standardized agent output
        """
        pass

    @abstractmethod
    async def stream(self, input: AgentInput) -> AsyncGenerator[StreamChunk, None]:
        """
        Execute agent with streaming output.

        Args:
            input: Standardized agent input

        Yields:
            StreamChunk for each piece of output
        """
        pass

    async def setup(self) -> None:
        """Optional: Called once when agent is registered."""
        pass

    async def teardown(self) -> None:
        """Optional: Called when agent is unregistered."""
        pass
