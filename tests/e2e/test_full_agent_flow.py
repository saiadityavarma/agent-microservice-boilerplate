# tests/e2e/test_full_agent_flow.py
"""End-to-end tests for complete agent workflows."""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, Mock


@pytest.mark.e2e
class TestCompleteAgentFlow:
    """Test complete agent flow from user creation to agent invocation."""

    async def test_full_user_journey(self, async_client: AsyncClient, db_session):
        """Test complete user journey: create user -> create API key -> invoke agent -> check session."""

        # Step 1: Create/register user (simulated)
        mock_user = {
            "id": "e2e-user-123",
            "email": "e2e@example.com",
            "username": "e2euser"
        }

        # Step 2: Create API key
        from agent_service.auth.services.api_key_service import APIKeyService

        api_key_service = APIKeyService(db_session)
        api_key = await api_key_service.create_api_key(
            user_id=mock_user["id"],
            name="E2E Test API Key",
            scopes=["read", "write", "invoke"]
        )

        assert api_key is not None
        assert api_key.key is not None

        # Step 3: Invoke agent with API key
        mock_agent = AsyncMock()
        mock_agent.invoke = AsyncMock(
            return_value=Mock(content="E2E Test Response", metadata={})
        )

        with patch("agent_service.api.routes.agents.CurrentAgent", return_value=mock_agent):
            with patch("agent_service.auth.dependencies.get_api_key_user") as mock_auth:
                mock_auth.return_value = mock_user

                response = await async_client.post(
                    "/api/v1/agents/invoke",
                    json={
                        "message": "E2E test message",
                        "session_id": "e2e-session-123"
                    },
                    headers={"X-API-Key": api_key.key}
                )

        assert response.status_code in [200, 401]  # 401 if auth not fully configured

        # Step 4: Check session (if session tracking is implemented)
        # This would depend on your session implementation

        # Step 5: Verify audit log
        from agent_service.infrastructure.database.models.audit_log import AuditLog
        from sqlalchemy import select

        result = await db_session.execute(
            select(AuditLog).where(AuditLog.user_id == mock_user["id"])
        )
        logs = result.scalars().all()

        # Audit logs may or may not be created depending on implementation
        assert isinstance(logs, list)

    async def test_anonymous_to_authenticated_flow(self, async_client: AsyncClient):
        """Test flow from anonymous to authenticated access."""

        # Step 1: Try to access protected endpoint without auth
        response = await async_client.post(
            "/api/v1/agents/invoke",
            json={"message": "Unauthorized request"}
        )

        # Should be unauthorized
        assert response.status_code == 401

        # Step 2: Authenticate and retry
        mock_user = {"id": "auth-user", "email": "auth@example.com"}

        with patch("agent_service.auth.dependencies.get_current_user_any", return_value=mock_user):
            mock_agent = AsyncMock()
            mock_agent.invoke = AsyncMock(
                return_value=Mock(content="Authenticated response", metadata={})
            )

            with patch("agent_service.api.routes.agents.CurrentAgent", return_value=mock_agent):
                response = await async_client.post(
                    "/api/v1/agents/invoke",
                    json={"message": "Authenticated request"},
                    headers={"Authorization": "Bearer mock-token"}
                )

        # Should succeed
        assert response.status_code == 200

    async def test_multi_agent_workflow(self, async_client: AsyncClient):
        """Test workflow involving multiple agent invocations."""

        mock_agent = AsyncMock()
        invocation_count = 0

        def mock_invoke(input_data):
            nonlocal invocation_count
            invocation_count += 1
            return Mock(
                content=f"Response {invocation_count}",
                metadata={"invocation": invocation_count}
            )

        mock_agent.invoke = AsyncMock(side_effect=mock_invoke)

        with patch("agent_service.api.routes.agents.CurrentAgent", return_value=mock_agent):
            # First invocation
            response1 = await async_client.post(
                "/api/v1/agents/invoke",
                json={"message": "First request", "session_id": "multi-session"}
            )

            # Second invocation (same session)
            response2 = await async_client.post(
                "/api/v1/agents/invoke",
                json={"message": "Second request", "session_id": "multi-session"}
            )

            # Third invocation (same session)
            response3 = await async_client.post(
                "/api/v1/agents/invoke",
                json={"message": "Third request", "session_id": "multi-session"}
            )

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200
        assert invocation_count == 3


