# src/agent_service/tools/examples/echo.py
"""
Example tool implementation.

Claude Code: Use this as a template for new tools.
"""
from typing import Any
from agent_service.interfaces import ITool, ToolSchema


class EchoTool(ITool):
    """Simple echo tool for testing."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="echo",
            description="Echoes the input message back",
            parameters={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Message to echo",
                    }
                },
                "required": ["message"],
            },
        )

    async def execute(self, message: str, **kwargs) -> str:
        return f"Echo: {message}"
