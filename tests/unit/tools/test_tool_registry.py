# tests/unit/tools/test_tool_registry.py
"""Unit tests for tool registry."""

import pytest
from unittest.mock import Mock, AsyncMock

from agent_service.tools.registry import ToolRegistry
from agent_service.interfaces import ITool, ToolSchema


@pytest.mark.unit
class TestToolRegistry:
    """Test tool registry functionality."""

    def test_register_tool(self):
        """Test registering a tool."""
        registry = ToolRegistry()

        mock_tool = Mock(spec=ITool)
        mock_tool.schema = ToolSchema(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object"}
        )

        registry.register(mock_tool)

        assert registry.get("test_tool") == mock_tool

    def test_unregister_tool(self):
        """Test unregistering a tool."""
        registry = ToolRegistry()

        mock_tool = Mock(spec=ITool)
        mock_tool.schema = ToolSchema(
            name="test_tool",
            description="Test",
            parameters={}
        )

        registry.register(mock_tool)
        registry.unregister("test_tool")

        assert registry.get("test_tool") is None

    def test_get_nonexistent_tool(self):
        """Test getting non-existent tool returns None."""
        registry = ToolRegistry()

        assert registry.get("nonexistent") is None

    def test_list_tools(self):
        """Test listing all registered tools."""
        registry = ToolRegistry()

        tool1 = Mock(spec=ITool)
        tool1.schema = ToolSchema(name="tool1", description="First", parameters={})

        tool2 = Mock(spec=ITool)
        tool2.schema = ToolSchema(name="tool2", description="Second", parameters={})

        registry.register(tool1)
        registry.register(tool2)

        schemas = registry.list_tools()
        assert len(schemas) == 2
        assert any(s.name == "tool1" for s in schemas)
        assert any(s.name == "tool2" for s in schemas)

    def test_list_tool_names(self):
        """Test listing tool names."""
        registry = ToolRegistry()

        tool1 = Mock(spec=ITool)
        tool1.schema = ToolSchema(name="tool1", description="First", parameters={})

        tool2 = Mock(spec=ITool)
        tool2.schema = ToolSchema(name="tool2", description="Second", parameters={})

        registry.register(tool1)
        registry.register(tool2)

        names = registry.list_tool_names()
        assert "tool1" in names
        assert "tool2" in names
        assert len(names) == 2

    async def test_execute_tool(self):
        """Test executing a tool."""
        registry = ToolRegistry()

        mock_tool = AsyncMock(spec=ITool)
        mock_tool.schema = ToolSchema(name="test_tool", description="Test", parameters={})
        mock_tool.execute.return_value = {"result": "success"}

        registry.register(mock_tool)

        result = await registry.execute("test_tool", param="value")

        assert result == {"result": "success"}
        mock_tool.execute.assert_called_once_with(param="value")

    async def test_execute_nonexistent_tool_raises_error(self):
        """Test executing non-existent tool raises ValueError."""
        registry = ToolRegistry()

        with pytest.raises(ValueError, match="Tool not found"):
            await registry.execute("nonexistent")

    def test_clear_registry(self):
        """Test clearing all tools."""
        registry = ToolRegistry()

        tool = Mock(spec=ITool)
        tool.schema = ToolSchema(name="tool", description="Test", parameters={})

        registry.register(tool)
        registry.clear()

        assert len(registry.list_tools()) == 0
        assert registry.get("tool") is None

    def test_register_duplicate_tool_overwrites(self):
        """Test that registering tool with same name overwrites."""
        registry = ToolRegistry()

        tool1 = Mock(spec=ITool)
        tool1.schema = ToolSchema(name="tool", description="First", parameters={})

        tool2 = Mock(spec=ITool)
        tool2.schema = ToolSchema(name="tool", description="Second", parameters={})

        registry.register(tool1)
        registry.register(tool2)

        assert registry.get("tool") == tool2


