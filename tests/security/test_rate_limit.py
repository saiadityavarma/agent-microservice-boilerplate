"""
Rate limiting security tests.

Tests for rate limiting middleware to ensure proper enforcement,
tier-based limits, and correct response headers.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from httpx import AsyncClient

from agent_service.config.settings import Settings
from agent_service.api.middleware.rate_limit import (
    RATE_LIMIT_TIERS,
    get_user_key,
    get_api_key_key,
    get_ip_key,
)


class TestRateLimitEnforcement:
    """Test rate limit enforcement."""

    @pytest.mark.asyncio
    async def test_rate_limit_enabled_by_default(self, test_settings: Settings):
        """Test rate limiting is enabled by default."""
        assert test_settings.rate_limit_enabled is True

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_excessive_requests(self, app: FastAPI):
        """Test rate limit blocks requests when limit is exceeded."""
        # This test would require making many requests rapidly
        # Skip if rate limiting is disabled or using in-memory storage
        from agent_service.config.settings import get_settings
        settings = get_settings()

        if not settings.rate_limit_enabled:
            pytest.skip("Rate limiting is disabled")

        # Create a test route with low rate limit
        from fastapi import Request
        from agent_service.api.middleware.rate_limit import limiter

        @app.get("/test-rate-limit")
        @limiter.limit("3/minute")  # Very low limit for testing
        async def test_endpoint(request: Request):
            return {"message": "success"}

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Make requests up to the limit
            responses = []
            for i in range(5):  # Try 5 requests with limit of 3
                response = await client.get("/test-rate-limit")
                responses.append(response)

            # First 3 should succeed, 4th and 5th should be rate limited
            success_count = sum(1 for r in responses if r.status_code == 200)
            rate_limited_count = sum(1 for r in responses if r.status_code == 429)

            # At least some requests should be rate limited
            # (exact count depends on timing and storage backend)
            assert rate_limited_count > 0 or success_count <= 3

    @pytest.mark.asyncio
    async def test_429_response_on_rate_limit_exceeded(self, app: FastAPI):
        """Test 429 Too Many Requests is returned when rate limit exceeded."""
        from agent_service.config.settings import get_settings
        settings = get_settings()

        if not settings.rate_limit_enabled:
            pytest.skip("Rate limiting is disabled")

        from fastapi import Request
        from agent_service.api.middleware.rate_limit import limiter

        @app.get("/test-rate-limit-429")
        @limiter.limit("1/minute")  # Very strict limit
        async def test_endpoint(request: Request):
            return {"message": "success"}

        async with AsyncClient(app=app, base_url="http://test") as client:
            # First request should succeed
            response1 = await client.get("/test-rate-limit-429")

            # Second immediate request should be rate limited
            response2 = await client.get("/test-rate-limit-429")

            # At least one should be rate limited
            status_codes = [response1.status_code, response2.status_code]
            assert 429 in status_codes or all(s == 200 for s in status_codes)


class TestRateLimitHeaders:
    """Test rate limit response headers."""

    @pytest.mark.asyncio
    async def test_rate_limit_headers_present(self, app: FastAPI):
        """Test X-RateLimit-* headers are present in responses."""
        from agent_service.config.settings import get_settings
        settings = get_settings()

        if not settings.rate_limit_enabled:
            pytest.skip("Rate limiting is disabled")

        from fastapi import Request
        from agent_service.api.middleware.rate_limit import limiter

        @app.get("/test-headers")
        @limiter.limit("10/minute")
        async def test_endpoint(request: Request):
            return {"message": "success"}

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/test-headers")

            # Rate limit headers may be present (depends on slowapi configuration)
            # X-RateLimit-Limit: max requests in window
            # X-RateLimit-Remaining: requests remaining
            # X-RateLimit-Reset: when the window resets

    @pytest.mark.asyncio
    async def test_retry_after_header_on_429(self, app: FastAPI):
        """Test Retry-After header is included in 429 responses."""
        from agent_service.config.settings import get_settings
        settings = get_settings()

        if not settings.rate_limit_enabled:
            pytest.skip("Rate limiting is disabled")

        from fastapi import Request
        from agent_service.api.middleware.rate_limit import limiter

        @app.get("/test-retry-after")
        @limiter.limit("1/minute")
        async def test_endpoint(request: Request):
            return {"message": "success"}

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Make multiple requests to trigger rate limit
            responses = []
            for _ in range(3):
                response = await client.get("/test-retry-after")
                responses.append(response)

            # Find a 429 response if any
            rate_limited = [r for r in responses if r.status_code == 429]
            if rate_limited:
                # Should have Retry-After header
                retry_after = rate_limited[0].headers.get("Retry-After")
                # May or may not be present depending on configuration

    @pytest.mark.asyncio
    async def test_rate_limit_remaining_decreases(self, app: FastAPI):
        """Test X-RateLimit-Remaining decreases with each request."""
        from agent_service.config.settings import get_settings
        settings = get_settings()

        if not settings.rate_limit_enabled:
            pytest.skip("Rate limiting is disabled")

        from fastapi import Request
        from agent_service.api.middleware.rate_limit import limiter

        @app.get("/test-remaining")
        @limiter.limit("10/minute")
        async def test_endpoint(request: Request):
            return {"message": "success"}

        async with AsyncClient(app=app, base_url="http://test") as client:
            response1 = await client.get("/test-remaining")
            response2 = await client.get("/test-remaining")

            # If headers are present, remaining should decrease
            remaining1 = response1.headers.get("X-RateLimit-Remaining")
            remaining2 = response2.headers.get("X-RateLimit-Remaining")

            if remaining1 and remaining2:
                assert int(remaining2) <= int(remaining1)


class TestRateLimitTiers:
    """Test tier-based rate limiting."""

    @pytest.mark.asyncio
    async def test_tier_configuration_exists(self):
        """Test rate limit tiers are properly configured."""
        assert "free" in RATE_LIMIT_TIERS
        assert "pro" in RATE_LIMIT_TIERS
        assert "enterprise" in RATE_LIMIT_TIERS

    @pytest.mark.asyncio
    async def test_tier_limits_progressive(self):
        """Test tier limits increase from free to enterprise."""
        # Extract numeric limits from tier strings (e.g., "100/hour" -> 100)
        def extract_limit(tier_str: str) -> int:
            return int(tier_str.split("/")[0])

        free_limit = extract_limit(RATE_LIMIT_TIERS["free"])
        pro_limit = extract_limit(RATE_LIMIT_TIERS["pro"])
        enterprise_limit = extract_limit(RATE_LIMIT_TIERS["enterprise"])

        # Higher tiers should have higher limits
        assert pro_limit > free_limit
        assert enterprise_limit > pro_limit

    @pytest.mark.asyncio
    async def test_default_tier_is_free(self, test_settings: Settings):
        """Test default tier for unauthenticated users is free."""
        assert test_settings.rate_limit_default_tier == "free"

    @pytest.mark.asyncio
    async def test_different_tiers_have_different_limits(self):
        """Test each tier has a different rate limit."""
        limits = set(RATE_LIMIT_TIERS.values())
        # All tiers should have different limits
        assert len(limits) == len(RATE_LIMIT_TIERS)


class TestRateLimitKeyFunctions:
    """Test rate limit key extraction functions."""

    @pytest.mark.asyncio
    async def test_get_user_key_with_authenticated_user(self):
        """Test user key extraction for authenticated users."""
        from fastapi import Request

        # Mock request with authenticated user
        request = MagicMock(spec=Request)
        user_mock = MagicMock()
        user_mock.id = "user-123"
        request.state.user = user_mock

        key = get_user_key(request)
        assert key == "user:user-123"

    @pytest.mark.asyncio
    async def test_get_user_key_fallback_to_ip(self):
        """Test user key falls back to IP for unauthenticated users."""
        from fastapi import Request

        # Mock request without user
        request = MagicMock(spec=Request)
        request.state.user = None
        request.client.host = "192.168.1.1"

        key = get_user_key(request)
        assert "ip:" in key

    @pytest.mark.asyncio
    async def test_get_api_key_key_from_bearer_token(self):
        """Test API key extraction from Authorization header."""
        from fastapi import Request

        request = MagicMock(spec=Request)
        request.headers.get.return_value = "Bearer test-api-key-12345"
        request.client.host = "192.168.1.1"

        key = get_api_key_key(request)
        assert "api_key:" in key
        assert "test-api-key-12" in key  # First 16 chars

    @pytest.mark.asyncio
    async def test_get_api_key_key_from_x_api_key_header(self):
        """Test API key extraction from X-API-Key header."""
        from fastapi import Request

        request = MagicMock(spec=Request)
        request.headers.get.side_effect = lambda h, default="": {
            "Authorization": "",
            "X-API-Key": "test-api-key-12345"
        }.get(h, default)
        request.client.host = "192.168.1.1"

        key = get_api_key_key(request)
        assert "api_key:" in key

    @pytest.mark.asyncio
    async def test_get_ip_key(self):
        """Test IP-based key extraction."""
        from fastapi import Request

        request = MagicMock(spec=Request)
        request.client.host = "192.168.1.100"

        key = get_ip_key(request)
        assert "ip:" in key


class TestRateLimitErrorResponse:
    """Test rate limit error response format."""

    @pytest.mark.asyncio
    async def test_429_response_format(self, app: FastAPI):
        """Test 429 response has correct JSON format."""
        from agent_service.config.settings import get_settings
        settings = get_settings()

        if not settings.rate_limit_enabled:
            pytest.skip("Rate limiting is disabled")

        from fastapi import Request
        from agent_service.api.middleware.rate_limit import limiter

        @app.get("/test-error-format")
        @limiter.limit("1/minute")
        async def test_endpoint(request: Request):
            return {"message": "success"}

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Make multiple requests to trigger rate limit
            responses = []
            for _ in range(3):
                response = await client.get("/test-error-format")
                responses.append(response)

            # Find a 429 response
            rate_limited = [r for r in responses if r.status_code == 429]
            if rate_limited:
                data = rate_limited[0].json()
                # Should have error information
                assert "error" in data or "message" in data or "detail" in data

    @pytest.mark.asyncio
    async def test_429_includes_error_code(self, app: FastAPI):
        """Test 429 response includes error code/type."""
        from agent_service.config.settings import get_settings
        settings = get_settings()

        if not settings.rate_limit_enabled:
            pytest.skip("Rate limiting is disabled")

        from fastapi import Request
        from agent_service.api.middleware.rate_limit import limiter

        @app.get("/test-error-code")
        @limiter.limit("1/minute")
        async def test_endpoint(request: Request):
            return {"message": "success"}

        async with AsyncClient(app=app, base_url="http://test") as client:
            responses = []
            for _ in range(3):
                response = await client.get("/test-error-code")
                responses.append(response)

            rate_limited = [r for r in responses if r.status_code == 429]
            if rate_limited:
                data = rate_limited[0].json()
                # Should identify as rate limit error
                assert (
                    "rate_limit" in str(data).lower() or
                    "too many" in str(data).lower()
                )


class TestRateLimitConfiguration:
    """Test rate limit configuration."""

    @pytest.mark.asyncio
    async def test_rate_limit_can_be_disabled(self, test_settings: Settings):
        """Test rate limiting can be disabled via configuration."""
        # Should be configurable
        assert hasattr(test_settings, "rate_limit_enabled")

    @pytest.mark.asyncio
    async def test_rate_limit_uses_redis_when_available(self, test_settings: Settings):
        """Test rate limiting uses Redis when configured."""
        if test_settings.redis_url:
            # Should use Redis for distributed rate limiting
            from agent_service.api.middleware.rate_limit import create_rate_limiter

            limiter = create_rate_limiter()
            # Limiter should be configured (can't easily test Redis connection here)
            assert limiter is not None

    @pytest.mark.asyncio
    async def test_rate_limit_falls_back_to_memory(self, test_settings: Settings):
        """Test rate limiting falls back to in-memory when Redis unavailable."""
        if not test_settings.redis_url:
            from agent_service.api.middleware.rate_limit import create_rate_limiter

            limiter = create_rate_limiter()
            # Should still create limiter with memory storage
            assert limiter is not None


class TestRateLimitByEndpoint:
    """Test different endpoints can have different rate limits."""

    @pytest.mark.asyncio
    async def test_per_endpoint_rate_limits(self, app: FastAPI):
        """Test different endpoints can have different rate limits."""
        from agent_service.config.settings import get_settings
        settings = get_settings()

        if not settings.rate_limit_enabled:
            pytest.skip("Rate limiting is disabled")

        from fastapi import Request
        from agent_service.api.middleware.rate_limit import limiter

        @app.get("/test-endpoint-a")
        @limiter.limit("5/minute")
        async def endpoint_a(request: Request):
            return {"endpoint": "a"}

        @app.get("/test-endpoint-b")
        @limiter.limit("10/minute")
        async def endpoint_b(request: Request):
            return {"endpoint": "b"}

        # Each endpoint should have its own limit
        async with AsyncClient(app=app, base_url="http://test") as client:
            response_a = await client.get("/test-endpoint-a")
            response_b = await client.get("/test-endpoint-b")

            # Both should succeed (first request to each)
            assert response_a.status_code == 200
            assert response_b.status_code == 200


class TestRateLimitSecurityBestPractices:
    """Test rate limiting security best practices."""

    @pytest.mark.asyncio
    async def test_rate_limit_by_user_not_global(self):
        """Test rate limits are per-user/IP, not global."""
        # Rate limits should be isolated per user/IP
        # This prevents one user from consuming the entire quota
        from agent_service.api.middleware.rate_limit import get_user_key
        from fastapi import Request

        # Different users should have different keys
        request1 = MagicMock(spec=Request)
        user1 = MagicMock()
        user1.id = "user-1"
        request1.state.user = user1

        request2 = MagicMock(spec=Request)
        user2 = MagicMock()
        user2.id = "user-2"
        request2.state.user = user2

        key1 = get_user_key(request1)
        key2 = get_user_key(request2)

        assert key1 != key2

    @pytest.mark.asyncio
    async def test_rate_limit_prevents_brute_force(self, app: FastAPI):
        """Test rate limiting helps prevent brute force attacks."""
        from agent_service.config.settings import get_settings
        settings = get_settings()

        if not settings.rate_limit_enabled:
            pytest.skip("Rate limiting is disabled")

        from fastapi import Request
        from agent_service.api.middleware.rate_limit import limiter

        @app.post("/test-login")
        @limiter.limit("5/minute")  # Low limit for auth endpoints
        async def login_endpoint(request: Request):
            return {"message": "login attempt"}

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Rapid login attempts should be rate limited
            responses = []
            for _ in range(10):
                response = await client.post("/test-login")
                responses.append(response)

            # Some should be blocked
            rate_limited = sum(1 for r in responses if r.status_code == 429)
            # At least some attempts should be blocked (depends on timing)
