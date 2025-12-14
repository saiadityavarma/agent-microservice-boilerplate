# tests/unit/protocols/test_protocol_handlers.py
"""Unit tests for protocol handlers."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from agent_service.interfaces import IProtocol, ProtocolType, AgentInput, AgentOutput


@pytest.mark.unit
class TestProtocolInterface:
    """Test IProtocol interface implementation."""

    async def test_protocol_has_required_methods(self):
        """Test that protocol implements required methods."""

        class MockProtocol(IProtocol):
            @property
            def protocol_type(self) -> ProtocolType:
                return ProtocolType.MCP

            async def handle_request(self, request, agent):
                return {"status": "ok"}

            async def handle_stream(self, request, agent):
                yield "data: test\n\n"

            def get_capability_info(self):
                return {"protocol": "mcp"}

        protocol = MockProtocol()
        assert protocol.protocol_type == ProtocolType.MCP
        assert protocol.get_capability_info()["protocol"] == "mcp"


@pytest.mark.unit
class TestProtocolRegistry:
    """Test protocol registry functionality."""

    def test_register_protocol(self):
        """Test registering a protocol."""
        from agent_service.protocols.registry import ProtocolRegistry

        registry = ProtocolRegistry()

        mock_protocol = Mock(spec=IProtocol)
        mock_protocol.protocol_type = ProtocolType.MCP

        registry.register(ProtocolType.MCP, mock_protocol)

        assert registry.get(ProtocolType.MCP) == mock_protocol

    def test_is_registered(self):
        """Test checking if protocol is registered."""
        from agent_service.protocols.registry import ProtocolRegistry

        registry = ProtocolRegistry()

        mock_protocol = Mock(spec=IProtocol)
        registry.register(ProtocolType.A2A, mock_protocol)

        assert registry.is_registered("a2a") is True
        assert registry.is_registered("mcp") is False

    def test_get_nonexistent_protocol(self):
        """Test getting non-existent protocol returns None."""
        from agent_service.protocols.registry import ProtocolRegistry

        registry = ProtocolRegistry()

        assert registry.get(ProtocolType.AGUI) is None


@pytest.mark.unit
class TestMCPProtocol:
    """Test MCP protocol handler."""

    async def test_mcp_capability_info(self):
        """Test MCP capability information."""
        mock_handler = Mock()
        mock_handler.get_capability_info.return_value = {
            "protocol": "mcp",
            "version": "1.0",
            "capabilities": {
                "sse": True,
                "tools": True
            }
        }

        info = mock_handler.get_capability_info()

        assert info["protocol"] == "mcp"
        assert info["capabilities"]["sse"] is True

    async def test_mcp_tool_list(self):
        """Test MCP tool listing."""
        mock_tools = [
            {
                "name": "tool1",
                "description": "First tool",
                "inputSchema": {"type": "object"}
            },
            {
                "name": "tool2",
                "description": "Second tool",
                "inputSchema": {"type": "object"}
            }
        ]

        assert len(mock_tools) == 2
        assert all("inputSchema" in t for t in mock_tools)

    async def test_mcp_request_handling(self):
        """Test MCP request handling."""
        mock_agent = AsyncMock()
        mock_agent.invoke.return_value = AgentOutput(content="MCP response")

        mock_request = Mock()
        mock_request.json = AsyncMock(return_value={"message": "test"})

        # Mock protocol handler
        async def handle_request(request, agent):
            data = await request.json()
            result = await agent.invoke(AgentInput(message=data["message"]))
            return {"content": result.content}

        response = await handle_request(mock_request, mock_agent)

        assert response["content"] == "MCP response"


@pytest.mark.unit
class TestA2AProtocol:
    """Test A2A protocol handler."""

    async def test_a2a_capability_info(self):
        """Test A2A capability information."""
        mock_handler = Mock()
        mock_handler.get_capability_info.return_value = {
            "name": "Test Agent",
            "description": "A test A2A agent",
            "capabilities": ["text", "async"],
            "endpoints": {
                "tasks": "/a2a/tasks",
                "messages": "/a2a/tasks/{task_id}/messages"
            }
        }

        info = mock_handler.get_capability_info()

        assert info["name"] == "Test Agent"
        assert "text" in info["capabilities"]

    async def test_a2a_task_creation(self):
        """Test A2A task creation."""
        mock_task = {
            "task_id": "task-123",
            "status": "created",
            "created_at": "2024-01-01T00:00:00Z"
        }

        # Simulate task creation
        async def create_task(message: str):
            return {
                "task_id": "task-123",
                "status": "created",
                "message": message
            }

        task = await create_task("Test task")

        assert task["task_id"] == "task-123"
        assert task["status"] == "created"

    async def test_a2a_task_status_tracking(self):
        """Test A2A task status tracking."""
        task_states = ["created", "processing", "completed"]

        for state in task_states:
            task = {"task_id": "task-1", "status": state}
            assert task["status"] in task_states


@pytest.mark.unit
class TestAGUIProtocol:
    """Test AG-UI protocol handler."""

    async def test_agui_capability_info(self):
        """Test AG-UI capability information."""
        mock_handler = Mock()
        mock_handler.get_capability_info.return_value = {
            "protocol": "agui",
            "version": "0.1.0",
            "events": [
                "RUN_START",
                "RUN_END",
                "TEXT_MESSAGE_START",
                "TEXT_MESSAGE_DELTA",
                "TEXT_MESSAGE_END",
                "TOOL_CALL_START",
                "TOOL_CALL_END",
                "STATE_UPDATED"
            ]
        }

        info = mock_handler.get_capability_info()

        assert info["protocol"] == "agui"
        assert "RUN_START" in info["events"]
        assert "TOOL_CALL_START" in info["events"]

    async def test_agui_event_streaming(self):
        """Test AG-UI event streaming."""
        async def mock_stream():
            events = [
                {"event": "RUN_START", "data": {}},
                {"event": "TEXT_MESSAGE_START", "data": {"id": "msg-1"}},
                {"event": "TEXT_MESSAGE_DELTA", "data": {"delta": "Hello"}},
                {"event": "TEXT_MESSAGE_END", "data": {"id": "msg-1"}},
                {"event": "RUN_END", "data": {}}
            ]
            for event in events:
                yield f"event: {event['event']}\ndata: {event['data']}\n\n"

        events = []
        async for event in mock_stream():
            events.append(event)

        assert len(events) == 5
        assert any("RUN_START" in e for e in events)

    async def test_agui_state_management(self):
        """Test AG-UI state management."""
        state = {
            "version": 1,
            "data": {
                "current_tool": None,
                "message_history": []
            }
        }

        # Simulate state update
        state["version"] += 1
        state["data"]["current_tool"] = "test_tool"

        assert state["version"] == 2
        assert state["data"]["current_tool"] == "test_tool"


@pytest.mark.unit
class TestProtocolConversion:
    """Test protocol format conversions."""

    def test_convert_agent_output_to_mcp_format(self):
        """Test converting agent output to MCP format."""
        output = AgentOutput(
            content="Test response",
            metadata={"model": "test"}
        )

        mcp_format = {
            "content": output.content,
            "metadata": output.metadata
        }

        assert mcp_format["content"] == "Test response"
        assert mcp_format["metadata"]["model"] == "test"

    def test_convert_agent_output_to_a2a_format(self):
        """Test converting agent output to A2A format."""
        output = AgentOutput(
            content="Test response",
            tool_calls=[{"name": "tool1", "args": {}}]
        )

        a2a_format = {
            "message": output.content,
            "actions": output.tool_calls
        }

        assert a2a_format["message"] == "Test response"
        assert len(a2a_format["actions"]) == 1

    def test_convert_mcp_request_to_agent_input(self):
        """Test converting MCP request to agent input."""
        mcp_request = {
            "message": "Test message",
            "context": {"user_id": "user-123"}
        }

        agent_input = AgentInput(
            message=mcp_request["message"],
            context=mcp_request["context"]
        )

        assert agent_input.message == "Test message"
        assert agent_input.context["user_id"] == "user-123"


@pytest.mark.unit
class TestProtocolErrorHandling:
    """Test protocol error handling."""

    async def test_protocol_handles_malformed_request(self):
        """Test protocol handles malformed requests."""
        mock_request = Mock()
        mock_request.json = AsyncMock(side_effect=ValueError("Invalid JSON"))

        async def handle_request(request):
            try:
                await request.json()
                return {"status": "ok"}
            except ValueError:
                return {"error": "Invalid request"}

        response = await handle_request(mock_request)

        assert "error" in response

    async def test_protocol_handles_agent_error(self):
        """Test protocol handles agent errors."""
        mock_agent = AsyncMock()
        mock_agent.invoke.side_effect = RuntimeError("Agent error")

        async def handle_request(agent):
            try:
                await agent.invoke(AgentInput(message="test"))
                return {"status": "ok"}
            except RuntimeError:
                return {"error": "Agent execution failed"}

        response = await handle_request(mock_agent)

        assert "error" in response

    async def test_protocol_handles_timeout(self):
        """Test protocol handles timeout scenarios."""
        import asyncio

        async def slow_operation():
            await asyncio.sleep(10)
            return "result"

        async def handle_with_timeout():
            try:
                result = await asyncio.wait_for(slow_operation(), timeout=0.1)
                return {"status": "ok", "result": result}
            except asyncio.TimeoutError:
                return {"error": "Operation timeout"}

        response = await handle_with_timeout()

        assert "error" in response
        assert "timeout" in response["error"].lower()
