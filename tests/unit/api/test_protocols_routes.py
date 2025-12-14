# tests/unit/api/test_protocols_routes.py
"""Unit tests for protocol API routes."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from httpx import AsyncClient

from agent_service.interfaces import ProtocolType


@pytest.mark.unit
class TestMCPRoutes:
    """Test MCP protocol routes."""

    async def test_mcp_info_endpoint(self, async_client: AsyncClient):
        """Test MCP info endpoint returns capability information."""
        mock_handler = Mock()
        mock_handler.get_capability_info.return_value = {
            "protocol": "mcp",
            "version": "1.0",
            "capabilities": ["sse", "tools"]
        }

        with patch("agent_service.api.routes.protocols.protocol_registry.get", return_value=mock_handler):
            response = await async_client.get("/api/v1/protocols/mcp/info")

        assert response.status_code == 200
        data = response.json()
        assert data["protocol"] == "mcp"
        assert "capabilities" in data

    async def test_mcp_info_when_disabled(self, async_client: AsyncClient):
        """Test MCP info returns 404 when MCP is disabled."""
        with patch("agent_service.api.routes.protocols.protocol_registry.get", return_value=None):
            response = await async_client.get("/api/v1/protocols/mcp/info")

        assert response.status_code == 404
        assert "MCP not enabled" in response.json()["error"]

    async def test_list_mcp_tools(self, async_client: AsyncClient):
        """Test listing MCP tools."""
        with patch("agent_service.api.routes.protocols.protocol_registry.is_registered", return_value=True):
            mock_tool_schema = Mock()
            mock_tool_schema.name = "test_tool"
            mock_tool_schema.description = "A test tool"
            mock_tool_schema.parameters = {"type": "object"}

            with patch("agent_service.api.routes.protocols.tool_registry.list_tools", return_value=[mock_tool_schema]):
                response = await async_client.get("/api/v1/protocols/mcp/tools")

        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert len(data["tools"]) == 1
        assert data["tools"][0]["name"] == "test_tool"

    async def test_mcp_direct_tool_invocation(self, async_client: AsyncClient):
        """Test direct tool invocation via MCP."""
        with patch("agent_service.api.routes.protocols.protocol_registry.is_registered", return_value=True):
            mock_result = {"status": "success", "output": "tool result"}
            with patch("agent_service.api.routes.protocols.tool_registry.execute", return_value=mock_result):
                response = await async_client.post(
                    "/api/v1/protocols/mcp/tools/test_tool",
                    json={"arguments": {"param": "value"}}
                )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["tool"] == "test_tool"
        assert data["result"] == mock_result

    async def test_mcp_tool_not_found(self, async_client: AsyncClient):
        """Test MCP tool invocation with non-existent tool."""
        with patch("agent_service.api.routes.protocols.protocol_registry.is_registered", return_value=True):
            with patch("agent_service.api.routes.protocols.tool_registry.execute", side_effect=ValueError("Tool not found")):
                response = await async_client.post(
                    "/api/v1/protocols/mcp/tools/nonexistent",
                    json={"arguments": {}}
                )

        assert response.status_code == 404

    async def test_mcp_sse_endpoint(self, async_client: AsyncClient):
        """Test MCP SSE streaming endpoint."""
        async def mock_stream(request, agent):
            yield "data: test\n\n"

        mock_handler = Mock()
        mock_handler.handle_stream = mock_stream

        with patch("agent_service.api.routes.protocols.protocol_registry.get", return_value=mock_handler):
            with patch("agent_service.api.routes.protocols.get_default_agent"):
                response = await async_client.get("/api/v1/protocols/mcp")

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]


@pytest.mark.unit
class TestA2ARoutes:
    """Test A2A protocol routes."""

    async def test_agent_card_endpoint(self, async_client: AsyncClient):
        """Test A2A agent card endpoint."""
        mock_handler = Mock()
        mock_handler.get_capability_info.return_value = {
            "name": "Test Agent",
            "description": "A test agent",
            "capabilities": ["text", "async"]
        }

        with patch("agent_service.api.routes.protocols.protocol_registry.get", return_value=mock_handler):
            response = await async_client.get("/api/v1/protocols/.well-known/agent.json")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Agent"

    async def test_create_a2a_task(self, async_client: AsyncClient):
        """Test creating A2A task."""
        mock_handler = AsyncMock()
        mock_handler.handle_request.return_value = {
            "task_id": "task-123",
            "status": "created"
        }

        with patch("agent_service.api.routes.protocols.protocol_registry.get", return_value=mock_handler):
            with patch("agent_service.api.routes.protocols.get_default_agent"):
                response = await async_client.post(
                    "/api/v1/protocols/a2a/tasks",
                    json={"message": "Test task"}
                )

        assert response.status_code == 200
        assert "task_id" in response.json()

    async def test_get_a2a_task(self, async_client: AsyncClient):
        """Test getting A2A task by ID."""
        mock_task = {
            "task_id": "task-456",
            "status": "completed",
            "result": "Task result"
        }

        with patch("agent_service.api.routes.protocols.protocol_registry.is_registered", return_value=True):
            mock_manager = AsyncMock()
            mock_manager.get_task.return_value = mock_task

            with patch("agent_service.api.routes.protocols.get_task_manager", return_value=mock_manager):
                response = await async_client.get("/api/v1/protocols/a2a/tasks/task-456")

        assert response.status_code == 200
        assert response.json()["task_id"] == "task-456"

    async def test_get_a2a_task_not_found(self, async_client: AsyncClient):
        """Test getting non-existent A2A task."""
        with patch("agent_service.api.routes.protocols.protocol_registry.is_registered", return_value=True):
            mock_manager = AsyncMock()
            mock_manager.get_task.return_value = None

            with patch("agent_service.api.routes.protocols.get_task_manager", return_value=mock_manager):
                response = await async_client.get("/api/v1/protocols/a2a/tasks/nonexistent")

        assert response.status_code == 404

    async def test_list_a2a_tasks(self, async_client: AsyncClient):
        """Test listing A2A tasks with filters."""
        mock_tasks = [
            {"task_id": "task-1", "status": "completed"},
            {"task_id": "task-2", "status": "pending"}
        ]

        with patch("agent_service.api.routes.protocols.protocol_registry.is_registered", return_value=True):
            mock_manager = AsyncMock()
            mock_manager.list_tasks.return_value = mock_tasks

            with patch("agent_service.api.routes.protocols.get_task_manager", return_value=mock_manager):
                response = await async_client.get(
                    "/api/v1/protocols/a2a/tasks?limit=10&offset=0"
                )

        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 2
        assert data["total"] == 2

    async def test_add_a2a_message(self, async_client: AsyncClient):
        """Test adding message to A2A task."""
        mock_handler = AsyncMock()
        mock_handler.handle_request.return_value = {
            "task_id": "task-789",
            "message_added": True
        }

        with patch("agent_service.api.routes.protocols.protocol_registry.get", return_value=mock_handler):
            with patch("agent_service.api.routes.protocols.get_default_agent"):
                response = await async_client.post(
                    "/api/v1/protocols/a2a/tasks/task-789/messages",
                    json={"content": "Additional message"}
                )

        assert response.status_code == 200

    async def test_a2a_stream(self, async_client: AsyncClient):
        """Test A2A streaming endpoint."""
        async def mock_stream(request, agent):
            yield "data: event1\n\n"

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


@pytest.mark.unit
class TestAGUIRoutes:
    """Test AG-UI protocol routes."""

    async def test_agui_capabilities(self, async_client: AsyncClient):
        """Test AG-UI capabilities endpoint."""
        mock_handler = Mock()
        mock_handler.get_capability_info.return_value = {
            "protocol": "agui",
            "events": ["RUN_START", "TEXT_MESSAGE", "TOOL_CALL"]
        }

        with patch("agent_service.api.routes.protocols.protocol_registry.get", return_value=mock_handler):
            response = await async_client.get("/api/v1/protocols/agui/capabilities")

        assert response.status_code == 200
        assert "events" in response.json()

    async def test_agui_stream(self, async_client: AsyncClient):
        """Test AG-UI streaming endpoint."""
        async def mock_stream(request, agent):
            yield "event: RUN_START\ndata: {}\n\n"

        mock_handler = Mock()
        mock_handler.handle_stream = mock_stream

        with patch("agent_service.api.routes.protocols.protocol_registry.get", return_value=mock_handler):
            with patch("agent_service.api.routes.protocols.get_default_agent"):
                response = await async_client.post(
                    "/api/v1/protocols/agui/stream",
                    json={"message": "Test"}
                )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    async def test_agui_state(self, async_client: AsyncClient):
        """Test AG-UI state endpoint."""
        mock_state = {
            "version": 1,
            "data": {"key": "value"}
        }

        with patch("agent_service.api.routes.protocols.protocol_registry.is_registered", return_value=True):
            mock_manager = Mock()
            mock_manager.get_state.return_value = mock_state["data"]
            mock_manager.get_version.return_value = mock_state["version"]

            with patch("agent_service.api.routes.protocols.get_state_manager", return_value=mock_manager):
                response = await async_client.get("/api/v1/protocols/agui/state")

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == 1


@pytest.mark.unit
class TestGenericProtocolRoutes:
    """Test generic protocol endpoints."""

    async def test_protocol_invoke_with_valid_protocol(self, async_client: AsyncClient):
        """Test generic protocol invoke endpoint."""
        mock_handler = AsyncMock()
        mock_handler.handle_request.return_value = {"result": "success"}

        with patch("agent_service.api.routes.protocols.protocol_registry.get", return_value=mock_handler):
            with patch("agent_service.api.routes.protocols.get_default_agent"):
                response = await async_client.post(
                    "/api/v1/protocols/mcp/invoke",
                    json={"message": "test"}
                )

        assert response.status_code == 200

    async def test_protocol_invoke_with_invalid_protocol(self, async_client: AsyncClient):
        """Test protocol invoke with disabled protocol."""
        with patch("agent_service.api.routes.protocols.protocol_registry.get", return_value=None):
            response = await async_client.post(
                "/api/v1/protocols/invalid/invoke",
                json={"message": "test"}
            )

        assert response.status_code == 404

    async def test_protocol_stream_with_valid_protocol(self, async_client: AsyncClient):
        """Test generic protocol stream endpoint."""
        async def mock_stream(request, agent):
            yield "data: test\n\n"

        mock_handler = Mock()
        mock_handler.handle_stream = mock_stream

        with patch("agent_service.api.routes.protocols.protocol_registry.get", return_value=mock_handler):
            with patch("agent_service.api.routes.protocols.get_default_agent"):
                response = await async_client.post(
                    "/api/v1/protocols/mcp/stream",
                    json={"message": "test"}
                )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
