# src/agent_service/interfaces/tool.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel


class ToolSchema(BaseModel):
    """JSON Schema for tool parameters."""
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema format


class ITool(ABC):
    """
    Interface for any tool implementation.

    Claude Code: Implement this interface to add a new tool.

    Example:
        class WebSearchTool(ITool):
            @property
            def schema(self) -> ToolSchema:
                return ToolSchema(
                    name="web_search",
                    description="Search the web",
                    parameters={"query": {"type": "string"}}
                )

            async def execute(self, **kwargs) -> Any:
                query = kwargs["query"]
                # Your implementation
                ...
    """

    @property
    @abstractmethod
    def schema(self) -> ToolSchema:
        """Return tool schema for LLM function calling."""
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """
        Execute the tool with given arguments.

        Args:
            **kwargs: Tool-specific arguments matching schema

        Returns:
            Tool execution result
        """
        pass

    @property
    def requires_confirmation(self) -> bool:
        """Override to require human confirmation before execution."""
        return False
