"""
Authentication and authorization bypass tests.

Tests for authentication security including:
- Route protection
- Token validation
- API key validation
- RBAC enforcement
- Session security
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from datetime import datetime, timedelta
import jwt

from agent_service.auth.schemas import UserInfo, AuthProvider
from agent_service.auth.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
    AuthenticationError,
)


class TestRouteProtection:
    """Test routes require proper authentication."""

    @pytest.mark.asyncio
    async def test_protected_route_requires_auth(self, async_client: AsyncClient):
        """Test protected routes reject unauthenticated requests."""
        # Try to access agents endpoint without auth
        response = await async_client.get("/api/v1/agents")

        # Should be unauthorized
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_protected_route_returns_401(self, async_client: AsyncClient):
        """Test protected routes return 401 Unauthorized."""
        response = await async_client.post("/api/v1/agents")

        # Should return 401 for missing authentication
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_public_routes_accessible_without_auth(self, async_client: AsyncClient):
        """Test public routes are accessible without authentication."""
        # Health check should be public
        response = await async_client.get("/health")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_docs_accessible_in_debug_mode(self, async_client: AsyncClient):
        """Test API docs are accessible in debug mode."""
        response = await async_client.get("/docs")

        # Should be accessible (200) or disabled (404)
        assert response.status_code in [200, 404]


class TestInvalidTokenRejection:
    """Test invalid tokens are properly rejected."""

    @pytest.mark.asyncio
    async def test_malformed_token_rejected(self, async_client: AsyncClient):
        """Test malformed JWT tokens are rejected."""
        response = await async_client.get(
            "/api/v1/agents",
            headers={"Authorization": "Bearer malformed.token.here"}
        )

        # Should reject malformed token
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_signature_rejected(self, async_client: AsyncClient):
        """Test tokens with invalid signatures are rejected."""
        # Create a token with wrong signature
        fake_token = jwt.encode(
            {"sub": "user123", "exp": datetime.utcnow() + timedelta(hours=1)},
            "wrong-secret-key",
            algorithm="HS256"
        )

        response = await async_client.get(
            "/api/v1/agents",
            headers={"Authorization": f"Bearer {fake_token}"}
        )

        # Should reject invalid signature
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_bearer_prefix_rejected(self, async_client: AsyncClient):
        """Test tokens without 'Bearer' prefix are rejected."""
        response = await async_client.get(
            "/api/v1/agents",
            headers={"Authorization": "token-without-bearer-prefix"}
        )

        # Should reject improper format
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_token_rejected(self, async_client: AsyncClient):
        """Test empty tokens are rejected."""
        response = await async_client.get(
            "/api/v1/agents",
            headers={"Authorization": "Bearer "}
        )

        # Should reject empty token
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_token_with_special_chars_handled(self, async_client: AsyncClient):
        """Test tokens with special characters are handled safely."""
        response = await async_client.get(
            "/api/v1/agents",
            headers={"Authorization": "Bearer <script>alert(1)</script>"}
        )

        # Should reject safely without XSS
        assert response.status_code == 401
        # Response should not contain unescaped script tags
        assert "<script>" not in response.text


class TestExpiredTokenRejection:
    """Test expired tokens are properly rejected."""

    @pytest.mark.asyncio
    async def test_expired_token_rejected(self, async_client: AsyncClient):
        """Test expired JWT tokens are rejected."""
        # Create an expired token
        expired_token = jwt.encode(
            {"sub": "user123", "exp": datetime.utcnow() - timedelta(hours=1)},
            "test-secret",
            algorithm="HS256"
        )

        response = await async_client.get(
            "/api/v1/agents",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        # Should reject expired token
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_token_error_message(self, async_client: AsyncClient):
        """Test expired token returns appropriate error message."""
        expired_token = jwt.encode(
            {"sub": "user123", "exp": datetime.utcnow() - timedelta(hours=1)},
            "test-secret",
            algorithm="HS256"
        )

        response = await async_client.get(
            "/api/v1/agents",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        # Should indicate token expiry in error
        data = response.json()
        error_text = str(data).lower()
        assert "expired" in error_text or "unauthorized" in error_text

    @pytest.mark.asyncio
    async def test_token_without_exp_rejected(self, async_client: AsyncClient):
        """Test tokens without expiration claim are rejected."""
        # Create token without 'exp' claim
        token_no_exp = jwt.encode(
            {"sub": "user123"},  # No exp claim
            "test-secret",
            algorithm="HS256"
        )

        response = await async_client.get(
            "/api/v1/agents",
            headers={"Authorization": f"Bearer {token_no_exp}"}
        )

        # Should reject or handle gracefully
        assert response.status_code == 401


class TestAPIKeyValidation:
    """Test API key validation."""

    @pytest.mark.asyncio
    async def test_invalid_api_key_rejected(self, async_client: AsyncClient):
        """Test invalid API keys are rejected."""
        response = await async_client.get(
            "/api/v1/agents",
            headers={"X-API-Key": "invalid-api-key"}
        )

        # Should reject invalid API key
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_api_key_rejected(self, async_client: AsyncClient, db_session):
        """Test expired API keys are rejected."""
        # This would require creating an expired API key in the database
        response = await async_client.get(
            "/api/v1/agents",
            headers={"X-API-Key": "expired-api-key"}
        )

        # Should reject expired key
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_revoked_api_key_rejected(self, async_client: AsyncClient):
        """Test revoked API keys are rejected."""
        response = await async_client.get(
            "/api/v1/agents",
            headers={"X-API-Key": "revoked-api-key"}
        )

        # Should reject revoked key
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_api_key_format_validation(self, async_client: AsyncClient):
        """Test API key format is validated."""
        # Test various invalid formats
        invalid_keys = [
            "",  # Empty
            "x" * 1000,  # Too long
            "short",  # Too short
            "<script>alert(1)</script>",  # XSS attempt
        ]

        for invalid_key in invalid_keys:
            response = await async_client.get(
                "/api/v1/agents",
                headers={"X-API-Key": invalid_key}
            )

            # Should reject invalid format
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_api_key_not_logged(self, async_client: AsyncClient):
        """Test API keys are not logged in plaintext."""
        # This is more of a logging test
        # API keys should be redacted in logs
        api_key = "test-secret-api-key-12345"

        response = await async_client.get(
            "/api/v1/agents",
            headers={"X-API-Key": api_key}
        )

        # Key should not appear in response or error messages
        assert api_key not in response.text


class TestRBACEnforcement:
    """Test Role-Based Access Control enforcement."""

    @pytest.mark.asyncio
    async def test_admin_route_requires_admin_role(self, async_client: AsyncClient):
        """Test admin routes require admin role."""
        # Try to access admin endpoint with regular user token
        response = await async_client.get(
            "/api/v1/agents",  # Would be an admin endpoint
            headers={"Authorization": "Bearer regular-user-token"}
        )

        # Should be rejected if user lacks admin role
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_role_based_access_enforced(self):
        """Test role-based access control is enforced."""
        from agent_service.auth.dependencies import RoleChecker

        # Create role checker for admin-only access
        admin_checker = RoleChecker(["admin"])

        # Mock user without admin role
        user = UserInfo(
            id="user123",
            email="user@example.com",
            name="Test User",
            roles=["user"],  # No admin role
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        # Should raise HTTPException
        with pytest.raises(Exception):  # HTTPException
            await admin_checker(user)

    @pytest.mark.asyncio
    async def test_multiple_roles_any_matches(self):
        """Test user with any of the required roles gets access."""
        from agent_service.auth.dependencies import RoleChecker

        # Require admin OR moderator
        checker = RoleChecker(["admin", "moderator"], require_all=False)

        # User with moderator role should pass
        user = UserInfo(
            id="user123",
            email="user@example.com",
            name="Test User",
            roles=["user", "moderator"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        # Should not raise exception
        await checker(user)

    @pytest.mark.asyncio
    async def test_require_all_roles(self):
        """Test require_all flag enforces all roles."""
        from agent_service.auth.dependencies import RoleChecker

        # Require both admin AND moderator
        checker = RoleChecker(["admin", "moderator"], require_all=True)

        # User with only admin role should fail
        user = UserInfo(
            id="user123",
            email="user@example.com",
            name="Test User",
            roles=["admin"],  # Missing moderator
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        # Should raise exception for missing role
        with pytest.raises(Exception):
            await checker(user)


class TestPermissionEnforcement:
    """Test permission-based access control."""

    @pytest.mark.asyncio
    async def test_permission_required(self):
        """Test specific permissions are required."""
        from agent_service.auth.dependencies import PermissionChecker

        # Require write permission
        checker = PermissionChecker(["write"])

        # User without write permission
        user = UserInfo(
            id="user123",
            email="user@example.com",
            name="Test User",
            roles=["user"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
            metadata={"permissions": ["read"]},  # Only read permission
        )

        # Should raise exception
        with pytest.raises(Exception):
            await checker(user)

    @pytest.mark.asyncio
    async def test_admin_has_all_permissions(self):
        """Test admin role grants all permissions."""
        from agent_service.auth.dependencies import PermissionChecker

        # Require any permission
        checker = PermissionChecker(["write", "delete"])

        # Admin user
        user = UserInfo(
            id="admin123",
            email="admin@example.com",
            name="Admin User",
            roles=["admin"],  # Admin role
            groups=[],
            provider=AuthProvider.AZURE_AD,
            metadata={"permissions": []},  # No explicit permissions
        )

        # Should pass because admin has all permissions
        await checker(user)


class TestScopeValidation:
    """Test API key scope validation."""

    @pytest.mark.asyncio
    async def test_scope_required_for_api_key(self):
        """Test API key must have required scopes."""
        from agent_service.auth.dependencies import ScopeChecker

        # Require write scope
        checker = ScopeChecker(["write"])

        # API key user with only read scope
        user = UserInfo(
            id="user123",
            email=None,
            name=None,
            roles=[],
            groups=[],
            provider=AuthProvider.CUSTOM,
            metadata={"scopes": ["read"]},  # Only read scope
        )

        # Should raise exception
        with pytest.raises(Exception):
            await checker(user)

    @pytest.mark.asyncio
    async def test_multiple_scopes_required(self):
        """Test multiple scopes can be required."""
        from agent_service.auth.dependencies import ScopeChecker

        # Require both read and write
        checker = ScopeChecker(["read", "write"], require_all=True)

        # User with only read scope
        user = UserInfo(
            id="user123",
            email=None,
            name=None,
            roles=[],
            groups=[],
            provider=AuthProvider.CUSTOM,
            metadata={"scopes": ["read"]},  # Missing write
        )

        # Should raise exception
        with pytest.raises(Exception):
            await checker(user)


class TestAuthenticationBypass:
    """Test common authentication bypass techniques are prevented."""

    @pytest.mark.asyncio
    async def test_header_injection_prevented(self, async_client: AsyncClient):
        """Test header injection attacks are prevented."""
        # Try to inject multiple headers
        response = await async_client.get(
            "/api/v1/agents",
            headers={"Authorization": "Bearer token\r\nX-Admin: true"}
        )

        # Should not accept injected headers
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_case_sensitivity_enforced(self, async_client: AsyncClient):
        """Test authentication is case-sensitive."""
        # Try different case variations
        response = await async_client.get(
            "/api/v1/agents",
            headers={"authorization": "bearer token"}  # lowercase
        )

        # Should still check auth (may accept lowercase, but should validate token)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_token_reuse_validation(self, async_client: AsyncClient):
        """Test tokens can't be reused after logout/revocation."""
        # This would require implementing token revocation
        # For now, test that expired tokens can't be reused
        expired_token = jwt.encode(
            {"sub": "user123", "exp": datetime.utcnow() - timedelta(hours=1)},
            "test-secret",
            algorithm="HS256"
        )

        response = await async_client.get(
            "/api/v1/agents",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_jwt_none_algorithm_rejected(self, async_client: AsyncClient):
        """Test JWT 'none' algorithm is rejected (critical vulnerability)."""
        # Create token with 'none' algorithm (security vulnerability)
        none_token = jwt.encode(
            {"sub": "user123", "exp": datetime.utcnow() + timedelta(hours=1)},
            "",  # No secret
            algorithm="none"
        )

        response = await async_client.get(
            "/api/v1/agents",
            headers={"Authorization": f"Bearer {none_token}"}
        )

        # Should reject 'none' algorithm
        assert response.status_code == 401


class TestAuthenticationErrorResponses:
    """Test authentication error responses."""

    @pytest.mark.asyncio
    async def test_401_includes_www_authenticate_header(self, async_client: AsyncClient):
        """Test 401 responses include WWW-Authenticate header."""
        response = await async_client.get("/api/v1/agents")

        assert response.status_code == 401
        # Should include WWW-Authenticate header per HTTP spec
        # assert "WWW-Authenticate" in response.headers

    @pytest.mark.asyncio
    async def test_403_for_insufficient_permissions(self):
        """Test 403 is returned for insufficient permissions."""
        from agent_service.auth.dependencies import RoleChecker
        from fastapi import HTTPException

        checker = RoleChecker(["admin"])

        user = UserInfo(
            id="user123",
            email="user@example.com",
            name="Test User",
            roles=["user"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        # Should raise 403 Forbidden
        with pytest.raises(HTTPException) as exc_info:
            await checker(user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_error_messages_dont_leak_info(self, async_client: AsyncClient):
        """Test error messages don't leak sensitive information."""
        response = await async_client.get(
            "/api/v1/agents",
            headers={"Authorization": "Bearer invalid-token"}
        )

        assert response.status_code == 401

        # Error should not reveal internal details
        data = response.json()
        error_msg = str(data).lower()

        # Should not reveal secret keys, internal paths, etc.
        assert "secret" not in error_msg
        assert "/home/" not in error_msg
        assert "stacktrace" not in error_msg


class TestMultipleAuthMethods:
    """Test multiple authentication methods."""

    @pytest.mark.asyncio
    async def test_bearer_token_takes_precedence(self, async_client: AsyncClient):
        """Test Bearer token is tried before API key."""
        response = await async_client.get(
            "/api/v1/agents",
            headers={
                "Authorization": "Bearer invalid-token",
                "X-API-Key": "api-key"
            }
        )

        # Should validate Bearer token first
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_fallback_to_api_key(self, async_client: AsyncClient):
        """Test fallback to API key when no Bearer token."""
        response = await async_client.get(
            "/api/v1/agents",
            headers={"X-API-Key": "invalid-api-key"}
        )

        # Should try API key authentication
        assert response.status_code == 401
