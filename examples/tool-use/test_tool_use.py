"""
Tests for Tool-Using Agent
"""

import pytest
import json
from agent_service.interfaces import AgentInput, AgentOutput
from agent_service.agent import AgentContext, agent_registry
from agent_service.tools import tool_registry
from agent_service.infrastructure.cache.cache import get_cache

# Import to register agents and tools
from examples.tool_use.agent import (
    tool_agent,
    tool_chain_agent,
    parallel_tool_agent,
    parse_intent,
    extract_expression,
    extract_search_query,
    parse_conversion
)
from examples.tool_use.tools import (
    calculate,
    convert_units,
    web_search,
    read_file,
    write_file,
    parse_json,
    format_json,
    extract_data,
    http_request,
    get_current_time,
    format_date
)


@pytest.fixture
async def agent_context():
    """Create a test agent context."""
    cache = await get_cache(namespace="test:tool_use")
    return AgentContext(
        tools=tool_registry,
        cache=cache,
        db=None,
        logger=None,
        user=None,
        request_id="test-request-123"
    )


class TestTools:
    """Test individual tools."""

    @pytest.mark.asyncio
    async def test_calculate(self):
        """Test calculator tool."""
        result = await calculate.execute(expression="2 + 2")
        assert result["success"] is True
        assert result["result"] == 4

        result = await calculate.execute(expression="10 * 5")
        assert result["result"] == 50

    @pytest.mark.asyncio
    async def test_calculate_complex(self):
        """Test complex calculations."""
        result = await calculate.execute(expression="sqrt(16) * 2")
        assert result["success"] is True
        assert result["result"] == 8.0

    @pytest.mark.asyncio
    async def test_calculate_error(self):
        """Test calculator error handling."""
        result = await calculate.execute(expression="invalid expression")
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_convert_units_temperature(self):
        """Test temperature conversion."""
        # Celsius to Fahrenheit
        result = await convert_units.execute(value=0, from_unit="C", to_unit="F")
        assert result["success"] is True
        assert result["converted_value"] == 32

        # Fahrenheit to Celsius
        result = await convert_units.execute(value=32, from_unit="F", to_unit="C")
        assert result["success"] is True
        assert result["converted_value"] == 0

    @pytest.mark.asyncio
    async def test_convert_units_length(self):
        """Test length conversion."""
        result = await convert_units.execute(value=1, from_unit="km", to_unit="m")
        assert result["success"] is True
        assert result["converted_value"] == 1000

    @pytest.mark.asyncio
    async def test_convert_units_invalid(self):
        """Test invalid conversion."""
        result = await convert_units.execute(value=100, from_unit="X", to_unit="Y")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_web_search(self):
        """Test web search tool."""
        result = await web_search.execute(query="Python programming", max_results=3)

        assert "results" in result
        assert "count" in result
        assert len(result["results"]) <= 3
        assert all("title" in r for r in result["results"])
        assert all("url" in r for r in result["results"])

    @pytest.mark.asyncio
    async def test_parse_json(self):
        """Test JSON parsing."""
        json_str = '{"name": "test", "value": 123}'
        result = await parse_json.execute(json_string=json_str)

        assert result["success"] is True
        assert result["data"]["name"] == "test"
        assert result["data"]["value"] == 123

    @pytest.mark.asyncio
    async def test_parse_json_invalid(self):
        """Test invalid JSON."""
        result = await parse_json.execute(json_string="invalid json")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_format_json(self):
        """Test JSON formatting."""
        data = {"name": "test", "nested": {"key": "value"}}
        result = await format_json.execute(data=data)

        assert result["success"] is True
        assert "formatted" in result
        # Check it's valid JSON
        parsed = json.loads(result["formatted"])
        assert parsed == data

    @pytest.mark.asyncio
    async def test_extract_data(self):
        """Test data extraction."""
        data = {
            "name": "John",
            "address": {
                "city": "New York",
                "zip": "10001"
            }
        }

        result = await extract_data.execute(
            data=data,
            fields=["name", "address.city"]
        )

        assert result["success"] is True
        assert result["extracted"]["name"] == "John"
        assert result["extracted"]["address.city"] == "New York"

    @pytest.mark.asyncio
    async def test_http_request(self):
        """Test HTTP request."""
        result = await http_request.execute(url="https://example.com")

        assert "status_code" in result
        assert "content" in result
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_get_current_time(self):
        """Test getting current time."""
        result = await get_current_time.execute(timezone="UTC")

        assert "datetime" in result
        assert "date" in result
        assert "time" in result
        assert result["timezone"] == "UTC"

    @pytest.mark.asyncio
    async def test_format_date(self):
        """Test date formatting."""
        result = await format_date.execute(
            date_string="2024-01-15",
            format="%Y-%m-%d"
        )

        assert result["success"] is True
        assert "formatted" in result


