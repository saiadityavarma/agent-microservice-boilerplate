"""
Model Context Protocol (MCP) handler.

This module provides MCP protocol support for exposing agent tools and resources
via the Model Context Protocol standard.

Key components:
- MCPHandler: Main protocol handler for MCP requests
- MCP Server: FastMCP server instance with tool registration
- MCP Tools: Utilities for converting tools to MCP format

Usage:
    from agent_service.protocols.mcp import MCPHandler

    handler = MCPHandler()
    response = await handler.handle_request(request, agent)
"""
from agent_service.protocols.mcp.handler import MCPHandler

try:
    from agent_service.protocols.mcp.server import (
        get_mcp_server,
        create_mcp_server,
        reset_mcp_server
    )
    from agent_service.protocols.mcp.tools import (
        register_tools_from_registry,
        convert_tool_to_mcp_format,
        create_tool_executor,
        validate_tool_arguments
    )
    MCP_AVAILABLE = True
except ImportError:
    # FastMCP not installed
    get_mcp_server = None
    create_mcp_server = None
    reset_mcp_server = None
    register_tools_from_registry = None
    convert_tool_to_mcp_format = None
    create_tool_executor = None
    validate_tool_arguments = None
    MCP_AVAILABLE = False


__all__ = [
    "MCPHandler",
    "get_mcp_server",
    "create_mcp_server",
    "reset_mcp_server",
    "register_tools_from_registry",
    "convert_tool_to_mcp_format",
    "create_tool_executor",
    "validate_tool_arguments",
    "MCP_AVAILABLE"
]
