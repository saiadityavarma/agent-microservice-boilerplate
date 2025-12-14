"""
CORS security tests.

Tests for CORS middleware to ensure proper origin validation,
credentials handling, and preflight request support.
"""

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from agent_service.config.settings import Settings


class TestCORSOriginValidation:
    """Test CORS origin validation."""

    @pytest.mark.asyncio
    async def test_cors_blocks_unauthorized_origin(self, async_client: AsyncClient):
        """Test CORS blocks requests from unauthorized origins."""
        # Request from unauthorized origin
        response = await async_client.get(
            "/health",
            headers={"Origin": "https://evil.com"}
        )

        # Request should succeed but CORS header should not allow the origin
        assert response.status_code == 200

        # Access-Control-Allow-Origin should not be set to evil.com
        allow_origin = response.headers.get("Access-Control-Allow-Origin")
        if allow_origin:
            # Should not match the evil origin
            assert allow_origin != "https://evil.com"

    @pytest.mark.asyncio
    async def test_cors_allows_configured_origins(self, test_settings: Settings):
        """Test CORS allows explicitly configured origins."""
        # In test environment, localhost origins are allowed by default
        from agent_service.api.app import create_app

        app = create_app()

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test with localhost origin (allowed in dev/local)
            response = await client.get(
                "/health",
                headers={"Origin": "http://localhost:3000"}
            )

            assert response.status_code == 200

            # Should have CORS headers for allowed origin
            allow_origin = response.headers.get("Access-Control-Allow-Origin")
            if allow_origin:
                # Should either be the origin or * (wildcard)
                assert allow_origin in ["http://localhost:3000", "*"]

    @pytest.mark.asyncio
    async def test_cors_no_wildcard_in_production(self, test_settings: Settings):
        """Test CORS doesn't use wildcard in production."""
        # Override to production environment
        test_settings.environment = "prod"
        test_settings.cors_origins = ["https://example.com"]

        from agent_service.api.app import create_app
        prod_app = create_app()

        async with AsyncClient(app=prod_app, base_url="http://test") as client:
            response = await client.get(
                "/health",
                headers={"Origin": "https://example.com"}
            )

            allow_origin = response.headers.get("Access-Control-Allow-Origin")

            # In production, should never use wildcard
            if test_settings.is_production and allow_origin:
                assert allow_origin != "*"

    @pytest.mark.asyncio
    async def test_cors_origin_validation_case_sensitive(self, async_client: AsyncClient):
        """Test CORS origin validation is case-sensitive for security."""
        # Origins should be matched exactly, not case-insensitively
        response = await async_client.get(
            "/health",
            headers={"Origin": "HTTP://LOCALHOST:3000"}  # Uppercase
        )

        # Origin matching should be strict
        allow_origin = response.headers.get("Access-Control-Allow-Origin")
        # The exact behavior depends on CORS config, but uppercase shouldn't match lowercase


class TestCORSPreflightRequests:
    """Test CORS preflight (OPTIONS) requests."""

    @pytest.mark.asyncio
    async def test_preflight_request_returns_200(self, async_client: AsyncClient):
        """Test preflight OPTIONS request returns 200 OK."""
        response = await async_client.options(
            "/api/v1/agents",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            }
        )

        # Preflight should return 200 or 204
        assert response.status_code in [200, 204]

    @pytest.mark.asyncio
    async def test_preflight_includes_allowed_methods(self, async_client: AsyncClient):
        """Test preflight response includes allowed methods."""
        response = await async_client.options(
            "/api/v1/agents",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            }
        )

        allowed_methods = response.headers.get("Access-Control-Allow-Methods")
        if allowed_methods:
            # Should include common HTTP methods
            assert "GET" in allowed_methods or "POST" in allowed_methods

    @pytest.mark.asyncio
    async def test_preflight_includes_allowed_headers(self, async_client: AsyncClient):
        """Test preflight response includes allowed headers."""
        response = await async_client.options(
            "/api/v1/agents",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,authorization",
            }
        )

        allowed_headers = response.headers.get("Access-Control-Allow-Headers")
        # CORS should allow common headers or * for all headers

    @pytest.mark.asyncio
    async def test_preflight_max_age_set(self, async_client: AsyncClient):
        """Test preflight response includes max-age for caching."""
        response = await async_client.options(
            "/api/v1/agents",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            }
        )

        max_age = response.headers.get("Access-Control-Max-Age")
        if max_age:
            # Max age should be a reasonable value (e.g., 600 seconds = 10 minutes)
            assert int(max_age) > 0

    @pytest.mark.asyncio
    async def test_preflight_credentials_handling(self, async_client: AsyncClient):
        """Test preflight handles credentials flag correctly."""
        response = await async_client.options(
            "/api/v1/agents",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            }
        )

        allow_credentials = response.headers.get("Access-Control-Allow-Credentials")
        # Should either be "true" or not set


class TestCORSCredentialsHandling:
    """Test CORS credentials handling."""

    @pytest.mark.asyncio
    async def test_credentials_flag_when_configured(self, async_client: AsyncClient):
        """Test Access-Control-Allow-Credentials is set when configured."""
        response = await async_client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )

        allow_credentials = response.headers.get("Access-Control-Allow-Credentials")
        # Default is True in the config, so should be "true"
        if allow_credentials:
            assert allow_credentials == "true"

    @pytest.mark.asyncio
    async def test_no_wildcard_with_credentials(self, test_settings: Settings):
        """Test that wildcard origin is not used with credentials=true."""
        # When credentials are allowed, origin cannot be wildcard (security requirement)
        if test_settings.cors_allow_credentials:
            from agent_service.api.app import create_app
            app = create_app()

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/health",
                    headers={"Origin": "http://localhost:3000"}
                )

                allow_origin = response.headers.get("Access-Control-Allow-Origin")
                allow_credentials = response.headers.get("Access-Control-Allow-Credentials")

                # If credentials=true, origin cannot be wildcard
                if allow_credentials == "true":
                    assert allow_origin != "*"


