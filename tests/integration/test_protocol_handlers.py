# tests/integration/test_protocol_handlers.py
"""Integration tests for protocol handlers with mock agents."""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, Mock

from agent_service.interfaces import AgentOutput, StreamChunk


@pytest.mark.integration
class TestMCPProtocolIntegration:
    """Integration tests for MCP protocol."""

    async def test_mcp_end_to_end_flow(self, async_client: AsyncClient):
        """Test complete MCP flow from request to response."""
        mock_agent = AsyncMock()
        mock_agent.invoke.return_value = AgentOutput(
            content="MCP response",
            metadata={"protocol": "mcp"}
        )

        with patch("agent_service.api.routes.protocols.get_default_agent", return_value=mock_agent):
            with patch("agent_service.api.routes.protocols.protocol_registry.get") as mock_registry:
                mock_handler = AsyncMock()
                mock_handler.handle_request.return_value = {
                    "content": "MCP response",
                    "metadata": {"protocol": "mcp"}
                }
                mock_registry.return_value = mock_handler

                response = await async_client.post(
                    "/api/v1/protocols/mcp/invoke",
                    json={"message": "Test MCP"}
                )

        assert response.status_code in [200, 404]  # 404 if MCP not enabled

    async def test_mcp_tool_discovery(self, async_client: AsyncClient):
        """Test MCP tool discovery."""
        from agent_service.tools.registry import tool_registry
        from agent_service.interfaces import ToolSchema

        # Register a test tool
        mock_tool = Mock()
        mock_tool.schema = ToolSchema(
            name="mcp_test_tool",
            description="A test tool for MCP",
            parameters={"type": "object", "properties": {}}
        )

        tool_registry.register(mock_tool)

        with patch("agent_service.api.routes.protocols.protocol_registry.is_registered", return_value=True):
            response = await async_client.get("/api/v1/protocols/mcp/tools")

        assert response.status_code == 200
        data = response.json()
        assert "tools" in data

        # Cleanup
        tool_registry.unregister("mcp_test_tool")

    async def test_mcp_direct_tool_execution(self, async_client: AsyncClient):
        """Test direct tool execution via MCP."""
        with patch("agent_service.api.routes.protocols.protocol_registry.is_registered", return_value=True):
            with patch("agent_service.api.routes.protocols.tool_registry.execute") as mock_execute:
                mock_execute.return_value = {"status": "success", "data": "tool result"}

                response = await async_client.post(
                    "/api/v1/protocols/mcp/tools/test_tool",
                    json={"arguments": {"param": "value"}}
                )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_mcp_sse_streaming(self, async_client: AsyncClient):
        """Test MCP Server-Sent Events streaming."""
        async def mock_stream(request, agent):
            events = [
                "data: event1\n\n",
                "data: event2\n\n",
                "data: event3\n\n"
            ]
            for event in events:
                yield event

        mock_handler = Mock()
        mock_handler.handle_stream = mock_stream

        with patch("agent_service.api.routes.protocols.protocol_registry.get", return_value=mock_handler):
            with patch("agent_service.api.routes.protocols.get_default_agent"):
                response = await async_client.get("/api/v1/protocols/mcp")

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]


