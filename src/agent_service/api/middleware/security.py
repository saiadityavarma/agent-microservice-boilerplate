"""Security headers middleware."""
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from agent_service.config.settings import get_settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.

    This middleware implements defense-in-depth security by adding multiple
    security headers to protect against common web vulnerabilities:
    - MIME sniffing attacks
    - Clickjacking
    - XSS attacks
    - Man-in-the-middle attacks (via HSTS)
    - Content injection (via CSP)

    Configuration is environment-aware, with certain headers like HSTS
    only enabled in production environments.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add security headers to response."""
        settings = get_settings()

        # Process request
        response = await call_next(request)

        # Add security headers

        # Prevent MIME sniffing - forces browsers to respect Content-Type
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking - configurable frame options
        response.headers["X-Frame-Options"] = settings.security_frame_options

        # XSS filter for legacy browsers (modern browsers use CSP)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # HTTP Strict Transport Security - only in production
        # Tells browsers to only connect via HTTPS
        if settings.security_hsts_enabled and settings.is_production:
            hsts_value = f"max-age={settings.security_hsts_max_age}; includeSubDomains"
            response.headers["Strict-Transport-Security"] = hsts_value
            logger.debug("HSTS header added (production mode)")

        # Content Security Policy - configurable policy
        # Controls which resources can be loaded
        response.headers["Content-Security-Policy"] = settings.security_csp_policy

        # Referrer Policy - controls referrer information sent with requests
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy - controls browser features and APIs
        # Denies access to sensitive features by default
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        # Remove Server header to avoid information disclosure
        # This prevents revealing server implementation details
        if "Server" in response.headers:
            del response.headers["Server"]

        return response