class TestToolAgents:
    """Test tool-using agents."""

    @pytest.mark.asyncio
    async def test_tool_agent_calculation(self, agent_context):
        """Test tool agent with calculation."""
        result = await tool_agent(
            AgentInput(message="Calculate 10 + 20"),
            agent_context
        )

        assert isinstance(result, AgentOutput)
        assert "30" in result.content
        assert "calculate" in result.metadata["tools_used"]

    @pytest.mark.asyncio
    async def test_tool_agent_search(self, agent_context):
        """Test tool agent with search."""
        result = await tool_agent(
            AgentInput(message="Search for Python tutorials"),
            agent_context
        )

        assert isinstance(result, AgentOutput)
        assert len(result.content) > 0
        assert "web_search" in result.metadata["tools_used"]

    @pytest.mark.asyncio
    async def test_tool_agent_time(self, agent_context):
        """Test tool agent with time query."""
        result = await tool_agent(
            AgentInput(message="What time is it?"),
            agent_context
        )

        assert isinstance(result, AgentOutput)
        assert "get_current_time" in result.metadata["tools_used"]

    @pytest.mark.asyncio
    async def test_tool_agent_conversion(self, agent_context):
        """Test tool agent with unit conversion."""
        result = await tool_agent(
            AgentInput(message="Convert 100 F to C"),
            agent_context
        )

        assert isinstance(result, AgentOutput)
        assert "convert_units" in result.metadata["tools_used"]

    @pytest.mark.asyncio
    async def test_tool_agent_unknown_intent(self, agent_context):
        """Test tool agent with unknown intent."""
        result = await tool_agent(
            AgentInput(message="Something random"),
            agent_context
        )

        assert isinstance(result, AgentOutput)
        assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_tool_chain_agent(self, agent_context):
        """Test tool chaining agent."""
        result = await tool_chain_agent(
            AgentInput(message="Search for Python and format as JSON"),
            agent_context
        )

        assert isinstance(result, AgentOutput)
        assert len(result.metadata.get("tools_used", [])) > 0

    @pytest.mark.asyncio
    async def test_parallel_tool_agent(self, agent_context):
        """Test parallel tool agent."""
        result = await parallel_tool_agent(
            AgentInput(message="Get time and search for Python"),
            agent_context
        )

        assert isinstance(result, AgentOutput)
        assert result.metadata.get("parallel_count", 0) > 1
        assert len(result.metadata.get("tools_used", [])) > 1


class TestHelperFunctions:
    """Test helper functions."""

    def test_parse_intent_calculation(self):
        """Test intent parsing for calculations."""
        assert parse_intent("Calculate 2 + 2") == "calculation"
        assert parse_intent("What is 10 * 5?") == "calculation"
        assert parse_intent("Compute 100 / 4") == "calculation"

    def test_parse_intent_search(self):
        """Test intent parsing for search."""
        assert parse_intent("Search for Python") == "search"
        assert parse_intent("Find information about AI") == "search"
        assert parse_intent("Google machine learning") == "search"

    def test_parse_intent_time(self):
        """Test intent parsing for time queries."""
        assert parse_intent("What time is it?") == "time"
        assert parse_intent("Current date") == "time"
        assert parse_intent("When is it?") == "time"

    def test_parse_intent_conversion(self):
        """Test intent parsing for conversions."""
        assert parse_intent("Convert 100 F to C") == "conversion"
        assert parse_intent("5 km to mi") == "conversion"

    def test_extract_expression(self):
        """Test expression extraction."""
        expr = extract_expression("Calculate 2 + 2")
        assert "2" in expr and "+" in expr

        expr = extract_expression("What is 10 * 5?")
        assert "10" in expr and "*" in expr and "5" in expr

    def test_extract_search_query(self):
        """Test search query extraction."""
        query = extract_search_query("Search for Python tutorials")
        assert "python" in query.lower()
        assert "search" not in query.lower()

        query = extract_search_query("Find AI resources")
        assert "ai" in query.lower()

    def test_parse_conversion(self):
        """Test conversion parsing."""
        conv = parse_conversion("Convert 100 F to C")
        assert conv is not None
        assert conv["value"] == 100
        assert conv["from_unit"] == "F"
        assert conv["to_unit"] == "C"

        conv = parse_conversion("5 km to mi")
        assert conv is not None
        assert conv["value"] == 5
        assert conv["from_unit"] == "KM"
        assert conv["to_unit"] == "MI"

    def test_parse_conversion_invalid(self):
        """Test invalid conversion parsing."""
        conv = parse_conversion("Random text")
        assert conv is None


