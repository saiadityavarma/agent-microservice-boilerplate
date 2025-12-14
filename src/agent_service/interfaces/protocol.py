# src/agent_service/interfaces/protocol.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator
from fastapi import Request
from enum import Enum


class ProtocolType(str, Enum):
    MCP = "mcp"
    A2A = "a2a"
    AGUI = "agui"


class IProtocolHandler(ABC):
    """
    Interface for protocol handlers (MCP, A2A, AG-UI).

    Claude Code: Implement this interface to add protocol support.

    Example:
        class MCPHandler(IProtocolHandler):
            protocol_type = ProtocolType.MCP

            async def handle_request(self, request, agent):
                # Transform MCP request -> AgentInput
                # Call agent
                # Transform AgentOutput -> MCP response
                ...
    """

    @property
    @abstractmethod
    def protocol_type(self) -> ProtocolType:
        """Which protocol this handler supports."""
        pass

    @abstractmethod
    async def handle_request(
        self,
        request: Request,
        agent: "IAgent",
    ) -> Any:
        """
        Handle incoming protocol request.

        Args:
            request: FastAPI request
            agent: Agent to invoke

        Returns:
            Protocol-specific response
        """
        pass

    @abstractmethod
    async def handle_stream(
        self,
        request: Request,
        agent: "IAgent",
    ) -> AsyncGenerator[str, None]:
        """
        Handle streaming protocol request.

        Args:
            request: FastAPI request
            agent: Agent to invoke

        Yields:
            Protocol-formatted SSE events
        """
        pass

    def get_capability_info(self) -> dict[str, Any]:
        """Return protocol-specific capability info (agent card, etc.)."""
        return {}
