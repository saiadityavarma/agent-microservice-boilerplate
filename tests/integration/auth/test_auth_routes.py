"""
Integration tests for authentication API routes.

Tests cover:
- GET /auth/me - returns user info
- API key CRUD operations
- API key rotation
- Token validation endpoint
- Unauthorized access returns 401
- Insufficient permissions returns 403
"""

import pytest
from uuid import uuid4, UUID
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from httpx import AsyncClient
from fastapi import FastAPI, status
from sqlalchemy.ext.asyncio import AsyncSession

from agent_service.auth.schemas import UserInfo, AuthProvider
from agent_service.auth.models.api_key import APIKey
from agent_service.auth.api_key import generate_api_key, hash_api_key
from agent_service.auth.schemas.api_key import APIKeyCreate


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_user_info():
    """Create mock UserInfo for authenticated requests."""
    return UserInfo(
        id=str(uuid4()),
        email="testuser@example.com",
        name="Test User",
        roles=["user", "developer"],
        groups=["AgentService.Developers"],
        provider=AuthProvider.AZURE_AD,
        tenant_id="test-tenant-123",
    )


@pytest.fixture
def mock_admin_user_info():
    """Create mock admin UserInfo for admin requests."""
    return UserInfo(
        id=str(uuid4()),
        email="admin@example.com",
        name="Admin User",
        roles=["admin"],
        groups=["AgentService.Admins"],
        provider=AuthProvider.AZURE_AD,
        tenant_id="test-tenant-123",
    )


@pytest.fixture
async def test_api_key(db_session: AsyncSession, mock_user_info: UserInfo):
    """Create a test API key in the database."""
    raw_key, key_hash = generate_api_key("sk_test")

    api_key = APIKey(
        user_id=UUID(mock_user_info.id),
        name="Test API Key",
        key_hash=key_hash,
        key_prefix="sk_test",
        scopes=["read", "write"],
        rate_limit_tier="pro",
        expires_at=datetime.utcnow() + timedelta(days=30),
    )

    db_session.add(api_key)
    await db_session.commit()
    await db_session.refresh(api_key)

    # Store raw key for testing
    api_key._raw_key = raw_key

    return api_key


# ============================================================================
# Test GET /auth/me - Get Current User Info
# ============================================================================


