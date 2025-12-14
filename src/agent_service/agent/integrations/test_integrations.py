"""
Basic tests for framework integrations.

Run with: pytest test_integrations.py
"""

import pytest
from agent_service.interfaces.agent import AgentInput, AgentOutput
from agent_service.agent.config import AgentConfig


class TestAgentConfig:
    """Test AgentConfig functionality."""

    def test_default_config(self):
        """Test default configuration values."""
        config = AgentConfig()
        assert config.timeout == 300
        assert config.max_tokens == 4096
        assert config.temperature == 0.7
        assert config.enabled_tools is None
        assert config.disabled_tools is None
        assert config.rate_limit == "100/hour"

    def test_custom_config(self):
        """Test custom configuration."""
        config = AgentConfig(
            timeout=60,
            max_tokens=1000,
            temperature=0.5,
            model="gpt-4",
        )
        assert config.timeout == 60
        assert config.max_tokens == 1000
        assert config.temperature == 0.5
        assert config.model == "gpt-4"

    def test_config_merge(self):
        """Test merging configurations."""
        base = AgentConfig(timeout=300, temperature=0.7)
        override = AgentConfig(temperature=0.9, model="gpt-4")

        merged = base.merge(override)
        assert merged.timeout == 300  # From base
        assert merged.temperature == 0.9  # From override
        assert merged.model == "gpt-4"  # From override

    def test_filter_tools(self):
        """Test tool filtering."""
        available = ["tool1", "tool2", "tool3", "tool4"]

        # Test whitelist
        config = AgentConfig(enabled_tools=["tool1", "tool2"])
        filtered = config.filter_tools(available)
        assert set(filtered) == {"tool1", "tool2"}

        # Test blacklist
        config = AgentConfig(disabled_tools=["tool3"])
        filtered = config.filter_tools(available)
        assert set(filtered) == {"tool1", "tool2", "tool4"}

        # Test both
        config = AgentConfig(
            enabled_tools=["tool1", "tool2", "tool3"],
            disabled_tools=["tool2"],
        )
        filtered = config.filter_tools(available)
        assert set(filtered) == {"tool1", "tool3"}

    def test_yaml_round_trip(self, tmp_path):
        """Test saving and loading YAML."""
        config = AgentConfig(
            timeout=60,
            temperature=0.5,
            model="gpt-4",
            enabled_tools=["tool1"],
            metadata={"custom": "value"},
        )

        # Save to YAML
        yaml_file = tmp_path / "config.yaml"
        config.to_yaml(yaml_file)

        # Load from YAML
        loaded = AgentConfig.from_yaml(yaml_file)
        assert loaded.timeout == 60
        assert loaded.temperature == 0.5
        assert loaded.model == "gpt-4"
        assert loaded.enabled_tools == ["tool1"]
        assert loaded.metadata == {"custom": "value"}


class TestIntegrationAvailability:
    """Test integration availability checks."""

    def test_check_integrations(self):
        """Test checking integration availability."""
        from agent_service.agent.integrations import check_integrations

        status = check_integrations()
        assert isinstance(status, dict)
        assert "langgraph" in status
        assert "crewai" in status
        assert "openai" in status
        assert all(isinstance(v, bool) for v in status.values())

    def test_get_missing_integrations(self):
        """Test getting missing integrations."""
        from agent_service.agent.integrations import get_missing_integrations

        missing = get_missing_integrations()
        assert isinstance(missing, list)
        assert all(isinstance(name, str) for name in missing)


# Conditional tests based on availability

@pytest.mark.skipif(
    not pytest.importorskip("langgraph", reason="langgraph not installed"),
    reason="langgraph not available"
)
class TestLangGraphIntegration:
    """Test LangGraph integration."""

    def test_langgraph_available(self):
        """Test that LangGraph integration is available."""
        from agent_service.agent.integrations import LANGGRAPH_AVAILABLE
        assert LANGGRAPH_AVAILABLE

    def test_langgraph_agent_creation(self):
        """Test creating a LangGraph agent."""
        from agent_service.agent.integrations import LangGraphAgent
        from langgraph.graph import StateGraph, END
        from typing import TypedDict

        class State(TypedDict):
            messages: list[dict]

        def node(state: State) -> State:
            return state

        graph = StateGraph(State)
        graph.add_node("node", node)
        graph.set_entry_point("node")
        graph.add_edge("node", END)
        compiled = graph.compile()

        agent = LangGraphAgent(
            graph=compiled,
            name="test_lg",
            description="Test agent",
        )

        assert agent.name == "test_lg"
        assert agent.description == "Test agent"


@pytest.mark.skipif(
    not pytest.importorskip("openai", reason="openai not installed"),
    reason="openai not available"
)
class TestOpenAIIntegration:
    """Test OpenAI integration."""

    def test_openai_available(self):
        """Test that OpenAI integration is available."""
        from agent_service.agent.integrations import OPENAI_AVAILABLE
        assert OPENAI_AVAILABLE

    def test_tool_to_openai_format(self):
        """Test converting tools to OpenAI format."""
        from agent_service.agent.integrations import tool_to_openai_format

        tool = tool_to_openai_format(
            name="test_tool",
            description="A test tool",
            parameters={
                "type": "object",
                "properties": {
                    "arg": {"type": "string"}
                },
                "required": ["arg"]
            }
        )

        assert tool["type"] == "function"
        assert tool["function"]["name"] == "test_tool"
        assert tool["function"]["description"] == "A test tool"
        assert "properties" in tool["function"]["parameters"]

    def test_openai_agent_creation(self):
        """Test creating an OpenAI agent."""
        from agent_service.agent.integrations import OpenAIFunctionAgent

        def test_tool(arg: str) -> str:
            return f"Result: {arg}"

        agent = OpenAIFunctionAgent(
            name="test_oai",
            model="gpt-4",
            tools=[],
            tool_executors={"test_tool": test_tool},
            description="Test agent",
        )

        assert agent.name == "test_oai"
        assert agent.description == "Test agent"


# Integration test with mocking
@pytest.mark.asyncio
async def test_agent_input_output():
    """Test basic AgentInput/AgentOutput flow."""
    input_data = AgentInput(
        message="Test message",
        session_id="test-session",
        context={"key": "value"},
    )

    assert input_data.message == "Test message"
    assert input_data.session_id == "test-session"
    assert input_data.context == {"key": "value"}

    output_data = AgentOutput(
        content="Test response",
        tool_calls=[{"name": "tool1", "args": {}}],
        metadata={"usage": {"tokens": 100}},
    )

    assert output_data.content == "Test response"
    assert len(output_data.tool_calls) == 1
    assert output_data.metadata["usage"]["tokens"] == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
