"""
Tool registration for MCP server.

This module provides utilities to register tools from the agent service tool registry
into the FastMCP server.
"""
from typing import Any, Callable
import inspect
from functools import wraps


def register_tools_from_registry(mcp_server: Any) -> None:
    """
    Register all tools from the tool registry as MCP tools.

    Args:
        mcp_server: FastMCP server instance
    """
    from agent_service.tools.registry import tool_registry

    # Get all registered tools
    tools = tool_registry.list_tools()

    for tool_schema in tools:
        # Create MCP tool wrapper
        mcp_tool_func = create_mcp_tool_wrapper(tool_schema.name, tool_registry)

        # Register with MCP server
        # FastMCP uses decorators, so we manually register the function
        mcp_server.tool(
            name=tool_schema.name,
            description=tool_schema.description
        )(mcp_tool_func)


def create_mcp_tool_wrapper(tool_name: str, tool_registry: Any) -> Callable:
    """
    Create an async wrapper function for a tool that can be registered with MCP.

    Args:
        tool_name: Name of the tool
        tool_registry: Tool registry instance

    Returns:
        Async function that executes the tool
    """
    async def mcp_tool_wrapper(**kwargs: Any) -> str:
        """
        Execute tool and return result.

        This wrapper is dynamically created for each tool.
        """
        try:
            result = await tool_registry.execute(tool_name, **kwargs)
            return str(result)
        except Exception as e:
            return f"Error executing tool {tool_name}: {str(e)}"

    # Set function metadata for MCP
    mcp_tool_wrapper.__name__ = tool_name
    mcp_tool_wrapper.__doc__ = f"Execute {tool_name} tool"

    return mcp_tool_wrapper


def convert_tool_to_mcp_format(tool_schema: Any) -> dict[str, Any]:
    """
    Convert an ITool schema to MCP tool format.

    Args:
        tool_schema: ToolSchema instance

    Returns:
        MCP tool definition
    """
    return {
        "name": tool_schema.name,
        "description": tool_schema.description,
        "inputSchema": tool_schema.parameters
    }


def create_tool_executor(tool_name: str) -> Callable:
    """
    Create a standalone executor function for a specific tool.

    Args:
        tool_name: Name of the tool to execute

    Returns:
        Async function that executes the tool
    """
    from agent_service.tools.registry import tool_registry

    async def execute_tool(**kwargs: Any) -> dict[str, Any]:
        """
        Execute a tool and return results.

        Args:
            **kwargs: Tool-specific arguments

        Returns:
            Tool execution result
        """
        try:
            result = await tool_registry.execute(tool_name, **kwargs)
            return {
                "success": True,
                "result": result,
                "tool": tool_name
            }
        except ValueError as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": "ValueError",
                "tool": tool_name
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "tool": tool_name
            }

    execute_tool.__name__ = f"execute_{tool_name}"
    execute_tool.__doc__ = f"Execute the {tool_name} tool"

    return execute_tool


def get_tool_parameters(tool_schema: Any) -> dict[str, Any]:
    """
    Extract parameter schema from a tool.

    Args:
        tool_schema: ToolSchema instance

    Returns:
        Parameter schema dictionary
    """
    return tool_schema.parameters


def validate_tool_arguments(tool_schema: Any, arguments: dict[str, Any]) -> tuple[bool, str | None]:
    """
    Validate arguments against tool schema.

    Args:
        tool_schema: ToolSchema instance
        arguments: Arguments to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    parameters = tool_schema.parameters
    required_params = parameters.get("required", [])

    # Check required parameters
    for param in required_params:
        if param not in arguments:
            return False, f"Missing required parameter: {param}"

    # Check parameter types (basic validation)
    properties = parameters.get("properties", {})
    for arg_name, arg_value in arguments.items():
        if arg_name in properties:
            expected_type = properties[arg_name].get("type")
            if expected_type:
                # Basic type checking
                type_map = {
                    "string": str,
                    "number": (int, float),
                    "integer": int,
                    "boolean": bool,
                    "object": dict,
                    "array": list
                }
                expected_python_type = type_map.get(expected_type)
                if expected_python_type and not isinstance(arg_value, expected_python_type):
                    return False, f"Parameter {arg_name} should be of type {expected_type}"

    return True, None
