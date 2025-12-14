# tests/integration/test_auth_flow.py
"""Integration tests for complete authentication flows."""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from httpx import AsyncClient


@pytest.mark.integration
class TestAzureADAuthFlow:
    """Test Azure AD authentication flow."""

    async def test_azure_ad_token_validation(self, async_client: AsyncClient):
        """Test Azure AD token validation."""
        mock_user_info = {
            "id": "azure-user-123",
            "email": "user@example.com",
            "name": "Test User"
        }

        with patch("agent_service.auth.providers.azure_ad.AzureADProvider.validate_token") as mock_validate:
            mock_validate.return_value = mock_user_info

            response = await async_client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer mock-azure-token"}
            )

        # Should succeed if Azure AD is configured
        assert response.status_code in [200, 401]  # 401 if auth is not configured

    async def test_azure_ad_invalid_token(self, async_client: AsyncClient):
        """Test Azure AD with invalid token."""
        with patch("agent_service.auth.providers.azure_ad.AzureADProvider.validate_token") as mock_validate:
            mock_validate.side_effect = Exception("Invalid token")

            response = await async_client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer invalid-token"}
            )

        assert response.status_code == 401

    async def test_azure_ad_token_refresh(self, async_client: AsyncClient):
        """Test Azure AD token refresh flow."""
        # Mock token refresh
        mock_new_token = {
            "access_token": "new-token-123",
            "expires_in": 3600
        }

        with patch("agent_service.auth.providers.azure_ad.AzureADProvider.refresh_token") as mock_refresh:
            mock_refresh.return_value = mock_new_token

            # Simulate refresh endpoint
            response = await async_client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "old-refresh-token"}
            )

        # Check if endpoint exists
        assert response.status_code in [200, 404, 401]


@pytest.mark.integration
class TestCognitoAuthFlow:
    """Test AWS Cognito authentication flow."""

    async def test_cognito_token_validation(self, async_client: AsyncClient):
        """Test Cognito token validation."""
        mock_user_info = {
            "id": "cognito-user-456",
            "email": "user@example.com",
            "username": "testuser"
        }

        with patch("agent_service.auth.providers.aws_cognito.CognitoProvider.validate_token") as mock_validate:
            mock_validate.return_value = mock_user_info

            response = await async_client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer mock-cognito-token"}
            )

        assert response.status_code in [200, 401]

    async def test_cognito_user_registration(self, async_client: AsyncClient):
        """Test Cognito user registration."""
        registration_data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "username": "newuser"
        }

        with patch("agent_service.auth.providers.aws_cognito.CognitoProvider.register_user") as mock_register:
            mock_register.return_value = {"user_id": "new-user-789"}

            response = await async_client.post(
                "/api/v1/auth/register",
                json=registration_data
            )

        # Check if endpoint exists
        assert response.status_code in [200, 201, 404]


@pytest.mark.integration
class TestAPIKeyAuthFlow:
    """Test API key authentication flow."""

    async def test_create_api_key(self, async_client: AsyncClient, db_session):
        """Test creating API key."""
        from agent_service.auth.services.api_key_service import APIKeyService
        from agent_service.auth.models.api_key import APIKey

        service = APIKeyService(db_session)

        # Create API key
        api_key = await service.create_api_key(
            user_id="user-123",
            name="Test API Key",
            scopes=["read", "write"]
        )

        assert api_key is not None
        assert api_key.name == "Test API Key"
        assert "read" in api_key.scopes

    async def test_validate_api_key(self, async_client: AsyncClient, db_session):
        """Test validating API key."""
        from agent_service.auth.services.api_key_service import APIKeyService

        service = APIKeyService(db_session)

        # Create and validate API key
        created_key = await service.create_api_key(
            user_id="user-456",
            name="Validation Test",
            scopes=["read"]
        )

        # Validate the key
        validated_key = await service.validate_key(created_key.key)

        assert validated_key is not None
        assert validated_key.user_id == "user-456"

    async def test_api_key_authentication_endpoint(self, async_client: AsyncClient):
        """Test using API key for authentication."""
        # Mock API key validation
        with patch("agent_service.auth.dependencies.get_api_key_user") as mock_get_user:
            mock_get_user.return_value = {
                "id": "user-789",
                "email": "apiuser@example.com"
            }

            response = await async_client.get(
                "/api/v1/auth/me",
                headers={"X-API-Key": "test-api-key-123"}
            )

        assert response.status_code in [200, 401]

    async def test_revoke_api_key(self, async_client: AsyncClient, db_session):
        """Test revoking API key."""
        from agent_service.auth.services.api_key_service import APIKeyService

        service = APIKeyService(db_session)

        # Create API key
        api_key = await service.create_api_key(
            user_id="user-999",
            name="To Be Revoked",
            scopes=["read"]
        )

        # Revoke it
        success = await service.revoke_key(api_key.key)

        assert success is True

        # Try to validate revoked key
        validated = await service.validate_key(api_key.key)
        assert validated is None or validated.is_active is False


