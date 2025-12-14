"""
Tests for Simple Chatbot Agent
"""

import pytest
from agent_service.interfaces import AgentInput, AgentOutput, StreamChunk
from agent_service.agent import AgentContext, agent_registry
from agent_service.tools import tool_registry
from agent_service.infrastructure.cache.cache import get_cache


# Import agent to register it
from examples.chatbot.agent import simple_chatbot, simple_chatbot_sync


@pytest.fixture
async def agent_context():
    """Create a test agent context."""
    cache = await get_cache(namespace="test:chatbot")
    return AgentContext(
        tools=tool_registry,
        cache=cache,
        db=None,
        logger=None,
        user=None,
        request_id="test-request-123"
    )


@pytest.fixture
async def clear_cache():
    """Clear cache before and after tests."""
    cache = await get_cache(namespace="test:chatbot")
    # Clear before test
    yield
    # Clear after test (if needed)


class TestSimpleChatbot:
    """Test suite for simple chatbot agent."""

    @pytest.mark.asyncio
    async def test_chatbot_basic_response(self, agent_context):
        """Test that chatbot returns a response."""
        input = AgentInput(
            message="Hello",
            session_id="test_session_1"
        )

        chunks = []
        async for chunk in simple_chatbot(input, agent_context):
            if chunk.type == "text":
                chunks.append(chunk.content)

        response = "".join(chunks)
        assert len(response) > 0
        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_chatbot_hello_greeting(self, agent_context):
        """Test that chatbot responds appropriately to greetings."""
        input = AgentInput(
            message="Hello!",
            session_id="test_session_2"
        )

        chunks = []
        async for chunk in simple_chatbot(input, agent_context):
            if chunk.type == "text":
                chunks.append(chunk.content)

        response = "".join(chunks).lower()
        # Should respond with a greeting
        assert any(word in response for word in ["hello", "hi", "help"])

    @pytest.mark.asyncio
    async def test_chatbot_conversation_history(self, agent_context):
        """Test that chatbot maintains conversation history."""
        session_id = "test_session_3"

        # First message
        input1 = AgentInput(message="Hello", session_id=session_id)
        async for chunk in simple_chatbot(input1, agent_context):
            pass

        # Check that history was saved
        if agent_context.cache:
            history_key = f"history:{session_id}"
            history = await agent_context.cache.get(history_key)
            assert history is not None
            assert len(history) == 2  # User + Assistant
            assert history[0]["role"] == "user"
            assert history[1]["role"] == "assistant"

        # Second message
        input2 = AgentInput(message="How are you?", session_id=session_id)
        async for chunk in simple_chatbot(input2, agent_context):
            pass

        # Check that history was updated
        if agent_context.cache:
            history = await agent_context.cache.get(history_key)
            assert len(history) == 4  # 2 exchanges

    @pytest.mark.asyncio
    async def test_chatbot_separate_sessions(self, agent_context):
        """Test that different sessions maintain separate histories."""
        # Session 1
        input1 = AgentInput(message="Hello from session 1", session_id="session_1")
        async for chunk in simple_chatbot(input1, agent_context):
            pass

        # Session 2
        input2 = AgentInput(message="Hello from session 2", session_id="session_2")
        async for chunk in simple_chatbot(input2, agent_context):
            pass

        # Check separate histories
        if agent_context.cache:
            history1 = await agent_context.cache.get("history:session_1")
            history2 = await agent_context.cache.get("history:session_2")

            assert history1[0]["content"] == "Hello from session 1"
            assert history2[0]["content"] == "Hello from session 2"

    @pytest.mark.asyncio
    async def test_chatbot_streaming(self, agent_context):
        """Test that chatbot streams responses."""
        input = AgentInput(
            message="Hello",
            session_id="test_session_streaming"
        )

        chunk_count = 0
        async for chunk in simple_chatbot(input, agent_context):
            if chunk.type == "text":
                chunk_count += 1
                assert isinstance(chunk.content, str)
                assert isinstance(chunk, StreamChunk)

        # Should have received multiple chunks
        assert chunk_count > 0

    @pytest.mark.asyncio
    async def test_chatbot_sync_version(self, agent_context):
        """Test non-streaming version of chatbot."""
        input = AgentInput(
            message="Hello",
            session_id="test_session_sync"
        )

        result = await simple_chatbot_sync(input, agent_context)

        assert isinstance(result, AgentOutput)
        assert len(result.content) > 0
        assert result.metadata["session_id"] == "test_session_sync"
        assert "message_count" in result.metadata

    @pytest.mark.asyncio
    async def test_chatbot_error_handling(self, agent_context):
        """Test that chatbot handles errors gracefully."""
        # Create input with very long session ID to potentially cause issues
        input = AgentInput(
            message="Test",
            session_id="x" * 1000
        )

        # Should not raise exception
        chunks = []
        async for chunk in simple_chatbot(input, agent_context):
            chunks.append(chunk)

        # Should have some response (even if error)
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_chatbot_max_history_limit(self, agent_context):
        """Test that conversation history is limited to max size."""
        session_id = "test_session_history_limit"

        # Send 25 messages (more than the 20 limit)
        for i in range(25):
            input = AgentInput(
                message=f"Message {i}",
                session_id=session_id
            )
            async for chunk in simple_chatbot(input, agent_context):
                pass

        # Check that history is trimmed to 20 messages
        if agent_context.cache:
            history = await agent_context.cache.get(f"history:{session_id}")
            # Should have at most 40 messages (20 exchanges * 2 messages each)
            assert len(history) <= 40

    @pytest.mark.asyncio
    async def test_chatbot_registry_integration(self):
        """Test that chatbot is registered in agent registry."""
        # Check streaming agent
        chatbot = agent_registry.get("simple_chatbot")
        assert chatbot is not None
        assert chatbot.name == "simple_chatbot"

        # Check non-streaming agent
        chatbot_sync = agent_registry.get("simple_chatbot_sync")
        assert chatbot_sync is not None
        assert chatbot_sync.name == "simple_chatbot_sync"

    @pytest.mark.asyncio
    async def test_chatbot_empty_message(self, agent_context):
        """Test chatbot handling of empty message."""
        input = AgentInput(
            message="",
            session_id="test_empty"
        )

        chunks = []
        async for chunk in simple_chatbot(input, agent_context):
            if chunk.type == "text":
                chunks.append(chunk.content)

        # Should still return some response
        response = "".join(chunks)
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_chatbot_special_characters(self, agent_context):
        """Test chatbot handling of special characters."""
        input = AgentInput(
            message="Hello! @#$%^&* Testing special chars: <script>alert('test')</script>",
            session_id="test_special_chars"
        )

        chunks = []
        async for chunk in simple_chatbot(input, agent_context):
            if chunk.type == "text":
                chunks.append(chunk.content)

        response = "".join(chunks)
        assert len(response) > 0
        # Response should be generated without errors


