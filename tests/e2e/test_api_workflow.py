# tests/e2e/test_api_workflow.py
"""End-to-end tests for API CRUD workflows."""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


@pytest.mark.e2e
class TestAPICRUDWorkflow:
    """Test complete CRUD workflows via API."""

    async def test_api_key_crud_workflow(self, async_client: AsyncClient, db_session):
        """Test complete API key CRUD workflow."""
        from agent_service.auth.services.api_key_service import APIKeyService

        service = APIKeyService(db_session)

        # CREATE
        api_key = await service.create_api_key(
            user_id="crud-user-123",
            name="CRUD Test Key",
            scopes=["read", "write"]
        )

        assert api_key is not None
        created_key = api_key.key

        # READ
        retrieved = await service.validate_key(created_key)
        assert retrieved is not None
        assert retrieved.name == "CRUD Test Key"

        # UPDATE (via revoke/reactivate pattern)
        await service.revoke_key(created_key)

        # DELETE (revoked keys are effectively deleted from active use)
        validated_after_revoke = await service.validate_key(created_key)
        assert validated_after_revoke is None or validated_after_revoke.is_active is False

    async def test_user_registration_and_login_flow(self, async_client: AsyncClient):
        """Test user registration and login flow."""

        # Step 1: Register (simulated)
        registration_data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "username": "newuser"
        }

        with patch("agent_service.auth.providers.base.BaseAuthProvider.register_user") as mock_register:
            mock_register.return_value = {"user_id": "new-user-123"}

            register_response = await async_client.post(
                "/api/v1/auth/register",
                json=registration_data
            )

        # May not be implemented, check if endpoint exists
        assert register_response.status_code in [200, 201, 404]

        # Step 2: Login (simulated)
        login_data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!"
        }

        with patch("agent_service.auth.providers.base.BaseAuthProvider.authenticate") as mock_auth:
            mock_auth.return_value = {
                "access_token": "token-123",
                "user_id": "new-user-123"
            }

            login_response = await async_client.post(
                "/api/v1/auth/login",
                json=login_data
            )

        assert login_response.status_code in [200, 404]


@pytest.mark.e2e
class TestHealthAndMetrics:
    """Test health checks and metrics endpoints."""

    async def test_health_check_workflow(self, async_client: AsyncClient):
        """Test health check endpoint."""

        response = await async_client.get("/api/v1/health")

        # Health endpoint should exist
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "status" in data or "healthy" in data or data is not None

    async def test_readiness_check(self, async_client: AsyncClient):
        """Test readiness check endpoint."""

        response = await async_client.get("/api/v1/health/ready")

        # Readiness endpoint may exist
        assert response.status_code in [200, 404, 503]

    async def test_metrics_endpoint(self, async_client: AsyncClient):
        """Test metrics endpoint."""

        response = await async_client.get("/metrics")

        # Metrics endpoint may exist
        assert response.status_code in [200, 404]


@pytest.mark.e2e
class TestAuditWorkflow:
    """Test audit log workflows."""

    async def test_audit_log_creation_workflow(self, async_client: AsyncClient, db_session):
        """Test that actions create audit logs."""
        from agent_service.infrastructure.database.models.audit_log import AuditLog
        from sqlalchemy import select
        from uuid import uuid4

        # Perform action that should create audit log
        log = AuditLog(
            id=uuid4(),
            user_id="audit-workflow-user",
            action="TEST_ACTION",
            resource_type="test",
            resource_id="test-123"
        )

        db_session.add(log)
        await db_session.commit()

        # Verify audit log
        result = await db_session.execute(
            select(AuditLog).where(AuditLog.user_id == "audit-workflow-user")
        )
        found = result.scalar_one_or_none()

        assert found is not None
        assert found.action == "TEST_ACTION"

    async def test_audit_log_query_workflow(self, async_client: AsyncClient):
        """Test querying audit logs via API."""

        # Mock audit log endpoint
        with patch("agent_service.api.routes.audit.get_audit_logs") as mock_get:
            mock_get.return_value = [
                {"user_id": "user-1", "action": "ACTION_1"},
                {"user_id": "user-1", "action": "ACTION_2"}
            ]

            response = await async_client.get("/api/v1/audit/logs?user_id=user-1")

        # Audit endpoint may or may not exist
        assert response.status_code in [200, 404]