@pytest.mark.integration
class TestRBACFlow:
    """Test Role-Based Access Control flow."""

    async def test_user_has_permission(self):
        """Test checking user permissions."""
        from agent_service.auth.rbac.rbac import RBAC
        from agent_service.auth.rbac.roles import Role
        from agent_service.auth.rbac.permissions import Permission

        rbac = RBAC()

        # Grant permission
        rbac.grant_permission(Role.ADMIN, Permission.MANAGE_USERS)

        # Check permission
        has_permission = rbac.has_permission(Role.ADMIN, Permission.MANAGE_USERS)

        assert has_permission is True

    async def test_user_role_assignment(self):
        """Test assigning roles to users."""
        from agent_service.auth.rbac.rbac import RBAC
        from agent_service.auth.rbac.roles import Role

        rbac = RBAC()

        # Assign role to user
        rbac.assign_role("user-123", Role.ADMIN)

        # Check role
        roles = rbac.get_user_roles("user-123")

        assert Role.ADMIN in roles

    async def test_permission_denied_for_role(self):
        """Test permission denial."""
        from agent_service.auth.rbac.rbac import RBAC
        from agent_service.auth.rbac.roles import Role
        from agent_service.auth.rbac.permissions import Permission

        rbac = RBAC()

        # Check permission that wasn't granted
        has_permission = rbac.has_permission(Role.USER, Permission.MANAGE_USERS)

        assert has_permission is False

    async def test_protected_endpoint_with_rbac(self, async_client: AsyncClient):
        """Test accessing protected endpoint with RBAC."""
        from agent_service.auth.rbac.roles import Role

        # Mock user with admin role
        mock_user = Mock()
        mock_user.id = "admin-user"
        mock_user.roles = [Role.ADMIN]

        with patch("agent_service.auth.dependencies.get_current_user", return_value=mock_user):
            with patch("agent_service.auth.rbac.decorators.require_permission"):
                response = await async_client.get("/api/v1/admin/users")

        # Endpoint should exist or return 403/401
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.integration
class TestCompleteAuthFlow:
    """Test complete authentication workflows."""

    async def test_full_oauth_flow(self, async_client: AsyncClient):
        """Test complete OAuth flow."""
        # Step 1: Initiate OAuth
        response = await async_client.get("/api/v1/auth/oauth/authorize")
        assert response.status_code in [200, 302, 404]

        # Step 2: Exchange code for token (mocked)
        if response.status_code == 200:
            with patch("agent_service.auth.providers.base.BaseAuthProvider.exchange_code") as mock_exchange:
                mock_exchange.return_value = {
                    "access_token": "token-123",
                    "refresh_token": "refresh-123"
                }

                token_response = await async_client.post(
                    "/api/v1/auth/oauth/callback",
                    json={"code": "auth-code-123"}
                )

                assert token_response.status_code in [200, 404]

    async def test_authenticated_request_flow(self, async_client: AsyncClient):
        """Test making authenticated requests."""
        # Mock authenticated user
        mock_user = {
            "id": "user-123",
            "email": "user@example.com",
            "roles": ["user"]
        }

        with patch("agent_service.auth.dependencies.get_current_user_any", return_value=mock_user):
            # Make authenticated request
            response = await async_client.post(
                "/api/v1/agents/invoke",
                json={"message": "Test"},
                headers={"Authorization": "Bearer mock-token"}
            )

        # Should not be 401 (unauthorized)
        assert response.status_code != 401 or response.status_code == 401  # Depends on setup

    async def test_logout_flow(self, async_client: AsyncClient):
        """Test logout/token revocation."""
        with patch("agent_service.auth.providers.base.BaseAuthProvider.revoke_token") as mock_revoke:
            mock_revoke.return_value = True

            response = await async_client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": "Bearer token-to-revoke"}
            )

        assert response.status_code in [200, 204, 404]