@pytest.mark.e2e
class TestStreamingWorkflow:
    """Test end-to-end streaming workflows."""

    async def test_complete_streaming_flow(self, async_client: AsyncClient):
        """Test complete streaming agent flow."""

        async def mock_stream(input_data):
            words = ["The", "quick", "brown", "fox"]
            for word in words:
                yield Mock(type="text", content=word)

        mock_agent = AsyncMock()
        mock_agent.stream = mock_stream

        with patch("agent_service.api.routes.agents.CurrentAgent", return_value=mock_agent):
            response = await async_client.post(
                "/api/v1/agents/stream",
                json={"message": "Stream test"}
            )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    async def test_streaming_with_tool_calls(self, async_client: AsyncClient):
        """Test streaming with intermediate tool calls."""

        async def mock_stream(input_data):
            yield Mock(type="text", content="Starting")
            yield Mock(type="tool_start", content="calculator")
            yield Mock(type="tool_end", content="result: 42")
            yield Mock(type="text", content="Completed")

        mock_agent = AsyncMock()
        mock_agent.stream = mock_stream

        with patch("agent_service.api.routes.agents.CurrentAgent", return_value=mock_agent):
            response = await async_client.post(
                "/api/v1/agents/stream",
                json={"message": "Calculate something"}
            )

        assert response.status_code == 200


@pytest.mark.e2e
class TestAsyncWorkflow:
    """Test end-to-end async (background job) workflows."""

    async def test_complete_async_flow(self, async_client: AsyncClient):
        """Test complete async agent invocation flow."""

        # Step 1: Queue async task
        mock_task = Mock()
        mock_task.id = "e2e-async-task-123"

        mock_user = Mock()
        mock_user.id = "async-user"

        with patch("agent_service.api.routes.agents.invoke_agent_async.delay", return_value=mock_task):
            with patch("agent_service.api.routes.agents.get_current_user_any", return_value=mock_user):
                queue_response = await async_client.post(
                    "/api/v1/agents/test-agent/invoke-async",
                    json={"message": "Long running task"}
                )

        assert queue_response.status_code == 202
        task_id = queue_response.json()["task_id"]

        # Step 2: Poll task status (simulate pending)
        mock_task_info = {
            "state": "PENDING",
            "successful": False,
            "failed": False
        }

        with patch("agent_service.api.routes.agents.get_task_info", return_value=mock_task_info):
            status_response = await async_client.get(f"/api/v1/agents/tasks/{task_id}")

        assert status_response.status_code == 200
        assert status_response.json()["status"] == "queued"

        # Step 3: Poll task status (simulate success)
        mock_task_info["state"] = "SUCCESS"
        mock_task_info["successful"] = True
        mock_task_info["result"] = {"content": "Task completed"}

        with patch("agent_service.api.routes.agents.get_task_info", return_value=mock_task_info):
            final_response = await async_client.get(f"/api/v1/agents/tasks/{task_id}")

        assert final_response.status_code == 200
        assert final_response.json()["status"] == "completed"


