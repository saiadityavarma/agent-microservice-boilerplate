# src/agent_service/api/middleware/test_rate_limit.py
"""
Tests for rate limiting functionality.

Run with: pytest src/agent_service/api/middleware/test_rate_limit.py
"""
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from agent_service.api.middleware.rate_limit import (
    get_user_key,
    get_api_key_key,
    get_ip_key,
    get_tier_from_request,
    limiter,
    setup_rate_limiting,
)


@pytest.fixture
def app():
    """Create a test FastAPI app with rate limiting."""
    app = FastAPI()

    # Setup rate limiting
    setup_rate_limiting(app)

    # Add test routes
    @app.get("/test/ip-limit")
    @limiter.limit("5/minute")
    async def test_ip_limit(request: Request):
        return {"message": "success"}

    @app.get("/test/user-limit")
    @limiter.limit("10/minute", key_func=get_user_key)
    async def test_user_limit(request: Request):
        return {"message": "success"}

    @app.get("/test/no-limit")
    async def test_no_limit(request: Request):
        return {"message": "success"}

    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


class TestKeyFunctions:
    """Test rate limit key generation functions."""

    def test_get_ip_key(self):
        """Test IP-based key generation."""
        request = Mock(spec=Request)
        request.client.host = "192.168.1.1"

        # Mock get_remote_address
        with patch("agent_service.api.middleware.rate_limit.get_remote_address", return_value="192.168.1.1"):
            key = get_ip_key(request)
            assert key == "ip:192.168.1.1"

    def test_get_user_key_authenticated(self):
        """Test user-based key generation for authenticated user."""
        request = Mock(spec=Request)
        request.state.user = Mock(id="user123")

        key = get_user_key(request)
        assert key == "user:user123"

    def test_get_user_key_unauthenticated(self):
        """Test user-based key generation falls back to IP."""
        request = Mock(spec=Request)
        request.state = Mock()
        delattr(request.state, "user")  # No user attribute
        request.client.host = "192.168.1.1"

        with patch("agent_service.api.middleware.rate_limit.get_remote_address", return_value="192.168.1.1"):
            key = get_user_key(request)
            assert key == "ip:192.168.1.1"

    def test_get_api_key_key_bearer_token(self):
        """Test API key-based key generation with Bearer token."""
        request = Mock(spec=Request)
        request.headers = {"Authorization": "Bearer sk_test_1234567890abcdef"}

        key = get_api_key_key(request)
        assert key == "api_key:sk_test_12345678"

    def test_get_api_key_key_x_api_key_header(self):
        """Test API key-based key generation with X-API-Key header."""
        request = Mock(spec=Request)
        request.headers = {
            "Authorization": "",
            "X-API-Key": "sk_test_1234567890abcdef"
        }

        key = get_api_key_key(request)
        assert key == "api_key:sk_test_12345678"

    def test_get_api_key_key_fallback(self):
        """Test API key-based key generation falls back to IP."""
        request = Mock(spec=Request)
        request.headers = {}
        request.client.host = "192.168.1.1"

        with patch("agent_service.api.middleware.rate_limit.get_remote_address", return_value="192.168.1.1"):
            key = get_api_key_key(request)
            assert key == "ip:192.168.1.1"


class TestTierExtraction:
    """Test tier extraction from request."""

    @patch("agent_service.api.middleware.rate_limit.get_settings")
    def test_get_tier_from_user(self, mock_get_settings):
        """Test tier extraction from authenticated user."""
        mock_settings = Mock()
        mock_settings.rate_limit_default_tier = "free"
        mock_get_settings.return_value = mock_settings

        request = Mock(spec=Request)
        request.state.user = Mock(tier="pro")

        tier = get_tier_from_request(request)
        assert tier == "pro"

    @patch("agent_service.api.middleware.rate_limit.get_settings")
    def test_get_tier_from_api_key(self, mock_get_settings):
        """Test tier extraction from API key metadata."""
        mock_settings = Mock()
        mock_settings.rate_limit_default_tier = "free"
        mock_get_settings.return_value = mock_settings

        request = Mock(spec=Request)
        request.state = Mock()
        delattr(request.state, "user")  # No user
        request.state.api_key_meta = Mock(tier="enterprise")

        tier = get_tier_from_request(request)
        assert tier == "enterprise"

    @patch("agent_service.api.middleware.rate_limit.get_settings")
    def test_get_tier_default(self, mock_get_settings):
        """Test default tier when no user or API key."""
        mock_settings = Mock()
        mock_settings.rate_limit_default_tier = "free"
        mock_get_settings.return_value = mock_settings

        request = Mock(spec=Request)
        request.state = Mock()

        tier = get_tier_from_request(request)
        assert tier == "free"


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_ip_rate_limit_allows_requests(self, client):
        """Test that requests within limit are allowed."""
        # Make 5 requests (within limit)
        for i in range(5):
            response = client.get("/test/ip-limit")
            assert response.status_code == 200
            assert response.json() == {"message": "success"}

            # Check rate limit headers
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers

    def test_ip_rate_limit_blocks_excess(self, client):
        """Test that requests exceeding limit are blocked."""
        # Make 5 requests (at limit)
        for i in range(5):
            response = client.get("/test/ip-limit")
            assert response.status_code == 200

        # 6th request should be rate limited
        response = client.get("/test/ip-limit")
        assert response.status_code == 429
        assert "rate_limit_exceeded" in response.json()["error"]

    def test_no_limit_endpoint(self, client):
        """Test that endpoints without limit are not rate limited."""
        # Make many requests
        for i in range(20):
            response = client.get("/test/no-limit")
            assert response.status_code == 200

    def test_rate_limit_headers(self, client):
        """Test that rate limit headers are present."""
        response = client.get("/test/ip-limit")
        assert response.status_code == 200

        # Check all expected headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_rate_limit_error_format(self, client):
        """Test that 429 error has correct format."""
        # Exceed rate limit
        for i in range(6):
            client.get("/test/ip-limit")

        response = client.get("/test/ip-limit")
        assert response.status_code == 429

        data = response.json()
        assert "error" in data
        assert "message" in data
        assert data["error"] == "rate_limit_exceeded"


class TestConfiguration:
    """Test rate limiting configuration."""

    @patch("agent_service.api.middleware.rate_limit.get_settings")
    def test_disabled_rate_limiting(self, mock_get_settings):
        """Test that rate limiting can be disabled."""
        mock_settings = Mock()
        mock_settings.rate_limit_enabled = False
        mock_get_settings.return_value = mock_settings

        app = FastAPI()
        setup_rate_limiting(app)

        # Limiter should not be added when disabled
        assert not hasattr(app.state, "limiter")


# Integration test example (requires Redis)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_integration():
    """
    Test rate limiting with actual Redis.

    Requires Redis to be running locally.
    Skip this test in CI if Redis is not available.
    """
    from agent_service.infrastructure.cache.redis import get_redis, close_redis

    # Initialize Redis
    redis = await get_redis()

    if redis is None:
        pytest.skip("Redis not available")

    try:
        # Test basic Redis operations
        await redis.set("test_key", "test_value", ex=60)
        value = await redis.get("test_key")
        assert value == "test_value"

        # Test rate limit counter
        key = "rate_limit:test:192.168.1.1"
        await redis.incr(key)
        await redis.expire(key, 60)

        count = await redis.get(key)
        assert int(count) == 1

    finally:
        # Cleanup
        await redis.delete("test_key")
        await redis.delete("rate_limit:test:192.168.1.1")
        await close_redis()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