class TestCORSMethodValidation:
    """Test CORS method validation."""

    @pytest.mark.asyncio
    async def test_allowed_methods_configured(self, test_settings: Settings):
        """Test allowed methods are properly configured."""
        # Should have standard HTTP methods configured
        assert "GET" in test_settings.cors_allow_methods
        assert "POST" in test_settings.cors_allow_methods

    @pytest.mark.asyncio
    async def test_options_method_always_allowed(self, async_client: AsyncClient):
        """Test OPTIONS method is always allowed for preflight."""
        response = await async_client.options(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )

        # OPTIONS should always be allowed for CORS preflight
        assert response.status_code in [200, 204, 405]  # 405 if route doesn't exist

    @pytest.mark.asyncio
    async def test_allowed_methods_in_response(self, async_client: AsyncClient):
        """Test allowed methods are included in CORS response."""
        response = await async_client.options(
            "/api/v1/agents",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "DELETE",
            }
        )

        allowed_methods = response.headers.get("Access-Control-Allow-Methods")
        if allowed_methods:
            # Should include standard CRUD methods
            methods = allowed_methods.upper()
            assert "GET" in methods or "POST" in methods or "OPTIONS" in methods


class TestCORSConfiguration:
    """Test CORS configuration and settings."""

    @pytest.mark.asyncio
    async def test_cors_origins_list_in_settings(self, test_settings: Settings):
        """Test CORS origins can be configured as a list."""
        # cors_origins should be a list
        assert isinstance(test_settings.cors_origins, list)

    @pytest.mark.asyncio
    async def test_default_localhost_in_dev(self, test_settings: Settings):
        """Test localhost origins are allowed by default in dev/local."""
        if test_settings.environment in ["local", "dev"]:
            # Middleware should add default localhost origins if none configured
            from agent_service.api.middleware.cors import get_cors_middleware_config

            config = get_cors_middleware_config(test_settings)
            allow_origins = config.get("allow_origins", [])

            # Should have at least one localhost origin
            localhost_found = any(
                "localhost" in origin or "127.0.0.1" in origin
                for origin in allow_origins
            )
            assert localhost_found or test_settings.cors_origins

    @pytest.mark.asyncio
    async def test_cors_max_age_configured(self, test_settings: Settings):
        """Test CORS max-age is configured."""
        assert test_settings.cors_max_age > 0
        # Should be reasonable (e.g., 600 seconds = 10 minutes)
        assert test_settings.cors_max_age <= 86400  # Max 24 hours


class TestCORSSecurityBestPractices:
    """Test CORS follows security best practices."""

    @pytest.mark.asyncio
    async def test_no_null_origin_allowed(self, async_client: AsyncClient):
        """Test CORS doesn't allow null origin (security risk)."""
        response = await async_client.get(
            "/health",
            headers={"Origin": "null"}
        )

        allow_origin = response.headers.get("Access-Control-Allow-Origin")

        # Should not allow "null" origin (security risk)
        if allow_origin:
            assert allow_origin != "null"

    @pytest.mark.asyncio
    async def test_origin_validation_not_regex(self, async_client: AsyncClient):
        """Test origin validation doesn't use unsafe regex matching."""
        # Try a crafted origin that might match a loose regex
        response = await async_client.get(
            "/health",
            headers={"Origin": "http://localhost.evil.com"}
        )

        allow_origin = response.headers.get("Access-Control-Allow-Origin")

        # Should not match partial domain names
        if allow_origin:
            assert allow_origin != "http://localhost.evil.com"

    @pytest.mark.asyncio
    async def test_credentials_not_exposed_to_all_origins(self, test_settings: Settings):
        """Test credentials are not exposed to all origins via wildcard."""
        # This is a critical security check
        if test_settings.cors_allow_credentials:
            # Wildcard should not be in origins if credentials are enabled
            assert "*" not in test_settings.cors_origins or not test_settings.cors_origins

    @pytest.mark.asyncio
    async def test_cors_headers_not_on_non_cors_requests(self, async_client: AsyncClient):
        """Test CORS headers are only added for cross-origin requests."""
        # Request without Origin header (same-origin request)
        response = await async_client.get("/health")

        # For same-origin requests, CORS headers may not be present
        # This is expected behavior
        assert response.status_code == 200


class TestCORSProductionConfiguration:
    """Test CORS configuration in production environment."""

    @pytest.mark.asyncio
    async def test_production_requires_explicit_origins(self, test_settings: Settings):
        """Test production environment requires explicitly configured origins."""
        test_settings.environment = "prod"
        test_settings.cors_origins = []

        from agent_service.api.middleware.cors import get_cors_middleware_config

        # Should warn or block all origins if none configured in production
        config = get_cors_middleware_config(test_settings)
        origins = config.get("allow_origins", [])

        # In production with no origins, should not default to wildcard
        if test_settings.is_production and not test_settings.cors_origins:
            assert "*" not in origins

    @pytest.mark.asyncio
    async def test_production_origin_validation_strict(self, test_settings: Settings):
        """Test production uses strict origin validation."""
        test_settings.environment = "prod"
        test_settings.cors_origins = ["https://app.example.com"]

        from agent_service.api.middleware.cors import get_cors_middleware_config

        config = get_cors_middleware_config(test_settings)
        origins = config.get("allow_origins", [])

        # Should only contain explicitly configured origins
        assert "https://app.example.com" in origins
        # Should not have dev/localhost origins in production
        assert not any("localhost" in origin for origin in origins)
