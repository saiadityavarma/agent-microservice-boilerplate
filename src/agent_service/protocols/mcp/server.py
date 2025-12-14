"""
MCP server setup using FastMCP.

This module provides a FastMCP server instance configured with tools from the tool registry.
"""
from typing import Any

try:
    from fastmcp import FastMCP
    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False
    FastMCP = None


# Global MCP server instance
_mcp_server: Any | None = None


def create_mcp_server() -> Any:
    """
    Create and configure a FastMCP server.

    Returns:
        FastMCP server instance

    Raises:
        ImportError: If fastmcp is not installed
    """
    if not FASTMCP_AVAILABLE:
        raise ImportError(
            "fastmcp is not installed. Install it with: pip install fastmcp"
        )

    # Create FastMCP server
    mcp = FastMCP(
        name="Agent Service MCP",
        version="1.0.0",
        description="MCP server exposing agent tools and resources"
    )

    # Register tools from tool registry
    from agent_service.protocols.mcp.tools import register_tools_from_registry
    register_tools_from_registry(mcp)

    # Register resources
    @mcp.resource("file:///system/info")
    async def get_system_info() -> str:
        """Get system information."""
        from agent_service.config.settings import get_settings
        import json

        settings = get_settings()
        info = {
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "protocols_enabled": {
                "mcp": settings.enable_mcp,
                "a2a": settings.enable_a2a,
                "agui": settings.enable_agui
            }
        }
        return json.dumps(info, indent=2)

    # Register prompts
    @mcp.prompt(
        name="agent_invoke",
        description="Invoke the agent with a message"
    )
    async def agent_invoke_prompt(message: str) -> str:
        """Prompt template for invoking the agent."""
        return f"Please process this message: {message}"

    return mcp


def get_mcp_server() -> Any:
    """
    Get the global MCP server instance.

    Creates the server on first call (lazy initialization).

    Returns:
        FastMCP server instance
    """
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = create_mcp_server()
    return _mcp_server


def reset_mcp_server() -> None:
    """
    Reset the MCP server instance.

    Useful for testing or reconfiguration.
    """
    global _mcp_server
    _mcp_server = None
