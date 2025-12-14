"""
Tool decorator for easy tool creation.

Provides a decorator-based approach to creating tools without implementing
the full ITool interface manually. Automatically generates schema from
function signature and type annotations.
"""

from __future__ import annotations
from typing import Callable, Any, get_type_hints, get_origin, get_args, Awaitable
from functools import wraps
import inspect
import asyncio
import time

from agent_service.interfaces import ITool, ToolSchema
from agent_service.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


def _python_type_to_json_schema(py_type: Any) -> dict[str, Any]:
    """
    Convert Python type annotation to JSON Schema type.

    Args:
        py_type: Python type annotation

    Returns:
        JSON Schema type definition

    Example:
        >>> _python_type_to_json_schema(str)
        {'type': 'string'}
        >>> _python_type_to_json_schema(int)
        {'type': 'integer'}
    """
    # Handle None type
    if py_type is type(None):
        return {"type": "null"}

    # Handle string types
    origin = get_origin(py_type)

    # Handle Optional[T] (Union[T, None])
    if origin is type(None) or str(origin) == "typing.Union":
        args = get_args(py_type)
        if args:
            # Filter out None type
            non_none_types = [arg for arg in args if arg is not type(None)]
            if len(non_none_types) == 1:
                schema = _python_type_to_json_schema(non_none_types[0])
                # Mark as nullable if None was in the union
                if len(args) > len(non_none_types):
                    schema["nullable"] = True
                return schema
            elif len(non_none_types) > 1:
                return {
                    "oneOf": [_python_type_to_json_schema(t) for t in non_none_types],
                    "nullable": len(args) > len(non_none_types),
                }

    # Handle list types
    if origin is list:
        args = get_args(py_type)
        if args:
            return {
                "type": "array",
                "items": _python_type_to_json_schema(args[0]),
            }
        return {"type": "array"}

    # Handle dict types
    if origin is dict:
        args = get_args(py_type)
        if args and len(args) == 2:
            return {
                "type": "object",
                "additionalProperties": _python_type_to_json_schema(args[1]),
            }
        return {"type": "object"}

    # Handle basic types
    type_mapping = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        dict: {"type": "object"},
        list: {"type": "array"},
        Any: {},  # Any type - no restriction
    }

    # Check if it's a basic type
    if py_type in type_mapping:
        return type_mapping[py_type]

    # Default to object for unknown types
    return {"type": "object"}


def _generate_schema_from_function(
    func: Callable,
    name: str,
    description: str,
) -> dict[str, Any]:
    """
    Generate JSON Schema parameters from function signature.

    Args:
        func: Function to analyze
        name: Tool name
        description: Tool description

    Returns:
        JSON Schema parameters object

    Example:
        >>> def my_func(query: str, limit: int = 10) -> str:
        ...     pass
        >>> schema = _generate_schema_from_function(my_func, "my_tool", "Does stuff")
        >>> schema["properties"]["query"]
        {'type': 'string', 'description': ''}
    """
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        # Skip **kwargs
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            continue

        # Skip *args
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            continue

        # Get type annotation
        param_type = type_hints.get(param_name, Any)

        # Convert to JSON Schema
        param_schema = _python_type_to_json_schema(param_type)

        # Add description from docstring if available
        param_schema["description"] = ""

        properties[param_name] = param_schema

        # Check if required (no default value)
        if param.default == inspect.Parameter.empty:
            required.append(param_name)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


