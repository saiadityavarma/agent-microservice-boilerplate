# src/agent_service/tools/examples/http_request.py
"""
Example: HTTP request tool.

Claude Code: Shows a more complex tool with validation and error handling.
"""
from typing import Any, Literal
import httpx

from agent_service.interfaces import ITool, ToolSchema


class HTTPRequestTool(ITool):
    """Make HTTP requests."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="http_request",
            description="Make an HTTP request to a URL",
            parameters={
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST"],
                        "description": "HTTP method",
                    },
                    "url": {
                        "type": "string",
                        "description": "URL to request",
                    },
                    "body": {
                        "type": "object",
                        "description": "Request body (for POST)",
                    },
                },
                "required": ["method", "url"],
            },
        )

    @property
    def requires_confirmation(self) -> bool:
        """Require user confirmation before making requests."""
        return True

    async def execute(
        self,
        method: Literal["GET", "POST"],
        url: str,
        body: dict | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url)
            else:
                response = await client.post(url, json=body)

            return {
                "status_code": response.status_code,
                "body": response.text[:1000],  # Truncate
            }