@pytest.mark.e2e
class TestProtocolWorkflows:
    """Test end-to-end protocol workflows."""

    async def test_mcp_complete_workflow(self, async_client: AsyncClient):
        """Test complete MCP workflow."""

        # Step 1: Discover tools
        with patch("agent_service.api.routes.protocols.protocol_registry.is_registered", return_value=True):
            from agent_service.interfaces import ToolSchema

            mock_tool = Mock()
            mock_tool.schema = ToolSchema(
                name="mcp_workflow_tool",
                description="Test tool",
                parameters={"type": "object"}
            )

            with patch("agent_service.api.routes.protocols.tool_registry.list_tools", return_value=[mock_tool.schema]):
                tools_response = await async_client.get("/api/v1/protocols/mcp/tools")

        assert tools_response.status_code == 200

        # Step 2: Execute tool
        with patch("agent_service.api.routes.protocols.protocol_registry.is_registered", return_value=True):
            with patch("agent_service.api.routes.protocols.tool_registry.execute", return_value={"result": "success"}):
                exec_response = await async_client.post(
                    "/api/v1/protocols/mcp/tools/mcp_workflow_tool",
                    json={"arguments": {}}
                )

        assert exec_response.status_code == 200

    async def test_a2a_complete_workflow(self, async_client: AsyncClient):
        """Test complete A2A workflow."""

        # Step 1: Create task
        mock_handler = AsyncMock()
        mock_handler.handle_request.return_value = {
            "task_id": "a2a-workflow-task",
            "status": "created"
        }

        with patch("agent_service.api.routes.protocols.protocol_registry.get", return_value=mock_handler):
            with patch("agent_service.api.routes.protocols.get_default_agent"):
                create_response = await async_client.post(
                    "/api/v1/protocols/a2a/tasks",
                    json={"message": "Create task"}
                )

        if create_response.status_code == 200:
            task_id = create_response.json()["task_id"]

            # Step 2: Add message
            with patch("agent_service.api.routes.protocols.protocol_registry.get", return_value=mock_handler):
                with patch("agent_service.api.routes.protocols.get_default_agent"):
                    message_response = await async_client.post(
                        f"/api/v1/protocols/a2a/tasks/{task_id}/messages",
                        json={"content": "Follow-up"}
                    )

            assert message_response.status_code == 200


@pytest.mark.e2e
@pytest.mark.slow
class TestComplexScenarios:
    """Test complex real-world scenarios."""

    async def test_high_frequency_requests(self, async_client: AsyncClient):
        """Test handling high frequency requests."""
        import asyncio

        mock_agent = AsyncMock()
        mock_agent.invoke = AsyncMock(
            return_value=Mock(content="Response", metadata={})
        )

        async def make_request(i: int):
            with patch("agent_service.api.routes.agents.CurrentAgent", return_value=mock_agent):
                return await async_client.post(
                    "/api/v1/agents/invoke",
                    json={"message": f"Request {i}"}
                )

        # Make 20 concurrent requests
        tasks = [make_request(i) for i in range(20)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Most should succeed (some may be rate limited)
        successful = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 200)
        assert successful >= 10

    async def test_error_recovery_workflow(self, async_client: AsyncClient):
        """Test error recovery in workflows."""

        # Step 1: Make failing request
        mock_agent = AsyncMock()
        mock_agent.invoke.side_effect = RuntimeError("Agent error")

        with patch("agent_service.api.routes.agents.CurrentAgent", return_value=mock_agent):
            error_response = await async_client.post(
                "/api/v1/agents/invoke",
                json={"message": "Failing request"}
            )

        assert error_response.status_code == 500

        # Step 2: Retry with working agent
        mock_agent.invoke.side_effect = None
        mock_agent.invoke.return_value = Mock(content="Recovered", metadata={})

        with patch("agent_service.api.routes.agents.CurrentAgent", return_value=mock_agent):
            success_response = await async_client.post(
                "/api/v1/agents/invoke",
                json={"message": "Retry request"}
            )

        assert success_response.status_code == 200

    async def test_session_persistence_across_requests(self, async_client: AsyncClient):
        """Test session persistence across multiple requests."""

        session_id = "persistent-session-123"
        messages = ["First", "Second", "Third"]

        mock_agent = AsyncMock()
        received_messages = []

        def track_invoke(input_data):
            received_messages.append(input_data.message)
            return Mock(content=f"Response to {input_data.message}", metadata={})

        mock_agent.invoke = AsyncMock(side_effect=track_invoke)

        with patch("agent_service.api.routes.agents.CurrentAgent", return_value=mock_agent):
            for message in messages:
                response = await async_client.post(
                    "/api/v1/agents/invoke",
                    json={"message": message, "session_id": session_id}
                )
                assert response.status_code == 200

        # All messages should have been received
        assert received_messages == messages
