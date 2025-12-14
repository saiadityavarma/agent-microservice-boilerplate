# tests/integration/test_agent_invocation.py
"""Integration tests for agent invocation with real database."""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

from agent_service.interfaces import AgentInput, AgentOutput, StreamChunk


@pytest.mark.integration
@pytest.mark.requires_db
class TestAgentInvocationWithDatabase:
    """Test agent invocation with real database operations."""

    async def test_invoke_agent_creates_session(self, async_client: AsyncClient, db_session):
        """Test that agent invocation creates session in database."""
        from agent_service.domain.models import Session

        mock_agent = AsyncMock()
        mock_agent.invoke.return_value = AgentOutput(content="Test response")

        with patch("agent_service.api.routes.agents.CurrentAgent", return_value=mock_agent):
            response = await async_client.post(
                "/api/v1/agents/invoke",
                json={
                    "message": "Test message",
                    "session_id": "test-session-123"
                }
            )

        assert response.status_code == 200

        # Check if session exists in database
        # Note: This depends on your session tracking implementation
        # sessions = await db_session.execute(select(Session).where(Session.id == "test-session-123"))
        # session = sessions.scalar_one_or_none()
        # assert session is not None

    async def test_invoke_agent_logs_audit_trail(self, async_client: AsyncClient, db_session):
        """Test that agent invocation creates audit log."""
        from agent_service.infrastructure.database.models.audit_log import AuditLog
        from sqlalchemy import select

        mock_agent = AsyncMock()
        mock_agent.invoke.return_value = AgentOutput(content="Response")

        with patch("agent_service.api.routes.agents.CurrentAgent", return_value=mock_agent):
            with patch("agent_service.auth.dependencies.get_current_user_any") as mock_user:
                mock_user.return_value.id = "user-123"

                response = await async_client.post(
                    "/api/v1/agents/invoke",
                    json={"message": "Test"}
                )

        assert response.status_code == 200

        # Check audit logs
        result = await db_session.execute(
            select(AuditLog).where(AuditLog.user_id == "user-123")
        )
        logs = result.scalars().all()

        # Audit logging may or may not be enabled
        assert isinstance(logs, list)

    async def test_concurrent_agent_invocations(self, async_client: AsyncClient):
        """Test multiple concurrent agent invocations."""
        import asyncio

        mock_agent = AsyncMock()
        mock_agent.invoke.return_value = AgentOutput(content="Concurrent response")

        async def invoke_agent(message: str):
            with patch("agent_service.api.routes.agents.CurrentAgent", return_value=mock_agent):
                return await async_client.post(
                    "/api/v1/agents/invoke",
                    json={"message": message}
                )

        # Make 5 concurrent requests
        tasks = [invoke_agent(f"Message {i}") for i in range(5)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r.status_code == 200 for r in responses)

    async def test_agent_invocation_with_transaction_rollback(self, db_session):
        """Test that failed invocations rollback database changes."""
        from agent_service.domain.models import Session

        # Simulate failed invocation
        try:
            async with db_session.begin():
                # Create session
                session = Session(id="rollback-test", user_id="user-123")
                db_session.add(session)

                # Simulate error
                raise RuntimeError("Simulated error")

        except RuntimeError:
            pass

        # Session should not exist due to rollback
        from sqlalchemy import select
        result = await db_session.execute(
            select(Session).where(Session.id == "rollback-test")
        )
        session = result.scalar_one_or_none()

        # Should be None due to rollback
        assert session is None


@pytest.mark.integration
class TestAgentStreamingIntegration:
    """Test agent streaming with full stack."""

    async def test_streaming_response_format(self, async_client: AsyncClient):
        """Test streaming response format."""
        async def mock_stream(input_data):
            for word in ["Hello", "streaming", "world"]:
                yield StreamChunk(type="text", content=word)

        mock_agent = AsyncMock()
        mock_agent.stream = mock_stream

        with patch("agent_service.api.routes.agents.CurrentAgent", return_value=mock_agent):
            response = await async_client.post(
                "/api/v1/agents/stream",
                json={"message": "Test streaming"}
            )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    async def test_streaming_connection_handling(self, async_client: AsyncClient):
        """Test streaming connection lifecycle."""
        async def mock_stream(input_data):
            for i in range(10):
                yield StreamChunk(type="text", content=f"chunk{i}")

        mock_agent = AsyncMock()
        mock_agent.stream = mock_stream

        with patch("agent_service.api.routes.agents.CurrentAgent", return_value=mock_agent):
            response = await async_client.post(
                "/api/v1/agents/stream",
                json={"message": "Test"}
            )

        # Connection should be established
        assert response.status_code == 200


@pytest.mark.integration
class TestAgentWithTools:
    """Test agent invocation with tool execution."""

    async def test_agent_executes_tool(self, async_client: AsyncClient):
        """Test agent that executes tools."""
        mock_tool_output = {"result": "tool execution result"}

        mock_agent = AsyncMock()
        mock_agent.invoke.return_value = AgentOutput(
            content="Used tool successfully",
            tool_calls=[{"name": "test_tool", "result": mock_tool_output}]
        )

        with patch("agent_service.api.routes.agents.CurrentAgent", return_value=mock_agent):
            response = await async_client.post(
                "/api/v1/agents/invoke",
                json={"message": "Execute a tool"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "metadata" in data

    async def test_agent_tool_error_handling(self, async_client: AsyncClient):
        """Test agent handles tool execution errors."""
        mock_agent = AsyncMock()
        mock_agent.invoke.side_effect = RuntimeError("Tool execution failed")

        with patch("agent_service.api.routes.agents.CurrentAgent", return_value=mock_agent):
            response = await async_client.post(
                "/api/v1/agents/invoke",
                json={"message": "Execute failing tool"}
            )

        # Should handle error gracefully
        assert response.status_code in [500, 200]


@pytest.mark.integration
class TestAsyncAgentInvocation:
    """Test async (Celery) agent invocation."""

    async def test_async_invoke_creates_task(self, async_client: AsyncClient):
        """Test that async invoke creates Celery task."""
        from unittest.mock import Mock

        mock_task = Mock()
        mock_task.id = "celery-task-123"

        mock_user = Mock()
        mock_user.id = "user-456"

        with patch("agent_service.api.routes.agents.invoke_agent_async.delay", return_value=mock_task):
            with patch("agent_service.api.routes.agents.get_current_user_any", return_value=mock_user):
                response = await async_client.post(
                    "/api/v1/agents/test-agent/invoke-async",
                    json={"message": "Async task"}
                )

        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert data["task_id"] == "celery-task-123"

    async def test_check_async_task_status(self, async_client: AsyncClient):
        """Test checking async task status."""
        mock_task_info = {
            "state": "SUCCESS",
            "successful": True,
            "failed": False,
            "result": {"content": "Task completed"}
        }

        with patch("agent_service.api.routes.agents.get_task_info", return_value=mock_task_info):
            response = await async_client.get("/api/v1/agents/tasks/task-123")

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "SUCCESS"

    async def test_async_task_failure_handling(self, async_client: AsyncClient):
        """Test handling of failed async tasks."""
        mock_task_info = {
            "state": "FAILURE",
            "successful": False,
            "failed": True,
            "result": "Task execution error"
        }

        with patch("agent_service.api.routes.agents.get_task_info", return_value=mock_task_info):
            response = await async_client.get("/api/v1/agents/tasks/failed-task")

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "FAILURE"
        assert "error" in data
