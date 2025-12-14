# tests/unit/api/test_agents_routes.py
"""Unit tests for agent API routes."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from httpx import AsyncClient
from fastapi import FastAPI

from agent_service.interfaces import AgentInput, AgentOutput, StreamChunk


@pytest.mark.unit
class TestAgentInvokeRoute:
    """Test /agents/invoke endpoint."""

    async def test_invoke_agent_success(self, async_client: AsyncClient, app: FastAPI):
        """Test successful agent invocation."""
        mock_agent = AsyncMock()
        mock_agent.invoke.return_value = AgentOutput(
            content="Test response",
            metadata={"tokens": 10}
        )

        with patch("agent_service.api.routes.agents.CurrentAgent", return_value=mock_agent):
            response = await async_client.post(
                "/api/v1/agents/invoke",
                json={"message": "Test message"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Test response"
        assert data["metadata"]["tokens"] == 10

    async def test_invoke_agent_with_session_id(self, async_client: AsyncClient):
        """Test agent invocation with session ID."""
        mock_agent = AsyncMock()
        mock_agent.invoke.return_value = AgentOutput(content="Response with session")

        with patch("agent_service.api.routes.agents.CurrentAgent", return_value=mock_agent):
            response = await async_client.post(
                "/api/v1/agents/invoke",
                json={
                    "message": "Test message",
                    "session_id": "session_123"
                }
            )

        assert response.status_code == 200
        mock_agent.invoke.assert_called_once()
        call_args = mock_agent.invoke.call_args[0][0]
        assert isinstance(call_args, AgentInput)
        assert call_args.message == "Test message"

    async def test_invoke_agent_with_metadata(self, async_client: AsyncClient):
        """Test agent invocation with custom metadata."""
        mock_agent = AsyncMock()
        mock_agent.invoke.return_value = AgentOutput(content="Response")

        with patch("agent_service.api.routes.agents.CurrentAgent", return_value=mock_agent):
            response = await async_client.post(
                "/api/v1/agents/invoke",
                json={
                    "message": "Test",
                    "metadata": {"source": "test_suite"}
                }
            )

        assert response.status_code == 200

    async def test_invoke_agent_empty_message(self, async_client: AsyncClient):
        """Test that empty messages are rejected."""
        response = await async_client.post(
            "/api/v1/agents/invoke",
            json={"message": ""}
        )

        assert response.status_code == 422  # Validation error

    async def test_invoke_agent_too_long_message(self, async_client: AsyncClient):
        """Test that overly long messages are rejected."""
        response = await async_client.post(
            "/api/v1/agents/invoke",
            json={"message": "x" * 10001}  # Exceeds max_length=10000
        )

        assert response.status_code == 422  # Validation error


@pytest.mark.unit
class TestAgentStreamRoute:
    """Test /agents/stream endpoint."""

    async def test_stream_agent_success(self, async_client: AsyncClient):
        """Test successful streaming invocation."""
        async def mock_stream(input_data):
            chunks = ["Hello", " ", "world", "!"]
            for chunk in chunks:
                yield StreamChunk(type="text", content=chunk)

        mock_agent = AsyncMock()
        mock_agent.stream = mock_stream

        with patch("agent_service.api.routes.agents.CurrentAgent", return_value=mock_agent):
            response = await async_client.post(
                "/api/v1/agents/stream",
                json={"message": "Test streaming"}
            )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    async def test_stream_agent_receives_correct_input(self, async_client: AsyncClient):
        """Test that streaming receives correct input."""
        received_input = None

        async def mock_stream(input_data):
            nonlocal received_input
            received_input = input_data
            yield StreamChunk(type="text", content="test")

        mock_agent = AsyncMock()
        mock_agent.stream = mock_stream

        with patch("agent_service.api.routes.agents.CurrentAgent", return_value=mock_agent):
            await async_client.post(
                "/api/v1/agents/stream",
                json={
                    "message": "Stream test",
                    "session_id": "session_456"
                }
            )

        assert received_input is not None
        assert isinstance(received_input, AgentInput)
        assert received_input.message == "Stream test"


@pytest.mark.unit
class TestAsyncInvokeRoute:
    """Test /agents/{agent_id}/invoke-async endpoint."""

    async def test_async_invoke_queues_task(self, async_client: AsyncClient):
        """Test that async invoke queues a Celery task."""
        mock_task = Mock()
        mock_task.id = "task-123-456"

        mock_user = Mock()
        mock_user.id = "user-789"

        with patch("agent_service.api.routes.agents.invoke_agent_async.delay", return_value=mock_task):
            with patch("agent_service.api.routes.agents.get_current_user_any", return_value=mock_user):
                response = await async_client.post(
                    "/api/v1/agents/agent-1/invoke-async",
                    json={"message": "Long running task"}
                )

        assert response.status_code == 202
        data = response.json()
        assert data["task_id"] == "task-123-456"
        assert data["status"] == "queued"
        assert "status_url" in data

    async def test_async_invoke_includes_user_context(self, async_client: AsyncClient):
        """Test that async invoke includes user context."""
        mock_task = Mock()
        mock_task.id = "task-abc"

        mock_user = Mock()
        mock_user.id = "user-xyz"

        with patch("agent_service.api.routes.agents.invoke_agent_async.delay") as mock_delay:
            mock_delay.return_value = mock_task
            with patch("agent_service.api.routes.agents.get_current_user_any", return_value=mock_user):
                await async_client.post(
                    "/api/v1/agents/agent-1/invoke-async",
                    json={
                        "message": "Test",
                        "session_id": "sess-1",
                        "metadata": {"key": "value"}
                    }
                )

            mock_delay.assert_called_once()
            call_kwargs = mock_delay.call_args[1]
            assert call_kwargs["agent_id"] == "agent-1"
            assert call_kwargs["message"] == "Test"
            assert call_kwargs["user_id"] == "user-xyz"
            assert call_kwargs["session_id"] == "sess-1"
            assert call_kwargs["metadata"] == {"key": "value"}


@pytest.mark.unit
class TestTaskStatusRoute:
    """Test /agents/tasks/{task_id} endpoint."""

    async def test_get_task_status_pending(self, async_client: AsyncClient):
        """Test getting status of pending task."""
        mock_task_info = {
            "state": "PENDING",
            "successful": False,
            "failed": False,
            "result": None
        }

        with patch("agent_service.api.routes.agents.get_task_info", return_value=mock_task_info):
            response = await async_client.get("/api/v1/agents/tasks/task-123")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task-123"
        assert data["state"] == "PENDING"
        assert data["status"] == "queued"

    async def test_get_task_status_success(self, async_client: AsyncClient):
        """Test getting status of completed task."""
        mock_task_info = {
            "state": "SUCCESS",
            "successful": True,
            "failed": False,
            "result": {
                "content": "Task result",
                "metadata": {"duration": 5.2}
            }
        }

        with patch("agent_service.api.routes.agents.get_task_info", return_value=mock_task_info):
            response = await async_client.get("/api/v1/agents/tasks/task-456")

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "SUCCESS"
        assert data["status"] == "completed"
        assert data["result"]["content"] == "Task result"

    async def test_get_task_status_failure(self, async_client: AsyncClient):
        """Test getting status of failed task."""
        mock_task_info = {
            "state": "FAILURE",
            "successful": False,
            "failed": True,
            "result": "Task execution error"
        }

        with patch("agent_service.api.routes.agents.get_task_info", return_value=mock_task_info):
            response = await async_client.get("/api/v1/agents/tasks/task-789")

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "FAILURE"
        assert data["status"] == "failed"
        assert "error" in data

    async def test_get_task_status_with_progress(self, async_client: AsyncClient):
        """Test task status with progress information."""
        mock_task_info = {
            "state": "STARTED",
            "successful": False,
            "failed": False,
            "info": {"progress": 45}
        }

        with patch("agent_service.api.routes.agents.get_task_info", return_value=mock_task_info):
            response = await async_client.get("/api/v1/agents/tasks/task-progress")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["progress"] == 45


@pytest.mark.unit
@pytest.mark.smoke
class TestAgentRoutesIntegration:
    """Smoke tests for agent routes."""

    async def test_all_agent_routes_exist(self, async_client: AsyncClient):
        """Test that all expected agent routes are registered."""
        # This is a smoke test to ensure routes are properly mounted
        routes = [
            ("/api/v1/agents/invoke", "POST"),
            ("/api/v1/agents/stream", "POST"),
            ("/api/v1/agents/test-agent/invoke-async", "POST"),
            ("/api/v1/agents/tasks/task-123", "GET"),
        ]

        for path, method in routes:
            # We expect 401/422/500, not 404 (route exists)
            if method == "POST":
                response = await async_client.post(path, json={})
            else:
                response = await async_client.get(path)

            # Route should exist (not 404)
            assert response.status_code != 404, f"Route {method} {path} not found"