class TestChatbotSimulation:
    """Test the simulation function specifically."""

    @pytest.mark.asyncio
    async def test_simulate_greeting_responses(self, agent_context):
        """Test that simulation provides appropriate greeting responses."""
        from examples.chatbot.agent import simulate_llm_response

        greetings = ["hello", "hi", "hey"]
        for greeting in greetings:
            response = await simulate_llm_response(
                system_prompt="You are helpful",
                conversation_history=[{"role": "user", "content": greeting}],
                ctx=agent_context
            )
            assert len(response) > 0

    @pytest.mark.asyncio
    async def test_simulate_goodbye_responses(self, agent_context):
        """Test goodbye responses."""
        from examples.chatbot.agent import simulate_llm_response

        response = await simulate_llm_response(
            system_prompt="You are helpful",
            conversation_history=[{"role": "user", "content": "goodbye"}],
            ctx=agent_context
        )
        assert "goodbye" in response.lower() or "bye" in response.lower()


class TestChatbotIntegration:
    """Integration tests for chatbot."""

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self, agent_context):
        """Test a complete conversation flow."""
        session_id = "test_full_conversation"

        # Message 1: Greeting
        input1 = AgentInput(message="Hello", session_id=session_id)
        response1_chunks = []
        async for chunk in simple_chatbot(input1, agent_context):
            if chunk.type == "text":
                response1_chunks.append(chunk.content)
        response1 = "".join(response1_chunks)
        assert len(response1) > 0

        # Message 2: Question
        input2 = AgentInput(message="What's your name?", session_id=session_id)
        response2_chunks = []
        async for chunk in simple_chatbot(input2, agent_context):
            if chunk.type == "text":
                response2_chunks.append(chunk.content)
        response2 = "".join(response2_chunks)
        assert len(response2) > 0

        # Message 3: Goodbye
        input3 = AgentInput(message="Goodbye", session_id=session_id)
        response3_chunks = []
        async for chunk in simple_chatbot(input3, agent_context):
            if chunk.type == "text":
                response3_chunks.append(chunk.content)
        response3 = "".join(response3_chunks)
        assert len(response3) > 0

        # Verify history
        if agent_context.cache:
            history = await agent_context.cache.get(f"history:{session_id}")
            assert len(history) == 6  # 3 exchanges


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
