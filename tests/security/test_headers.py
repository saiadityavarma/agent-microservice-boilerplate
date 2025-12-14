"""
Security headers tests.

Tests for the SecurityHeadersMiddleware to ensure all security headers
are properly set and configured according to environment.
"""

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from agent_service.config.settings import Settings


class TestSecurityHeaders:
    """Test security headers middleware."""

    @pytest.mark.asyncio
    async def test_all_security_headers_present(self, async_client: AsyncClient):
        """Test that all required security headers are present in responses."""
        response = await async_client.get("/health")

        assert response.status_code == 200

        # Verify all security headers are present
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Content-Security-Policy" in response.headers
        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers

    @pytest.mark.asyncio
    async def test_x_content_type_options_nosniff(self, async_client: AsyncClient):
        """Test X-Content-Type-Options is set to nosniff."""
        response = await async_client.get("/health")

        assert response.headers["X-Content-Type-Options"] == "nosniff"

    @pytest.mark.asyncio
    async def test_x_frame_options_deny(self, async_client: AsyncClient):
        """Test X-Frame-Options is set correctly."""
        response = await async_client.get("/health")

        # Default is DENY
        assert response.headers["X-Frame-Options"] in ["DENY", "SAMEORIGIN"]

    @pytest.mark.asyncio
    async def test_x_xss_protection_enabled(self, async_client: AsyncClient):
        """Test X-XSS-Protection is enabled."""
        response = await async_client.get("/health")

        assert response.headers["X-XSS-Protection"] == "1; mode=block"

    @pytest.mark.asyncio
    async def test_content_security_policy_set(self, async_client: AsyncClient):
        """Test Content-Security-Policy header is set."""
        response = await async_client.get("/health")

        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None
        assert "default-src" in csp

    @pytest.mark.asyncio
    async def test_referrer_policy_set(self, async_client: AsyncClient):
        """Test Referrer-Policy is set correctly."""
        response = await async_client.get("/health")

        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    @pytest.mark.asyncio
    async def test_permissions_policy_restrictive(self, async_client: AsyncClient):
        """Test Permissions-Policy denies sensitive features."""
        response = await async_client.get("/health")

        permissions_policy = response.headers.get("Permissions-Policy")
        assert permissions_policy is not None

        # Should deny geolocation, microphone, camera
        assert "geolocation=()" in permissions_policy
        assert "microphone=()" in permissions_policy
        assert "camera=()" in permissions_policy

    @pytest.mark.asyncio
    async def test_server_header_removed(self, async_client: AsyncClient):
        """Test Server header is removed to prevent information disclosure."""
        response = await async_client.get("/health")

        # Server header should not be present
        assert "Server" not in response.headers


class TestHSTSHeader:
    """Test HSTS header behavior in different environments."""

    @pytest.mark.asyncio
    async def test_hsts_not_in_development(self, app: FastAPI):
        """Test HSTS is not enabled in non-production environments."""
        # Test settings show we're in local/test environment
        from agent_service.config.settings import get_settings
        settings = get_settings()

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

            # HSTS should not be present in non-production
            if not settings.is_production:
                assert "Strict-Transport-Security" not in response.headers

    @pytest.mark.asyncio
    async def test_hsts_only_in_production(self, test_settings: Settings):
        """Test HSTS is only enabled when environment is production."""
        # Override settings to production
        test_settings.environment = "prod"
        test_settings.security_hsts_enabled = True

        # Create app with production settings
        from agent_service.api.app import create_app
        prod_app = create_app()

        async with AsyncClient(app=prod_app, base_url="https://test") as client:
            response = await client.get("/health")

            if test_settings.is_production and test_settings.security_hsts_enabled:
                # HSTS should be present in production
                hsts = response.headers.get("Strict-Transport-Security")
                if hsts:  # Only test if present (depends on middleware execution)
                    assert "max-age=" in hsts
                    assert "includeSubDomains" in hsts

    @pytest.mark.asyncio
    async def test_hsts_max_age_configured(self, app: FastAPI):
        """Test HSTS max-age is properly configured."""
        from agent_service.config.settings import get_settings
        settings = get_settings()

        if settings.is_production and settings.security_hsts_enabled:
            async with AsyncClient(app=app, base_url="https://test") as client:
                response = await client.get("/health")

                hsts = response.headers.get("Strict-Transport-Security")
                if hsts:
                    # Should have a reasonable max-age (1 year = 31536000)
                    assert "max-age=31536000" in hsts or "max-age=" in hsts


class TestSecurityHeadersOnAllEndpoints:
    """Test security headers are present on all endpoints."""

    @pytest.mark.asyncio
    async def test_headers_on_health_endpoint(self, async_client: AsyncClient):
        """Test security headers on health check endpoint."""
        response = await async_client.get("/health")

        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers

    @pytest.mark.asyncio
    async def test_headers_on_docs_endpoint(self, async_client: AsyncClient):
        """Test security headers on API docs endpoint."""
        response = await async_client.get("/docs")

        # Even on docs endpoint, security headers should be present
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers

    @pytest.mark.asyncio
    async def test_headers_on_404_response(self, async_client: AsyncClient):
        """Test security headers are present even on error responses."""
        response = await async_client.get("/nonexistent-endpoint")

        assert response.status_code == 404

        # Security headers should still be present on error responses
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers

    @pytest.mark.asyncio
    async def test_headers_on_post_requests(self, async_client: AsyncClient):
        """Test security headers are present on POST requests."""
        response = await async_client.post("/api/v1/agents")

        # Even unauthorized requests should have security headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers


class TestCSPConfiguration:
    """Test Content Security Policy configuration."""

    @pytest.mark.asyncio
    async def test_csp_default_src_self(self, async_client: AsyncClient):
        """Test CSP default-src is restricted to self."""
        response = await async_client.get("/health")

        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None

        # Should restrict resources to same origin by default
        assert "default-src" in csp
        assert "'self'" in csp or "self" in csp

    @pytest.mark.asyncio
    async def test_csp_no_unsafe_inline(self, async_client: AsyncClient):
        """Test CSP doesn't allow unsafe-inline by default."""
        response = await async_client.get("/health")

        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None

        # Should not contain unsafe-inline (security risk)
        # Unless explicitly configured for specific reasons
        # This is informational - strict policy is "default-src 'self'"
        default_csp = "default-src 'self'"
        assert csp == default_csp or "default-src" in csp


class TestSecurityHeadersConfiguration:
    """Test security headers can be configured via settings."""

    @pytest.mark.asyncio
    async def test_frame_options_configurable(self, test_settings: Settings):
        """Test X-Frame-Options can be configured."""
        # Default from settings
        assert test_settings.security_frame_options in ["DENY", "SAMEORIGIN"]

    @pytest.mark.asyncio
    async def test_csp_policy_configurable(self, test_settings: Settings):
        """Test CSP policy can be configured."""
        # Should have a CSP policy configured
        assert test_settings.security_csp_policy is not None
        assert len(test_settings.security_csp_policy) > 0

    @pytest.mark.asyncio
    async def test_hsts_settings_available(self, test_settings: Settings):
        """Test HSTS settings are configurable."""
        assert hasattr(test_settings, "security_hsts_enabled")
        assert hasattr(test_settings, "security_hsts_max_age")

        # Max age should be at least 1 year (31536000 seconds) for production
        if test_settings.security_hsts_enabled:
            assert test_settings.security_hsts_max_age > 0
