# tests/conftest.py
"""
Main pytest configuration and shared fixtures for all tests.

This module provides:
- Async test support (pytest-asyncio auto mode)
- FastAPI TestClient (async)
- Database session fixtures with test database and auto-rollback
- Redis mock/test fixtures
- Factory Boy integration
- Authentication fixtures (mock user, API key)
- Settings override for test environment
"""

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

from agent_service.api.app import create_app
from agent_service.config.settings import Settings, get_settings
from agent_service.infrastructure.database.connection import DatabaseManager


# ============================================================================
# Pytest Configuration
# ============================================================================

pytest_plugins = ["tests.factories.fixtures"]


def pytest_configure(config):
    """Configure pytest-asyncio to use auto mode."""
    config.option.asyncio_mode = "auto"


# ============================================================================
# Settings and Configuration
# ============================================================================

@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """
    Test settings with overrides for test environment.

    Override environment-specific settings to ensure tests run in isolation.
    Uses SQLite for testing by default (fast and doesn't require external DB).
    """
    return Settings(
        app_name="Agent Service Test",
        app_version="0.1.0-test",
        environment="local",
        debug=True,
        host="127.0.0.1",
        port=8001,
        # Use SQLite for tests (fast, no external dependencies)
        # For PostgreSQL tests, override with: postgresql+asyncpg://user:pass@localhost/test_db
        database_url="sqlite+aiosqlite:///:memory:",
        # Use fake Redis or mock
        redis_url=None,
        secret_key="test-secret-key-for-testing-only-not-for-production",
        enable_mcp=True,
        enable_a2a=True,
        enable_agui=True,
        log_level=40,  # ERROR level to reduce noise in tests
        otel_exporter_endpoint=None,
    )


@pytest.fixture(scope="session", autouse=True)
def override_settings(test_settings: Settings):
    """
    Override global settings for all tests.

    This fixture runs automatically and ensures get_settings() returns
    test settings throughout the test session.
    """
    get_settings.cache_clear()

    def _get_test_settings():
        return test_settings

    # Replace the cached function
    original = get_settings
    get_settings.__wrapped__ = _get_test_settings
    get_settings.cache_clear()

    yield

    # Restore original after tests
    get_settings.__wrapped__ = original.__wrapped__
    get_settings.cache_clear()


# ============================================================================
# Event Loop (for async tests)
# ============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create an event loop for the test session.

    This ensures all async tests share the same event loop,
    which is required for session-scoped async fixtures.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="session")
async def test_engine(test_settings: Settings):
    """
    Create test database engine.

    Uses NullPool to prevent connection pooling issues in tests.
    Creates all tables at session start and drops them at session end.
    """
    engine = create_async_engine(
        test_settings.database_url.get_secret_value(),
        poolclass=NullPool,  # Disable pooling for tests
        echo=False,  # Set to True for SQL debugging
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    yield engine

    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="session")
async def test_session_factory(test_engine):
    """Create session factory for tests."""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture
async def db_session(test_session_factory) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a database session with automatic rollback.

    Each test gets a fresh transaction that is rolled back after the test,
    ensuring test isolation and database cleanliness.

    Usage:
        async def test_something(db_session):
            user = User(name="Test")
            db_session.add(user)
            await db_session.commit()
            # ... test logic ...
    """
    async with test_session_factory() as session:
        # Begin a nested transaction
        async with session.begin():
            yield session
            # Rollback happens automatically at context exit


@pytest.fixture
async def db_manager(test_settings: Settings, test_engine) -> AsyncGenerator[DatabaseManager, None]:
    """
    Provide a configured DatabaseManager instance for tests.

    This can be used to test code that depends on the DatabaseManager.
    """
    manager = DatabaseManager()
    manager._engine = test_engine
    manager._session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    yield manager

    # Cleanup is handled by test_engine fixture


# ============================================================================
# Redis Fixtures
# ============================================================================

@pytest.fixture
def mock_redis() -> MagicMock:
    """
    Mock Redis client for tests that don't need real Redis.

    Provides basic Redis operations as mocks.

    Usage:
        def test_cache(mock_redis):
            mock_redis.get.return_value = b"cached_value"
            result = await my_cache_function()
            assert result == "cached_value"
    """
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=0)
    redis.expire = AsyncMock(return_value=True)
    redis.ping = AsyncMock(return_value=True)
    redis.close = AsyncMock()
    return redis


@pytest.fixture
async def redis_client(test_settings: Settings):
    """
    Real Redis client for integration tests.

    If redis_url is configured in test settings, this will connect to real Redis.
    Otherwise, returns a mock.

    For real Redis tests, set REDIS_URL env var:
        REDIS_URL=redis://localhost:6379/15 pytest
    """
    if test_settings.redis_url:
        try:
            import redis.asyncio as aioredis
            client = await aioredis.from_url(
                test_settings.redis_url.get_secret_value(),
                decode_responses=True,
            )
            await client.ping()
            yield client
            await client.flushdb()  # Clean up after tests
            await client.close()
        except Exception:
            # Fall back to mock if Redis is unavailable
            pytest.skip("Redis not available, skipping test")
    else:
        # Return mock if no Redis configured
        pytest.skip("Redis not configured for tests")


# ============================================================================
# FastAPI Application and Client
# ============================================================================

@pytest.fixture
def app(test_settings: Settings) -> FastAPI:
    """
    Create FastAPI application for testing.

    This creates a fresh app instance with test configuration.
    """
    return create_app()


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client for testing FastAPI endpoints.

    Usage:
        async def test_endpoint(async_client):
            response = await async_client.get("/api/v1/users")
            assert response.status_code == 200
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def authenticated_client(
    async_client: AsyncClient,
    mock_user: dict,
) -> AsyncClient:
    """
    Authenticated HTTP client with mock user token.

    Automatically includes authentication headers in all requests.

    Usage:
        async def test_protected_endpoint(authenticated_client):
            response = await authenticated_client.get("/api/v1/profile")
            assert response.status_code == 200
    """
    # Add authentication header
    async_client.headers.update({
        "Authorization": f"Bearer {mock_user['token']}"
    })
    return async_client


# ============================================================================
# Authentication Fixtures
# ============================================================================

@pytest.fixture
def mock_user() -> dict:
    """
    Mock user data for authentication tests.

    Returns a dictionary with user information and a mock JWT token.
    """
    return {
        "id": "test-user-id-123",
        "email": "test@example.com",
        "username": "testuser",
        "is_active": True,
        "is_superuser": False,
        "token": "mock-jwt-token-for-testing",
        "roles": ["user"],
    }


@pytest.fixture
def mock_admin_user() -> dict:
    """Mock admin user data for authorization tests."""
    return {
        "id": "admin-user-id-456",
        "email": "admin@example.com",
        "username": "adminuser",
        "is_active": True,
        "is_superuser": True,
        "token": "mock-admin-jwt-token",
        "roles": ["user", "admin"],
    }


@pytest.fixture
def mock_api_key() -> str:
    """
    Mock API key for API key authentication tests.

    Usage:
        async def test_api_endpoint(async_client, mock_api_key):
            response = await async_client.get(
                "/api/v1/data",
                headers={"X-API-Key": mock_api_key}
            )
    """
    return "test-api-key-12345"


@pytest.fixture
def auth_headers(mock_user: dict) -> dict:
    """
    Authentication headers for manual request building.

    Usage:
        async def test_endpoint(async_client, auth_headers):
            response = await async_client.get(
                "/api/v1/resource",
                headers=auth_headers
            )
    """
    return {
        "Authorization": f"Bearer {mock_user['token']}"
    }


@pytest.fixture
def api_key_headers(mock_api_key: str) -> dict:
    """API key headers for manual request building."""
    return {
        "X-API-Key": mock_api_key
    }


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def anyio_backend():
    """
    Configure anyio backend for async tests.

    Required by some async testing libraries.
    """
    return "asyncio"


# ============================================================================
# Cleanup and Teardown
# ============================================================================

@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """
    Automatic cleanup after each test.

    Add any global cleanup logic here that should run after every test.
    """
    yield
    # Cleanup code here (runs after each test)
    # Example: clear caches, reset singletons, etc.
    pass