class DecoratedTool(ITool):
    """
    ITool implementation that wraps a decorated function.

    Automatically handles:
    - Schema generation from function signature
    - Type validation
    - Error handling
    - Timeout handling
    - Metrics collection
    """

    def __init__(
        self,
        func: Callable[..., Awaitable[Any]],
        name: str,
        description: str,
        requires_confirmation: bool = False,
        timeout: float | None = None,
        auto_register: bool = True,
    ):
        """
        Initialize a decorated tool.

        Args:
            func: The tool function to wrap
            name: Tool name
            description: Tool description
            requires_confirmation: Whether tool requires user confirmation
            timeout: Timeout in seconds (None = no timeout)
            auto_register: Whether to auto-register with the tool registry
        """
        self._func = func
        self._name = name
        self._description = description
        self._requires_confirmation = requires_confirmation
        self._timeout = timeout

        # Generate schema from function signature
        self._parameters = _generate_schema_from_function(func, name, description)

        # Auto-register if requested
        if auto_register:
            from agent_service.tools.registry import tool_registry

            tool_registry.register(self)
            logger.info(
                "tool_registered",
                tool=name,
                description=description,
                requires_confirmation=requires_confirmation,
            )

    @property
    def schema(self) -> ToolSchema:
        """Get tool schema."""
        return ToolSchema(
            name=self._name,
            description=self._description,
            parameters=self._parameters,
        )

    @property
    def requires_confirmation(self) -> bool:
        """Check if tool requires confirmation."""
        return self._requires_confirmation

    async def execute(self, **kwargs: Any) -> Any:
        """
        Execute the tool function with validation and error handling.

        Args:
            **kwargs: Tool arguments

        Returns:
            Tool execution result

        Raises:
            ValueError: If validation fails
            TimeoutError: If execution times out
            Exception: Any exception from the tool function
        """
        start_time = time.time()

        logger.info(
            "tool_execution_started",
            tool=self._name,
            args=list(kwargs.keys()),
        )

        try:
            # Execute with timeout if specified
            if self._timeout:
                result = await asyncio.wait_for(
                    self._func(**kwargs),
                    timeout=self._timeout,
                )
            else:
                result = await self._func(**kwargs)

            duration = time.time() - start_time
            logger.info(
                "tool_execution_completed",
                tool=self._name,
                success=True,
                duration_seconds=duration,
            )

            return result

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            logger.error(
                "tool_execution_timeout",
                tool=self._name,
                timeout_seconds=self._timeout,
                duration_seconds=duration,
            )
            raise TimeoutError(
                f"Tool '{self._name}' execution timed out after {self._timeout}s"
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "tool_execution_failed",
                tool=self._name,
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=duration,
                exc_info=True,
            )
            raise


def tool(
    name: str | None = None,
    description: str | None = None,
    requires_confirmation: bool = False,
    timeout: float | None = None,
    auto_register: bool = True,
) -> Callable:
    """
    Decorator to create a tool from a simple async function.

    The decorated function's signature and type annotations are used to
    automatically generate the tool schema. The function must be async.

    Args:
        name: Tool name (defaults to function name)
        description: Tool description (defaults to function docstring)
        requires_confirmation: Whether tool requires user confirmation (default: False)
        timeout: Timeout in seconds (None = no timeout)
        auto_register: Whether to auto-register with the tool registry (default: True)

    Returns:
        Decorated tool

    Example (basic):
        >>> @tool(name="web_search", description="Search the web")
        >>> async def web_search(query: str, max_results: int = 10) -> list[dict]:
        ...     # Implementation here
        ...     return [{"title": "Result 1", "url": "http://..."}]

    Example (with confirmation):
        >>> @tool(
        ...     name="delete_file",
        ...     description="Delete a file",
        ...     requires_confirmation=True
        ... )
        >>> async def delete_file(path: str) -> dict:
        ...     import os
        ...     os.remove(path)
        ...     return {"deleted": path}

    Example (with timeout):
        >>> @tool(name="slow_task", description="Long running task", timeout=30.0)
        >>> async def slow_task(iterations: int) -> str:
        ...     import asyncio
        ...     for i in range(iterations):
        ...         await asyncio.sleep(1)
        ...     return f"Completed {iterations} iterations"

    Example (complex types):
        >>> @tool(name="process_data", description="Process structured data")
        >>> async def process_data(
        ...     data: dict[str, Any],
        ...     filters: list[str] | None = None,
        ...     threshold: float = 0.5
        ... ) -> dict:
        ...     # Process data with filters
        ...     return {"processed": True, "count": len(data)}
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> DecoratedTool:
        # Validate function is async
        if not inspect.iscoroutinefunction(func):
            raise TypeError(
                f"Tool function '{func.__name__}' must be async (use 'async def')"
            )

        # Determine name and description
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or f"Tool: {tool_name}"

        # Create the decorated tool
        decorated = DecoratedTool(
            func=func,
            name=tool_name,
            description=tool_description,
            requires_confirmation=requires_confirmation,
            timeout=timeout,
            auto_register=auto_register,
        )

        return decorated

    return decorator


def confirmed_tool(
    name: str | None = None,
    description: str | None = None,
    timeout: float | None = None,
    auto_register: bool = True,
) -> Callable:
    """
    Decorator for tools that require user confirmation before execution.

    This is a convenience wrapper around @tool with requires_confirmation=True.

    Args:
        name: Tool name (defaults to function name)
        description: Tool description (defaults to function docstring)
        timeout: Timeout in seconds (None = no timeout)
        auto_register: Whether to auto-register with the tool registry (default: True)

    Returns:
        Decorated tool that requires confirmation

    Example:
        >>> @confirmed_tool(name="execute_code", description="Execute Python code")
        >>> async def execute_code(code: str) -> str:
        ...     # Execute code (dangerous!)
        ...     return exec(code)
    """
    return tool(
        name=name,
        description=description,
        requires_confirmation=True,
        timeout=timeout,
        auto_register=auto_register,
    )