class TestGetCurrentUserEndpoint:
    """Test GET /auth/me endpoint."""

    @pytest.mark.asyncio
    async def test_get_current_user_with_valid_token(
        self, async_client: AsyncClient, mock_user_info: UserInfo
    ):
        """Test getting current user info with valid authentication."""
        with patch(
            "agent_service.auth.dependencies.get_current_user_any",
            return_value=mock_user_info,
        ):
            response = await async_client.get(
                "/auth/me", headers={"Authorization": "Bearer valid-token"}
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["id"] == mock_user_info.id
            assert data["email"] == mock_user_info.email
            assert data["name"] == mock_user_info.name
            assert "developer" in data["roles"]
            assert data["provider"] == "azure_ad"

    @pytest.mark.asyncio
    async def test_get_current_user_without_auth(self, async_client: AsyncClient):
        """Test that endpoint returns 401 without authentication."""
        response = await async_client.get("/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_user_with_api_key(
        self, async_client: AsyncClient, mock_user_info: UserInfo
    ):
        """Test getting current user info with API key authentication."""
        with patch(
            "agent_service.auth.dependencies.get_current_user_any",
            return_value=mock_user_info,
        ):
            response = await async_client.get(
                "/auth/me", headers={"X-API-Key": "sk_test_validkey"}
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == mock_user_info.id


# ============================================================================
# Test GET /auth/permissions - Get User Permissions
# ============================================================================


class TestGetUserPermissionsEndpoint:
    """Test GET /auth/permissions endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_permissions(
        self, async_client: AsyncClient, mock_user_info: UserInfo
    ):
        """Test getting user permissions and roles."""
        with patch(
            "agent_service.auth.dependencies.get_current_user_any",
            return_value=mock_user_info,
        ):
            response = await async_client.get(
                "/auth/permissions", headers={"Authorization": "Bearer valid-token"}
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["user_id"] == mock_user_info.id
            assert "developer" in data["roles"]
            assert "AgentService.Developers" in data["groups"]
            assert data["provider"] == "azure_ad"
            assert isinstance(data["scopes"], list)

    @pytest.mark.asyncio
    async def test_get_permissions_without_auth(self, async_client: AsyncClient):
        """Test that permissions endpoint requires authentication."""
        response = await async_client.get("/auth/permissions")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Test POST /api/v1/auth/api-keys - Create API Key
# ============================================================================


class TestCreateAPIKeyEndpoint:
    """Test POST /api/v1/auth/api-keys endpoint."""

    @pytest.mark.asyncio
    async def test_create_api_key_success(
        self, async_client: AsyncClient, db_session: AsyncSession, mock_user_info: UserInfo
    ):
        """Test successful API key creation."""
        with patch(
            "agent_service.auth.dependencies.get_current_user_any",
            return_value=mock_user_info,
        ):
            with patch(
                "agent_service.api.routes.auth.get_db_session", return_value=db_session
            ):
                key_data = {
                    "name": "My Test Key",
                    "scopes": ["read", "write"],
                    "expires_in_days": 365,
                    "rate_limit_tier": "pro",
                }

                response = await async_client.post(
                    "/api/v1/auth/api-keys",
                    json=key_data,
                    headers={"Authorization": "Bearer valid-token"},
                )

                assert response.status_code == status.HTTP_201_CREATED
                data = response.json()

                # Verify response contains the raw key (shown only once)
                assert "key" in data
                assert data["key"].startswith("sk_")
                assert data["name"] == "My Test Key"
                assert "read" in data["scopes"]
                assert data["rate_limit_tier"] == "pro"
                assert "id" in data
                assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_api_key_with_custom_prefix(
        self, async_client: AsyncClient, db_session: AsyncSession, mock_user_info: UserInfo
    ):
        """Test creating API key with custom prefix."""
        with patch(
            "agent_service.auth.dependencies.get_current_user_any",
            return_value=mock_user_info,
        ):
            with patch(
                "agent_service.api.routes.auth.get_db_session", return_value=db_session
            ):
                key_data = {
                    "name": "Custom Prefix Key",
                    "scopes": ["read"],
                    "prefix": "pk_test",
                }

                response = await async_client.post(
                    "/api/v1/auth/api-keys",
                    json=key_data,
                    headers={"Authorization": "Bearer valid-token"},
                )

                assert response.status_code == status.HTTP_201_CREATED
                data = response.json()
                assert data["key"].startswith("pk_test_")

    @pytest.mark.asyncio
    async def test_create_api_key_without_auth(self, async_client: AsyncClient):
        """Test that API key creation requires authentication."""
        key_data = {"name": "Test Key", "scopes": ["read"]}

        response = await async_client.post("/api/v1/auth/api-keys", json=key_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_create_api_key_invalid_data(
        self, async_client: AsyncClient, mock_user_info: UserInfo
    ):
        """Test API key creation with invalid data."""
        with patch(
            "agent_service.auth.dependencies.get_current_user_any",
            return_value=mock_user_info,
        ):
            # Missing required 'name' field
            key_data = {"scopes": ["read"]}

            response = await async_client.post(
                "/api/v1/auth/api-keys",
                json=key_data,
                headers={"Authorization": "Bearer valid-token"},
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ============================================================================
# Test GET /api/v1/auth/api-keys - List API Keys
# ============================================================================


class TestListAPIKeysEndpoint:
    """Test GET /api/v1/auth/api-keys endpoint."""

    @pytest.mark.asyncio
    async def test_list_api_keys(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        mock_user_info: UserInfo,
        test_api_key: APIKey,
    ):
        """Test listing user's API keys."""
        with patch(
            "agent_service.auth.dependencies.get_current_user_any",
            return_value=mock_user_info,
        ):
            with patch(
                "agent_service.api.routes.auth.get_db_session", return_value=db_session
            ):
                response = await async_client.get(
                    "/api/v1/auth/api-keys",
                    headers={"Authorization": "Bearer valid-token"},
                )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()

                assert isinstance(data, list)
                assert len(data) >= 1

                # Verify raw key is NOT returned in list
                for key in data:
                    assert "key" not in key
                    assert "key_prefix" in key
                    assert "name" in key
                    assert "is_active" in key

    @pytest.mark.asyncio
    async def test_list_api_keys_empty(
        self, async_client: AsyncClient, db_session: AsyncSession, mock_user_info: UserInfo
    ):
        """Test listing API keys when user has none."""
        # Use a different user ID
        different_user = UserInfo(
            id=str(uuid4()),
            email="other@example.com",
            name="Other User",
            roles=["user"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        with patch(
            "agent_service.auth.dependencies.get_current_user_any",
            return_value=different_user,
        ):
            with patch(
                "agent_service.api.routes.auth.get_db_session", return_value=db_session
            ):
                response = await async_client.get(
                    "/api/v1/auth/api-keys",
                    headers={"Authorization": "Bearer valid-token"},
                )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert isinstance(data, list)
                assert len(data) == 0


# ============================================================================
# Test GET /api/v1/auth/api-keys/{key_id} - Get API Key Details
# ============================================================================


class TestGetAPIKeyEndpoint:
    """Test GET /api/v1/auth/api-keys/{key_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_api_key_details(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        mock_user_info: UserInfo,
        test_api_key: APIKey,
    ):
        """Test getting API key details."""
        with patch(
            "agent_service.auth.dependencies.get_current_user_any",
            return_value=mock_user_info,
        ):
            with patch(
                "agent_service.api.routes.auth.get_db_session", return_value=db_session
            ):
                response = await async_client.get(
                    f"/api/v1/auth/api-keys/{test_api_key.id}",
                    headers={"Authorization": "Bearer valid-token"},
                )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()

                assert data["id"] == str(test_api_key.id)
                assert data["name"] == test_api_key.name
                assert "key" not in data  # Raw key should not be returned
                assert data["key_prefix"] == test_api_key.key_prefix
                assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_api_key_not_found(
        self, async_client: AsyncClient, db_session: AsyncSession, mock_user_info: UserInfo
    ):
        """Test getting non-existent API key returns 404."""
        with patch(
            "agent_service.auth.dependencies.get_current_user_any",
            return_value=mock_user_info,
        ):
            with patch(
                "agent_service.api.routes.auth.get_db_session", return_value=db_session
            ):
                fake_id = str(uuid4())
                response = await async_client.get(
                    f"/api/v1/auth/api-keys/{fake_id}",
                    headers={"Authorization": "Bearer valid-token"},
                )

                assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_api_key_forbidden(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_api_key: APIKey,
    ):
        """Test that users cannot access other users' API keys."""
        # Different user trying to access the key
        other_user = UserInfo(
            id=str(uuid4()),
            email="other@example.com",
            name="Other User",
            roles=["user"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        with patch(
            "agent_service.auth.dependencies.get_current_user_any",
            return_value=other_user,
        ):
            with patch(
                "agent_service.api.routes.auth.get_db_session", return_value=db_session
            ):
                response = await async_client.get(
                    f"/api/v1/auth/api-keys/{test_api_key.id}",
                    headers={"Authorization": "Bearer valid-token"},
                )

                assert response.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# Test DELETE /api/v1/auth/api-keys/{key_id} - Revoke API Key
# ============================================================================


class TestRevokeAPIKeyEndpoint:
    """Test DELETE /api/v1/auth/api-keys/{key_id} endpoint."""

    @pytest.mark.asyncio
    async def test_revoke_api_key_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        mock_user_info: UserInfo,
        test_api_key: APIKey,
    ):
        """Test successful API key revocation."""
        with patch(
            "agent_service.auth.dependencies.get_current_user_any",
            return_value=mock_user_info,
        ):
            with patch(
                "agent_service.api.routes.auth.get_db_session", return_value=db_session
            ):
                response = await async_client.delete(
                    f"/api/v1/auth/api-keys/{test_api_key.id}",
                    headers={"Authorization": "Bearer valid-token"},
                )

                assert response.status_code == status.HTTP_204_NO_CONTENT

                # Verify key is soft-deleted
                await db_session.refresh(test_api_key)
                assert test_api_key.deleted_at is not None

    @pytest.mark.asyncio
    async def test_revoke_api_key_not_found(
        self, async_client: AsyncClient, db_session: AsyncSession, mock_user_info: UserInfo
    ):
        """Test revoking non-existent API key returns 404."""
        with patch(
            "agent_service.auth.dependencies.get_current_user_any",
            return_value=mock_user_info,
        ):
            with patch(
                "agent_service.api.routes.auth.get_db_session", return_value=db_session
            ):
                fake_id = str(uuid4())
                response = await async_client.delete(
                    f"/api/v1/auth/api-keys/{fake_id}",
                    headers={"Authorization": "Bearer valid-token"},
                )

                assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_revoke_api_key_forbidden(
        self, async_client: AsyncClient, db_session: AsyncSession, test_api_key: APIKey
    ):
        """Test that users cannot revoke other users' API keys."""
        other_user = UserInfo(
            id=str(uuid4()),
            email="other@example.com",
            name="Other User",
            roles=["user"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        with patch(
            "agent_service.auth.dependencies.get_current_user_any",
            return_value=other_user,
        ):
            with patch(
                "agent_service.api.routes.auth.get_db_session", return_value=db_session
            ):
                response = await async_client.delete(
                    f"/api/v1/auth/api-keys/{test_api_key.id}",
                    headers={"Authorization": "Bearer valid-token"},
                )

                assert response.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# Test POST /api/v1/auth/api-keys/{key_id}/rotate - Rotate API Key
# ============================================================================


class TestRotateAPIKeyEndpoint:
    """Test POST /api/v1/auth/api-keys/{key_id}/rotate endpoint."""

    @pytest.mark.asyncio
    async def test_rotate_api_key_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        mock_user_info: UserInfo,
        test_api_key: APIKey,
    ):
        """Test successful API key rotation."""
        old_key_id = test_api_key.id

        with patch(
            "agent_service.auth.dependencies.get_current_user_any",
            return_value=mock_user_info,
        ):
            with patch(
                "agent_service.api.routes.auth.get_db_session", return_value=db_session
            ):
                response = await async_client.post(
                    f"/api/v1/auth/api-keys/{old_key_id}/rotate",
                    headers={"Authorization": "Bearer valid-token"},
                )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()

                # Verify response structure
                assert data["old_key_id"] == str(old_key_id)
                assert "new_key" in data
                assert data["new_key"]["key"].startswith("sk_")  # Raw key shown once
                assert data["new_key"]["name"] == test_api_key.name  # Same name
                assert data["new_key"]["scopes"] == test_api_key.scopes  # Same scopes

                # Old key should be revoked
                await db_session.refresh(test_api_key)
                assert test_api_key.deleted_at is not None

    @pytest.mark.asyncio
    async def test_rotate_api_key_not_found(
        self, async_client: AsyncClient, db_session: AsyncSession, mock_user_info: UserInfo
    ):
        """Test rotating non-existent API key returns 404."""
        with patch(
            "agent_service.auth.dependencies.get_current_user_any",
            return_value=mock_user_info,
        ):
            with patch(
                "agent_service.api.routes.auth.get_db_session", return_value=db_session
            ):
                fake_id = str(uuid4())
                response = await async_client.post(
                    f"/api/v1/auth/api-keys/{fake_id}/rotate",
                    headers={"Authorization": "Bearer valid-token"},
                )

                assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_rotate_api_key_forbidden(
        self, async_client: AsyncClient, db_session: AsyncSession, test_api_key: APIKey
    ):
        """Test that users cannot rotate other users' API keys."""
        other_user = UserInfo(
            id=str(uuid4()),
            email="other@example.com",
            name="Other User",
            roles=["user"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        with patch(
            "agent_service.auth.dependencies.get_current_user_any",
            return_value=other_user,
        ):
            with patch(
                "agent_service.api.routes.auth.get_db_session", return_value=db_session
            ):
                response = await async_client.post(
                    f"/api/v1/auth/api-keys/{test_api_key.id}/rotate",
                    headers={"Authorization": "Bearer valid-token"},
                )

                assert response.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# Test POST /auth/validate - Token Validation
# ============================================================================


class TestTokenValidationEndpoint:
    """Test POST /auth/validate endpoint."""

    @pytest.mark.asyncio
    async def test_validate_token_placeholder(self, async_client: AsyncClient):
        """Test token validation endpoint (placeholder implementation)."""
        # Note: This is a placeholder test as the actual implementation is TODO
        token_data = {"token": "test.jwt.token", "token_type": "bearer"}

        response = await async_client.post("/auth/validate", json=token_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Placeholder returns invalid with error message
        assert "valid" in data
        assert "error" in data


# ============================================================================
# Test Authorization - 401 Unauthorized
# ============================================================================


class TestUnauthorizedAccess:
    """Test that endpoints return 401 for unauthorized access."""

    @pytest.mark.asyncio
    async def test_get_me_without_token(self, async_client: AsyncClient):
        """Test /auth/me returns 401 without token."""
        response = await async_client.get("/auth/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_permissions_without_token(self, async_client: AsyncClient):
        """Test /auth/permissions returns 401 without token."""
        response = await async_client.get("/auth/permissions")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_list_api_keys_without_token(self, async_client: AsyncClient):
        """Test listing API keys returns 401 without token."""
        response = await async_client.get("/api/v1/auth/api-keys")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_create_api_key_without_token(self, async_client: AsyncClient):
        """Test creating API key returns 401 without token."""
        response = await async_client.post(
            "/api/v1/auth/api-keys", json={"name": "Test", "scopes": ["read"]}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Test Authorization - 403 Forbidden
# ============================================================================


class TestForbiddenAccess:
    """Test that endpoints return 403 for insufficient permissions."""

    @pytest.mark.asyncio
    async def test_access_other_users_api_key(
        self, async_client: AsyncClient, db_session: AsyncSession, test_api_key: APIKey
    ):
        """Test that users cannot access other users' API keys."""
        other_user = UserInfo(
            id=str(uuid4()),
            email="other@example.com",
            name="Other User",
            roles=["user"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        with patch(
            "agent_service.auth.dependencies.get_current_user_any",
            return_value=other_user,
        ):
            with patch(
                "agent_service.api.routes.auth.get_db_session", return_value=db_session
            ):
                # Try to get another user's key
                response = await async_client.get(
                    f"/api/v1/auth/api-keys/{test_api_key.id}",
                    headers={"Authorization": "Bearer valid-token"},
                )

                assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_delete_other_users_api_key(
        self, async_client: AsyncClient, db_session: AsyncSession, test_api_key: APIKey
    ):
        """Test that users cannot delete other users' API keys."""
        other_user = UserInfo(
            id=str(uuid4()),
            email="other@example.com",
            name="Other User",
            roles=["user"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        with patch(
            "agent_service.auth.dependencies.get_current_user_any",
            return_value=other_user,
        ):
            with patch(
                "agent_service.api.routes.auth.get_db_session", return_value=db_session
            ):
                response = await async_client.delete(
                    f"/api/v1/auth/api-keys/{test_api_key.id}",
                    headers={"Authorization": "Bearer valid-token"},
                )

                assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_rotate_other_users_api_key(
        self, async_client: AsyncClient, db_session: AsyncSession, test_api_key: APIKey
    ):
        """Test that users cannot rotate other users' API keys."""
        other_user = UserInfo(
            id=str(uuid4()),
            email="other@example.com",
            name="Other User",
            roles=["user"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        with patch(
            "agent_service.auth.dependencies.get_current_user_any",
            return_value=other_user,
        ):
            with patch(
                "agent_service.api.routes.auth.get_db_session", return_value=db_session
            ):
                response = await async_client.post(
                    f"/api/v1/auth/api-keys/{test_api_key.id}/rotate",
                    headers={"Authorization": "Bearer valid-token"},
                )

                assert response.status_code == status.HTTP_403_FORBIDDEN