class TestIntegration:
    """Integration tests."""

    @pytest.mark.asyncio
    async def test_end_to_end_calculation(self, agent_context):
        """Test complete calculation workflow."""
        # Agent receives query
        result = await tool_agent(
            AgentInput(message="Calculate sqrt(16) * 3"),
            agent_context
        )

        # Should have called calculator
        assert "calculate" in result.metadata["tools_used"]
        # Should have result
        assert "12" in result.content or "12.0" in result.content

    @pytest.mark.asyncio
    async def test_end_to_end_search_and_format(self, agent_context):
        """Test search and format workflow."""
        result = await tool_chain_agent(
            AgentInput(message="Search for Python and format as JSON"),
            agent_context
        )

        # Should have used multiple tools
        assert len(result.metadata.get("tools_used", [])) > 1

    @pytest.mark.asyncio
    async def test_agent_registry_integration(self):
        """Test that agents are registered."""
        assert agent_registry.get("tool_agent") is not None
        assert agent_registry.get("tool_chain_agent") is not None
        assert agent_registry.get("parallel_tool_agent") is not None

    @pytest.mark.asyncio
    async def test_tool_registry_integration(self):
        """Test that tools are registered."""
        # Calculator tools
        assert tool_registry.get("calculate") is not None
        assert tool_registry.get("convert_units") is not None

        # Information tools
        assert tool_registry.get("web_search") is not None
        assert tool_registry.get("get_current_time") is not None

        # Data tools
        assert tool_registry.get("parse_json") is not None
        assert tool_registry.get("format_json") is not None

    @pytest.mark.asyncio
    async def test_multiple_agents_same_tools(self, agent_context):
        """Test multiple agents using the same tools."""
        # Both agents use web_search
        result1 = await tool_agent(
            AgentInput(message="Search for Python"),
            agent_context
        )

        result2 = await tool_chain_agent(
            AgentInput(message="Search for JavaScript and format as JSON"),
            agent_context
        )

        # Both should have used web_search
        assert "web_search" in result1.metadata["tools_used"]
        assert "web_search" in result2.metadata["tools_used"]


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_tool_agent_handles_errors(self, agent_context):
        """Test that agent handles tool errors gracefully."""
        # This should not crash
        result = await tool_agent(
            AgentInput(message=""),
            agent_context
        )

        assert isinstance(result, AgentOutput)

    @pytest.mark.asyncio
    async def test_invalid_calculation(self):
        """Test calculator with invalid expression."""
        result = await calculate.execute(expression="invalid / expression *")
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_tool_timeout(self):
        """Test tool timeout handling."""
        # Tools have timeout configuration
        # In a real test, you'd trigger a timeout
        assert calculate._timeout == 5.0
        assert web_search._timeout == 10.0


class TestToolConfirmation:
    """Test tool confirmation requirements."""

    @pytest.mark.asyncio
    async def test_write_file_requires_confirmation(self):
        """Test that write_file requires confirmation."""
        assert write_file.requires_confirmation is True

    @pytest.mark.asyncio
    async def test_regular_tools_no_confirmation(self):
        """Test that regular tools don't require confirmation."""
        assert calculate.requires_confirmation is False
        assert web_search.requires_confirmation is False


class TestToolMetadata:
    """Test tool metadata and schema."""

    def test_tool_schemas(self):
        """Test that tools have proper schemas."""
        calc_schema = calculate.schema
        assert calc_schema.name == "calculate"
        assert "expression" in calc_schema.parameters["properties"]

        search_schema = web_search.schema
        assert search_schema.name == "web_search"
        assert "query" in search_schema.parameters["properties"]

    def test_tool_descriptions(self):
        """Test that tools have descriptions."""
        assert len(calculate.schema.description) > 0
        assert len(web_search.schema.description) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