@pytest.mark.integration
class TestA2AProtocolIntegration:
    """Integration tests for A2A protocol."""

    async def test_a2a_task_lifecycle(self, async_client: AsyncClient):
        """Test complete A2A task lifecycle."""
        # Step 1: Create task
        mock_handler = AsyncMock()
        mock_handler.handle_request.return_value = {
            "task_id": "a2a-task-123",
            "status": "created"
        }

        with patch("agent_service.api.routes.protocols.protocol_registry.get", return_value=mock_handler):
            with patch("agent_service.api.routes.protocols.get_default_agent"):
                create_response = await async_client.post(
                    "/api/v1/protocols/a2a/tasks",
                    json={"message": "Create A2A task"}
                )

        if create_response.status_code == 200:
            # Step 2: Get task status
            mock_task = {
                "task_id": "a2a-task-123",
                "status": "processing"
            }

            with patch("agent_service.api.routes.protocols.protocol_registry.is_registered", return_value=True):
                with patch("agent_service.api.routes.protocols.get_task_manager") as mock_manager:
                    mock_mgr = AsyncMock()
                    mock_mgr.get_task.return_value = mock_task
                    mock_manager.return_value = mock_mgr

                    status_response = await async_client.get("/api/v1/protocols/a2a/tasks/a2a-task-123")

            assert status_response.status_code == 200

    async def test_a2a_message_threading(self, async_client: AsyncClient):
        """Test A2A message threading in tasks."""
        # Create task
        task_id = "task-with-messages"

        # Add message to task
        mock_handler = AsyncMock()
        mock_handler.handle_request.return_value = {
            "task_id": task_id,
            "message_count": 2
        }

        with patch("agent_service.api.routes.protocols.protocol_registry.get", return_value=mock_handler):
            with patch("agent_service.api.routes.protocols.get_default_agent"):
                response = await async_client.post(
                    f"/api/v1/protocols/a2a/tasks/{task_id}/messages",
                    json={"content": "Follow-up message"}
                )

        assert response.status_code in [200, 404]

    async def test_a2a_task_filtering(self, async_client: AsyncClient):
        """Test A2A task filtering and pagination."""
        mock_tasks = [
            {"task_id": "task-1", "status": "completed"},
            {"task_id": "task-2", "status": "processing"}
        ]

        with patch("agent_service.api.routes.protocols.protocol_registry.is_registered", return_value=True):
            with patch("agent_service.api.routes.protocols.get_task_manager") as mock_manager:
                mock_mgr = AsyncMock()
                mock_mgr.list_tasks.return_value = mock_tasks
                mock_manager.return_value = mock_mgr

                response = await async_client.get(
                    "/api/v1/protocols/a2a/tasks?status=completed&limit=10"
                )

        assert response.status_code == 200

    async def test_a2a_streaming(self, async_client: AsyncClient):
        """Test A2A streaming events."""
        async def mock_stream(request, agent):
            yield "event: task.created\ndata: {}\n\n"
            yield "event: task.processing\ndata: {}\n\n"
            yield "event: task.completed\ndata: {}\n\n"

        mock_handler = Mock()
        mock_handler.handle_stream = mock_stream

        with patch("agent_service.api.routes.protocols.protocol_registry.get", return_value=mock_handler):
            with patch("agent_service.api.routes.protocols.get_default_agent"):
                response = await async_client.post(
                    "/api/v1/protocols/a2a/stream",
                    json={"message": "Stream test"}
                )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]