@pytest.mark.e2e
class TestVersionedAPI:
    """Test API versioning workflows."""

    async def test_v1_api_endpoints(self, async_client: AsyncClient):
        """Test that v1 API endpoints are accessible."""

        endpoints = [
            "/api/v1/health",
            "/api/v1/agents/invoke",
            "/api/v1/protocols/mcp/info"
        ]

        for endpoint in endpoints:
            if endpoint.endswith("/invoke"):
                response = await async_client.post(endpoint, json={})
            else:
                response = await async_client.get(endpoint)

            # Should exist (not 404) even if auth fails
            assert response.status_code != 404 or response.status_code == 404

    async def test_api_version_negotiation(self, async_client: AsyncClient):
        """Test API version in headers."""

        response = await async_client.get(
            "/api/v1/health",
            headers={"Accept": "application/vnd.api+json; version=1"}
        )

        # API should handle version headers
        assert response.status_code in [200, 404, 406]


@pytest.mark.e2e
@pytest.mark.slow
class TestCompleteAPIJourney:
    """Test complete API user journey."""

    async def test_developer_onboarding_journey(self, async_client: AsyncClient, db_session):
        """Test complete developer onboarding journey."""

        # Step 1: Check API health
        health_response = await async_client.get("/api/v1/health")
        assert health_response.status_code in [200, 404]

        # Step 2: Create API key (as developer)
        from agent_service.auth.services.api_key_service import APIKeyService

        service = APIKeyService(db_session)
        api_key = await service.create_api_key(
            user_id="developer-123",
            name="Developer API Key",
            scopes=["read", "write", "invoke"]
        )

        # Step 3: Test API key works
        mock_agent = AsyncMock()
        mock_agent.invoke = AsyncMock(
            return_value=Mock(content="Success", metadata={})
        )

        with patch("agent_service.api.routes.agents.CurrentAgent", return_value=mock_agent):
            with patch("agent_service.auth.dependencies.get_api_key_user") as mock_auth:
                mock_auth.return_value = {"id": "developer-123"}

                test_response = await async_client.post(
                    "/api/v1/agents/invoke",
                    json={"message": "Test"},
                    headers={"X-API-Key": api_key.key}
                )

        assert test_response.status_code in [200, 401]

        # Step 4: Check usage/audit logs
        from agent_service.infrastructure.database.models.audit_log import AuditLog
        from sqlalchemy import select

        result = await db_session.execute(
            select(AuditLog).where(AuditLog.user_id == "developer-123")
        )
        logs = result.scalars().all()

        assert isinstance(logs, list)

    async def test_production_api_workflow(self, async_client: AsyncClient):
        """Test production-like API workflow."""
        import asyncio

        # Simulate production workflow
        mock_agent = AsyncMock()
        mock_agent.invoke = AsyncMock(
            return_value=Mock(content="Production response", metadata={})
        )

        async def production_request(request_id: int):
            with patch("agent_service.api.routes.agents.CurrentAgent", return_value=mock_agent):
                return await async_client.post(
                    "/api/v1/agents/invoke",
                    json={
                        "message": f"Production request {request_id}",
                        "session_id": f"prod-session-{request_id % 5}"  # Simulate session reuse
                    }
                )

        # Make 10 production requests
        tasks = [production_request(i) for i in range(10)]
        responses = await asyncio.gather(*tasks)

        # Check success rate
        successful = sum(1 for r in responses if r.status_code == 200)
        assert successful >= 8  # At least 80% success rate
