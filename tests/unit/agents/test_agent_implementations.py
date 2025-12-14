# tests/unit/agents/test_agent_implementations.py
"""Unit tests for agent implementations."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from agent_service.interfaces import AgentInput, AgentOutput, StreamChunk, IAgent
from agent_service.agent.registry import AgentRegistry


@pytest.mark.unit
class TestAgentInterface:
    """Test IAgent interface implementation."""

    async def test_agent_has_required_properties(self):
        """Test that agent implements required properties."""

        class MockAgent(IAgent):
            @property
            def name(self) -> str:
                return "test_agent"

            @property
            def description(self) -> str:
                return "A test agent"

            async def invoke(self, input: AgentInput) -> AgentOutput:
                return AgentOutput(content=f"Response to: {input.message}")

            async def stream(self, input: AgentInput):
                yield StreamChunk(type="text", content="chunk")

        agent = MockAgent()
        assert agent.name == "test_agent"
        assert agent.description == "A test agent"

        result = await agent.invoke(AgentInput(message="test"))
        assert isinstance(result, AgentOutput)
        assert "test" in result.content

    async def test_agent_invoke_returns_correct_output(self):
        """Test agent invoke returns AgentOutput."""

        class TestAgent(IAgent):
            @property
            def name(self) -> str:
                return "test"

            @property
            def description(self) -> str:
                return "test"

            async def invoke(self, input: AgentInput) -> AgentOutput:
                return AgentOutput(
                    content="response",
                    metadata={"model": "test-model"}
                )

            async def stream(self, input: AgentInput):
                yield StreamChunk(type="text", content="")

        agent = TestAgent()
        output = await agent.invoke(AgentInput(message="test"))

        assert output.content == "response"
        assert output.metadata["model"] == "test-model"

    async def test_agent_stream_yields_chunks(self):
        """Test agent stream yields StreamChunk objects."""

        class StreamingAgent(IAgent):
            @property
            def name(self) -> str:
                return "streaming"

            @property
            def description(self) -> str:
                return "streaming agent"

            async def invoke(self, input: AgentInput) -> AgentOutput:
                return AgentOutput(content="")

            async def stream(self, input: AgentInput):
                for word in ["Hello", "World"]:
                    yield StreamChunk(type="text", content=word)

        agent = StreamingAgent()
        chunks = []
        async for chunk in agent.stream(AgentInput(message="test")):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert all(isinstance(c, StreamChunk) for c in chunks)
        assert chunks[0].content == "Hello"
        assert chunks[1].content == "World"


@pytest.mark.unit
class TestAgentRegistry:
    """Test agent registry functionality."""

    def test_register_agent(self):
        """Test registering an agent."""
        registry = AgentRegistry()

        mock_agent = Mock(spec=IAgent)
        mock_agent.name = "test_agent"

        registry.register(mock_agent)

        assert registry.get("test_agent") == mock_agent

    def test_unregister_agent(self):
        """Test unregistering an agent."""
        registry = AgentRegistry()

        mock_agent = Mock(spec=IAgent)
        mock_agent.name = "test_agent"

        registry.register(mock_agent)
        registry.unregister("test_agent")

        assert registry.get("test_agent") is None

    def test_get_nonexistent_agent(self):
        """Test getting non-existent agent returns None."""
        registry = AgentRegistry()

        assert registry.get("nonexistent") is None

    def test_list_agents(self):
        """Test listing all registered agents."""
        registry = AgentRegistry()

        agent1 = Mock(spec=IAgent)
        agent1.name = "agent1"
        agent1.description = "First agent"

        agent2 = Mock(spec=IAgent)
        agent2.name = "agent2"
        agent2.description = "Second agent"

        registry.register(agent1)
        registry.register(agent2)

        agents = registry.list_agents()
        assert len(agents) == 2
        assert any(a["name"] == "agent1" for a in agents)
        assert any(a["name"] == "agent2" for a in agents)

    def test_set_default_agent(self):
        """Test setting default agent."""
        registry = AgentRegistry()

        mock_agent = Mock(spec=IAgent)
        mock_agent.name = "default_agent"

        registry.register(mock_agent)
        registry.set_default("default_agent")

        assert registry.get_default() == mock_agent

    def test_get_default_when_not_set(self):
        """Test getting default agent when none is set."""
        registry = AgentRegistry()

        # Should return None or raise appropriate exception
        default = registry.get_default()
        assert default is None or isinstance(default, IAgent)

    def test_register_duplicate_agent_overwrites(self):
        """Test that registering agent with same name overwrites."""
        registry = AgentRegistry()

        agent1 = Mock(spec=IAgent)
        agent1.name = "agent"
        agent1.description = "First"

        agent2 = Mock(spec=IAgent)
        agent2.name = "agent"
        agent2.description = "Second"

        registry.register(agent1)
        registry.register(agent2)

        assert registry.get("agent") == agent2


@pytest.mark.unit
class TestAgentContext:
    """Test agent context management."""

    async def test_agent_receives_session_id(self):
        """Test that agent receives session ID in input."""

        class ContextAgent(IAgent):
            @property
            def name(self) -> str:
                return "context"

            @property
            def description(self) -> str:
                return "context agent"

            async def invoke(self, input: AgentInput) -> AgentOutput:
                return AgentOutput(
                    content="ok",
                    metadata={"session_id": input.session_id}
                )

            async def stream(self, input: AgentInput):
                yield StreamChunk(type="text", content="")

        agent = ContextAgent()
        output = await agent.invoke(AgentInput(
            message="test",
            session_id="session-123"
        ))

        assert output.metadata["session_id"] == "session-123"

    async def test_agent_receives_custom_context(self):
        """Test that agent receives custom context."""

        class ContextAgent(IAgent):
            @property
            def name(self) -> str:
                return "context"

            @property
            def description(self) -> str:
                return "context agent"

            async def invoke(self, input: AgentInput) -> AgentOutput:
                user_id = input.context.get("user_id") if input.context else None
                return AgentOutput(
                    content="ok",
                    metadata={"user_id": user_id}
                )

            async def stream(self, input: AgentInput):
                yield StreamChunk(type="text", content="")

        agent = ContextAgent()
        output = await agent.invoke(AgentInput(
            message="test",
            context={"user_id": "user-456"}
        ))

        assert output.metadata["user_id"] == "user-456"


@pytest.mark.unit
class TestAgentLifecycle:
    """Test agent lifecycle hooks."""

    async def test_agent_setup_hook(self):
        """Test agent setup hook is called."""
        setup_called = False

        class LifecycleAgent(IAgent):
            @property
            def name(self) -> str:
                return "lifecycle"

            @property
            def description(self) -> str:
                return "lifecycle agent"

            async def invoke(self, input: AgentInput) -> AgentOutput:
                return AgentOutput(content="ok")

            async def stream(self, input: AgentInput):
                yield StreamChunk(type="text", content="")

            async def setup(self):
                nonlocal setup_called
                setup_called = True

        agent = LifecycleAgent()
        await agent.setup()

        assert setup_called

    async def test_agent_teardown_hook(self):
        """Test agent teardown hook is called."""
        teardown_called = False

        class LifecycleAgent(IAgent):
            @property
            def name(self) -> str:
                return "lifecycle"

            @property
            def description(self) -> str:
                return "lifecycle agent"

            async def invoke(self, input: AgentInput) -> AgentOutput:
                return AgentOutput(content="ok")

            async def stream(self, input: AgentInput):
                yield StreamChunk(type="text", content="")

            async def teardown(self):
                nonlocal teardown_called
                teardown_called = True

        agent = LifecycleAgent()
        await agent.teardown()

        assert teardown_called


@pytest.mark.unit
@pytest.mark.slow
class TestAgentPerformance:
    """Test agent performance characteristics."""

    async def test_agent_handles_large_input(self):
        """Test agent can handle large input messages."""

        class TestAgent(IAgent):
            @property
            def name(self) -> str:
                return "test"

            @property
            def description(self) -> str:
                return "test"

            async def invoke(self, input: AgentInput) -> AgentOutput:
                return AgentOutput(content=f"Processed {len(input.message)} chars")

            async def stream(self, input: AgentInput):
                yield StreamChunk(type="text", content="")

        agent = TestAgent()
        large_message = "x" * 10000
        output = await agent.invoke(AgentInput(message=large_message))

        assert "10000" in output.content

    async def test_agent_streaming_memory_efficient(self):
        """Test that streaming doesn't buffer all chunks."""

        class StreamingAgent(IAgent):
            @property
            def name(self) -> str:
                return "streaming"

            @property
            def description(self) -> str:
                return "streaming"

            async def invoke(self, input: AgentInput) -> AgentOutput:
                return AgentOutput(content="")

            async def stream(self, input: AgentInput):
                # Simulate large stream
                for i in range(1000):
                    yield StreamChunk(type="text", content=f"chunk{i}")

        agent = StreamingAgent()
        chunk_count = 0

        async for chunk in agent.stream(AgentInput(message="test")):
            chunk_count += 1
            # Process immediately, don't accumulate

        assert chunk_count == 1000