@pytest.mark.unit
class TestToolFormats:
    """Test tool export formats."""

    def test_to_openai_format(self):
        """Test converting tools to OpenAI format."""
        registry = ToolRegistry()

        mock_tool = Mock(spec=ITool)
        mock_tool.schema = ToolSchema(
            name="test_tool",
            description="A test tool",
            parameters={
                "type": "object",
                "properties": {
                    "param1": {"type": "string"}
                }
            }
        )

        registry.register(mock_tool)

        openai_format = registry.to_openai_format()

        assert len(openai_format) == 1
        assert openai_format[0]["type"] == "function"
        assert openai_format[0]["function"]["name"] == "test_tool"
        assert openai_format[0]["function"]["description"] == "A test tool"
        assert "param1" in openai_format[0]["function"]["parameters"]["properties"]

    def test_to_anthropic_format(self):
        """Test converting tools to Anthropic format."""
        registry = ToolRegistry()

        mock_tool = Mock(spec=ITool)
        mock_tool.schema = ToolSchema(
            name="test_tool",
            description="A test tool",
            parameters={
                "type": "object",
                "properties": {
                    "param1": {"type": "string"}
                }
            }
        )

        registry.register(mock_tool)

        anthropic_format = registry.to_anthropic_format()

        assert len(anthropic_format) == 1
        assert anthropic_format[0]["name"] == "test_tool"
        assert anthropic_format[0]["description"] == "A test tool"
        assert "param1" in anthropic_format[0]["input_schema"]["properties"]

    def test_empty_registry_formats(self):
        """Test export formats with empty registry."""
        registry = ToolRegistry()

        assert registry.to_openai_format() == []
        assert registry.to_anthropic_format() == []


@pytest.mark.unit
class TestToolExecution:
    """Test tool execution scenarios."""

    async def test_tool_execution_with_multiple_params(self):
        """Test executing tool with multiple parameters."""
        registry = ToolRegistry()

        mock_tool = AsyncMock(spec=ITool)
        mock_tool.schema = ToolSchema(name="multi_param_tool", description="Test", parameters={})
        mock_tool.execute.return_value = "result"

        registry.register(mock_tool)

        await registry.execute("multi_param_tool", param1="value1", param2="value2")

        mock_tool.execute.assert_called_once_with(param1="value1", param2="value2")

    async def test_tool_execution_propagates_errors(self):
        """Test that tool execution errors are propagated."""
        registry = ToolRegistry()

        mock_tool = AsyncMock(spec=ITool)
        mock_tool.schema = ToolSchema(name="error_tool", description="Test", parameters={})
        mock_tool.execute.side_effect = RuntimeError("Tool execution failed")

        registry.register(mock_tool)

        with pytest.raises(RuntimeError, match="Tool execution failed"):
            await registry.execute("error_tool")

    async def test_tool_execution_with_no_params(self):
        """Test executing tool with no parameters."""
        registry = ToolRegistry()

        mock_tool = AsyncMock(spec=ITool)
        mock_tool.schema = ToolSchema(name="no_param_tool", description="Test", parameters={})
        mock_tool.execute.return_value = "success"

        registry.register(mock_tool)

        result = await registry.execute("no_param_tool")

        assert result == "success"
        mock_tool.execute.assert_called_once_with()


@pytest.mark.unit
class TestToolSchema:
    """Test tool schema validation."""

    def test_tool_schema_creation(self):
        """Test creating tool schema."""
        schema = ToolSchema(
            name="test_tool",
            description="A test tool",
            parameters={
                "type": "object",
                "properties": {
                    "param": {"type": "string"}
                },
                "required": ["param"]
            }
        )

        assert schema.name == "test_tool"
        assert schema.description == "A test tool"
        assert "param" in schema.parameters["properties"]
        assert "param" in schema.parameters["required"]

    def test_tool_schema_with_minimal_params(self):
        """Test tool schema with minimal parameters."""
        schema = ToolSchema(
            name="minimal_tool",
            description="Minimal tool",
            parameters={"type": "object"}
        )

        assert schema.name == "minimal_tool"
        assert schema.parameters["type"] == "object"
