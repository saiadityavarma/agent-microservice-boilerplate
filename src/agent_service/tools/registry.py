# src/agent_service/tools/registry.py
"""
Tool registry for managing tool instances.

Supports both class-based tools (ITool implementations) and
decorator-based tools created with @tool decorator.
"""
from typing import Any
from agent_service.interfaces import ITool, ToolSchema


class ToolRegistry:
    """
    Registry for tool implementations.

    Supports:
    - Class-based tools (implement ITool)
    - Decorator-based tools (use @tool decorator)

    Example:
        >>> # Class-based registration
        >>> registry.register(MyTool())
        >>>
        >>> # Decorator-based (auto-registered)
        >>> @tool(name="my_tool", description="Does something")
        >>> async def my_tool(arg: str) -> str:
        ...     return f"Result: {arg}"
        >>>
        >>> # Execute tool
        >>> result = await registry.execute("my_tool", arg="test")
    """

    def __init__(self):
        self._tools: dict[str, ITool] = {}

    def register(self, tool: ITool) -> None:
        """
        Register a tool.

        Args:
            tool: Tool instance (ITool implementation)

        Example:
            >>> registry.register(MyTool())
        """
        self._tools[tool.schema.name] = tool

    def unregister(self, name: str) -> None:
        """
        Unregister a tool by name.

        Args:
            name: Tool name to unregister

        Example:
            >>> registry.unregister("my_tool")
        """
        if name in self._tools:
            del self._tools[name]

    def get(self, name: str) -> ITool | None:
        """
        Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance or None if not found

        Example:
            >>> tool = registry.get("my_tool")
        """
        return self._tools.get(name)

    def list_tools(self) -> list[ToolSchema]:
        """
        List all registered tool schemas.

        Returns:
            List of tool schemas

        Example:
            >>> schemas = registry.list_tools()
            >>> for schema in schemas:
            ...     print(f"{schema.name}: {schema.description}")
        """
        return [t.schema for t in self._tools.values()]

    def list_tool_names(self) -> list[str]:
        """
        List all registered tool names.

        Returns:
            List of tool names

        Example:
            >>> names = registry.list_tool_names()
            >>> print(names)
            ['tool1', 'tool2', 'tool3']
        """
        return list(self._tools.keys())

    def to_openai_format(self) -> list[dict[str, Any]]:
        """
        Export tools in OpenAI function calling format.

        Returns:
            List of tools in OpenAI format

        Example:
            >>> tools = registry.to_openai_format()
            >>> response = client.chat.completions.create(
            ...     model="gpt-4",
            ...     messages=[...],
            ...     tools=tools
            ... )
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": t.schema.name,
                    "description": t.schema.description,
                    "parameters": t.schema.parameters,
                }
            }
            for t in self._tools.values()
        ]

    def to_anthropic_format(self) -> list[dict[str, Any]]:
        """
        Export tools in Anthropic Claude format.

        Returns:
            List of tools in Anthropic format

        Example:
            >>> tools = registry.to_anthropic_format()
            >>> response = client.messages.create(
            ...     model="claude-3-5-sonnet-20241022",
            ...     messages=[...],
            ...     tools=tools
            ... )
        """
        return [
            {
                "name": t.schema.name,
                "description": t.schema.description,
                "input_schema": t.schema.parameters,
            }
            for t in self._tools.values()
        ]

    async def execute(self, name: str, **kwargs: Any) -> Any:
        """
        Execute a tool by name.

        Args:
            name: Tool name
            **kwargs: Tool arguments

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool not found
            Exception: Any exception from tool execution

        Example:
            >>> result = await registry.execute("web_search", query="Python")
        """
        tool = self.get(name)
        if not tool:
            raise ValueError(f"Tool not found: {name}")
        return await tool.execute(**kwargs)

    def clear(self) -> None:
        """
        Clear all registered tools.

        Example:
            >>> registry.clear()
        """
        self._tools.clear()


# Global registry
tool_registry = ToolRegistry()