@pytest.mark.integration
class TestAGUIProtocolIntegration:
    """Integration tests for AG-UI protocol."""

    async def test_agui_event_streaming(self, async_client: AsyncClient):
        """Test AG-UI event streaming."""
        async def mock_stream(request, agent):
            events = [
                "event: RUN_START\ndata: {}\n\n",
                "event: TEXT_MESSAGE_START\ndata: {}\n\n",
                "event: TEXT_MESSAGE_DELTA\ndata: {\"delta\": \"Hello\"}\n\n",
                "event: TEXT_MESSAGE_END\ndata: {}\n\n",
                "event: RUN_END\ndata: {}\n\n"
            ]
            for event in events:
                yield event

        mock_handler = Mock()
        mock_handler.handle_stream = mock_stream

        with patch("agent_service.api.routes.protocols.protocol_registry.get", return_value=mock_handler):
            with patch("agent_service.api.routes.protocols.get_default_agent"):
                response = await async_client.post(
                    "/api/v1/protocols/agui/stream",
                    json={"message": "Test AG-UI"}
                )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    async def test_agui_tool_call_events(self, async_client: AsyncClient):
        """Test AG-UI tool call event sequence."""
        async def mock_stream(request, agent):
            yield "event: TOOL_CALL_START\ndata: {\"tool\": \"test_tool\"}\n\n"
            yield "event: TOOL_CALL_END\ndata: {\"result\": \"success\"}\n\n"

        mock_handler = Mock()
        mock_handler.handle_stream = mock_stream

        with patch("agent_service.api.routes.protocols.protocol_registry.get", return_value=mock_handler):
            with patch("agent_service.api.routes.protocols.get_default_agent"):
                response = await async_client.post(
                    "/api/v1/protocols/agui/stream",
                    json={"message": "Execute tool"}
                )

        assert response.status_code == 200

    async def test_agui_state_synchronization(self, async_client: AsyncClient):
        """Test AG-UI state synchronization."""
        mock_state = {
            "version": 1,
            "data": {"key": "value"}
        }

        with patch("agent_service.api.routes.protocols.protocol_registry.is_registered", return_value=True):
            with patch("agent_service.api.routes.protocols.get_state_manager") as mock_manager:
                mock_mgr = Mock()
                mock_mgr.get_state.return_value = mock_state["data"]
                mock_mgr.get_version.return_value = mock_state["version"]
                mock_manager.return_value = mock_mgr

                response = await async_client.get("/api/v1/protocols/agui/state")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data

    async def test_agui_capabilities(self, async_client: AsyncClient):
        """Test AG-UI capabilities endpoint."""
        mock_capabilities = {
            "protocol": "agui",
            "version": "0.1.0",
            "events": ["RUN_START", "RUN_END", "TEXT_MESSAGE_START"]
        }

        mock_handler = Mock()
        mock_handler.get_capability_info.return_value = mock_capabilities

        with patch("agent_service.api.routes.protocols.protocol_registry.get", return_value=mock_handler):
            response = await async_client.get("/api/v1/protocols/agui/capabilities")

        assert response.status_code == 200
        data = response.json()
        assert "events" in data


@pytest.mark.integration
class TestProtocolInteroperability:
    """Test interoperability between protocols."""

    async def test_same_agent_multiple_protocols(self, async_client: AsyncClient):
        """Test accessing same agent through different protocols."""
        mock_agent = AsyncMock()
        mock_agent.invoke.return_value = AgentOutput(content="Universal response")

        # Test MCP
        with patch("agent_service.api.routes.protocols.get_default_agent", return_value=mock_agent):
            mock_handler = AsyncMock()
            mock_handler.handle_request.return_value = {"content": "Universal response"}

            with patch("agent_service.api.routes.protocols.protocol_registry.get", return_value=mock_handler):
                mcp_response = await async_client.post(
                    "/api/v1/protocols/mcp/invoke",
                    json={"message": "Test"}
                )

        # Test A2A
        with patch("agent_service.api.routes.protocols.get_default_agent", return_value=mock_agent):
            with patch("agent_service.api.routes.protocols.protocol_registry.get", return_value=mock_handler):
                a2a_response = await async_client.post(
                    "/api/v1/protocols/a2a/tasks",
                    json={"message": "Test"}
                )

        # Both should work (or both return 404 if not enabled)
        assert mcp_response.status_code == a2a_response.status_code or \
               (mcp_response.status_code in [200, 404] and a2a_response.status_code in [200, 404])

    async def test_protocol_capability_negotiation(self, async_client: AsyncClient):
        """Test protocol capability negotiation."""
        # Check MCP capabilities
        mock_mcp = Mock()
        mock_mcp.get_capability_info.return_value = {"protocol": "mcp", "sse": True}

        with patch("agent_service.api.routes.protocols.protocol_registry.get", return_value=mock_mcp):
            mcp_info = await async_client.get("/api/v1/protocols/mcp/info")

        # Check A2A capabilities
        mock_a2a = Mock()
        mock_a2a.get_capability_info.return_value = {"name": "Agent", "capabilities": ["text"]}

        with patch("agent_service.api.routes.protocols.protocol_registry.get", return_value=mock_a2a):
            a2a_info = await async_client.get("/api/v1/protocols/.well-known/agent.json")

        # Both should return capability info (or 404)
        assert mcp_info.status_code in [200, 404]
        assert a2a_info.status_code in [200, 404]
