"""
Security test fixtures and configuration.

Provides fixtures for security testing including:
- Authenticated and unauthenticated clients
- Mock users with different roles and permissions
- API key fixtures
- Token generation utilities
"""

import pytest
from datetime import datetime, timedelta
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
import jwt

from httpx import AsyncClient
from fastapi import FastAPI

from agent_service.auth.schemas import UserInfo, AuthProvider


# ============================================================================
# Authentication Fixtures
# ============================================================================


@pytest.fixture
def valid_jwt_token(test_settings) -> str:
    """
    Generate a valid JWT token for testing.

    Returns a properly signed JWT token that would pass validation.
    """
    payload = {
        "sub": "test-user-123",
        "email": "test@example.com",
        "name": "Test User",
        "roles": ["user"],
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }

    # Use test secret key
    secret_key = test_settings.secret_key.get_secret_value() if test_settings.secret_key else "test-secret-key"

    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return token


@pytest.fixture
def expired_jwt_token(test_settings) -> str:
    """
    Generate an expired JWT token for testing.

    Returns a JWT token that expired 1 hour ago.
    """
    payload = {
        "sub": "test-user-123",
        "email": "test@example.com",
        "exp": datetime.utcnow() - timedelta(hours=1),  # Expired
        "iat": datetime.utcnow() - timedelta(hours=2),
    }

    secret_key = test_settings.secret_key.get_secret_value() if test_settings.secret_key else "test-secret-key"

    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return token


@pytest.fixture
def admin_jwt_token(test_settings) -> str:
    """
    Generate a valid JWT token with admin role.

    Returns a JWT token for a user with admin privileges.
    """
    payload = {
        "sub": "admin-user-456",
        "email": "admin@example.com",
        "name": "Admin User",
        "roles": ["user", "admin"],
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }

    secret_key = test_settings.secret_key.get_secret_value() if test_settings.secret_key else "test-secret-key"

    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return token


@pytest.fixture
def valid_api_key() -> str:
    """
    Generate a valid API key for testing.

    Returns a properly formatted API key.
    """
    return "sk_test_1234567890abcdef1234567890abcdef"


@pytest.fixture
def mock_user_regular() -> UserInfo:
    """
    Mock regular user with basic permissions.

    Returns UserInfo for a regular user.
    """
    return UserInfo(
        id="user-123",
        email="user@example.com",
        name="Regular User",
        roles=["user"],
        groups=["users"],
        provider=AuthProvider.AZURE_AD,
        metadata={
            "permissions": ["read"],
            "tier": "free",
        },
    )


@pytest.fixture
def mock_user_admin() -> UserInfo:
    """
    Mock admin user with elevated permissions.

    Returns UserInfo for an admin user.
    """
    return UserInfo(
        id="admin-456",
        email="admin@example.com",
        name="Admin User",
        roles=["user", "admin"],
        groups=["users", "admins"],
        provider=AuthProvider.AZURE_AD,
        metadata={
            "permissions": ["read", "write", "delete", "admin"],
            "tier": "enterprise",
        },
    )


@pytest.fixture
def mock_user_moderator() -> UserInfo:
    """
    Mock moderator user with intermediate permissions.

    Returns UserInfo for a moderator user.
    """
    return UserInfo(
        id="mod-789",
        email="moderator@example.com",
        name="Moderator User",
        roles=["user", "moderator"],
        groups=["users", "moderators"],
        provider=AuthProvider.AZURE_AD,
        metadata={
            "permissions": ["read", "write"],
            "tier": "pro",
        },
    )


@pytest.fixture
def mock_api_key_user() -> UserInfo:
    """
    Mock user authenticated via API key.

    Returns UserInfo for an API key authenticated user.
    """
    return UserInfo(
        id="apikey-user-999",
        email=None,  # API keys don't have email
        name=None,
        roles=["read", "write"],  # Scopes mapped to roles
        groups=[],
        provider=AuthProvider.CUSTOM,
        metadata={
            "api_key_id": "key-123",
            "rate_limit_tier": "pro",
            "scopes": ["read", "write"],
        },
    )


# ============================================================================
# HTTP Client Fixtures
# ============================================================================


@pytest.fixture
async def unauthenticated_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP client without authentication headers.

    Use this to test that endpoints properly reject unauthenticated requests.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def authenticated_client(
    app: FastAPI, valid_jwt_token: str
) -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP client with valid JWT authentication.

    Use this to test authenticated access to protected endpoints.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        client.headers.update({"Authorization": f"Bearer {valid_jwt_token}"})
        yield client


@pytest.fixture
async def admin_client(
    app: FastAPI, admin_jwt_token: str
) -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP client authenticated as admin user.

    Use this to test admin-only endpoints.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        client.headers.update({"Authorization": f"Bearer {admin_jwt_token}"})
        yield client


@pytest.fixture
async def api_key_client(
    app: FastAPI, valid_api_key: str
) -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP client authenticated with API key.

    Use this to test API key authentication.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        client.headers.update({"X-API-Key": valid_api_key})
        yield client


@pytest.fixture
async def expired_token_client(
    app: FastAPI, expired_jwt_token: str
) -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP client with expired JWT token.

    Use this to test that expired tokens are rejected.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        client.headers.update({"Authorization": f"Bearer {expired_jwt_token}"})
        yield client


# ============================================================================
# Mock Authentication Provider Fixtures
# ============================================================================


@pytest.fixture
def mock_auth_provider():
    """
    Mock authentication provider for testing.

    Returns a mock provider that can be configured to return specific users
    or raise authentication errors.
    """
    provider = MagicMock()

    # Default: return a regular user
    provider.get_user_info.return_value = UserInfo(
        id="user-123",
        email="user@example.com",
        name="Test User",
        roles=["user"],
        groups=[],
        provider=AuthProvider.AZURE_AD,
    )

    return provider


@pytest.fixture
def mock_auth_provider_invalid():
    """
    Mock authentication provider that always fails.

    Use this to test authentication failure scenarios.
    """
    provider = MagicMock()
    from agent_service.auth.exceptions import InvalidTokenError

    provider.get_user_info.side_effect = InvalidTokenError("Invalid token")

    return provider


# ============================================================================
# Security Test Helpers
# ============================================================================


@pytest.fixture
def injection_payloads() -> dict:
    """
    Common injection attack payloads for testing.

    Returns a dictionary of attack types and their payloads.
    """
    return {
        "sql_injection": [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "admin'--",
            "' UNION SELECT * FROM users--",
        ],
        "xss": [
            "<script>alert('xss')</script>",
            "<img src=x onerror='alert(1)'>",
            "<svg onload='alert(1)'>",
            "javascript:alert(1)",
        ],
        "path_traversal": [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/passwd",
            "....//....//etc/passwd",
        ],
        "null_byte": [
            "file.txt\x00.jpg",
            "user\x00admin",
            "\x00' OR '1'='1",
        ],
        "command_injection": [
            "; ls -la",
            "| cat /etc/passwd",
            "& whoami",
            "`id`",
        ],
    }


@pytest.fixture
def cors_origins() -> dict:
    """
    CORS test origins for testing.

    Returns allowed and blocked origins for CORS testing.
    """
    return {
        "allowed": [
            "http://localhost:3000",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
        ],
        "blocked": [
            "https://evil.com",
            "http://malicious.site",
            "https://phishing.example.com",
        ],
        "invalid": [
            "not-a-url",
            "ftp://invalid-protocol.com",
            "null",
            "",
        ],
    }


@pytest.fixture
def rate_limit_tier_users() -> dict:
    """
    Users with different rate limit tiers for testing.

    Returns UserInfo objects for different tier levels.
    """
    return {
        "free": UserInfo(
            id="free-user",
            email="free@example.com",
            name="Free User",
            roles=["user"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
            metadata={"tier": "free"},
        ),
        "pro": UserInfo(
            id="pro-user",
            email="pro@example.com",
            name="Pro User",
            roles=["user"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
            metadata={"tier": "pro"},
        ),
        "enterprise": UserInfo(
            id="enterprise-user",
            email="enterprise@example.com",
            name="Enterprise User",
            roles=["user", "admin"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
            metadata={"tier": "enterprise"},
        ),
    }


# ============================================================================
# Cleanup Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
async def cleanup_security_test():
    """
    Automatic cleanup after each security test.

    Ensures no test pollution between security tests.
    """
    yield

    # Cleanup after test
    # Reset any global state, clear caches, etc.
    pass
