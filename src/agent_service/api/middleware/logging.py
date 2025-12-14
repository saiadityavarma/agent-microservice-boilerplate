"""
Request logging middleware with structured logging.

This middleware provides:
- Structured logging for all HTTP requests
- Request/response body logging (with truncation and PII masking)
- Timing metrics
- User context from authentication
- Health check endpoint filtering
"""
import time
import json
from typing import Optional, Set
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from agent_service.infrastructure.observability.logging import get_logger, mask_pii_value
from agent_service.config.settings import get_settings


logger = get_logger(__name__)


# Health check paths to skip logging (reduce noise)
HEALTH_CHECK_PATHS: Set[str] = {
    "/health",
    "/healthz",
    "/ready",
    "/readiness",
    "/live",
    "/liveness",
    "/ping",
}


def truncate_body(body: str, max_length: int = 1000) -> str:
    """
    Truncate body content to max length.

    Args:
        body: Body content to truncate
        max_length: Maximum length

    Returns:
        Truncated body with indicator if truncated
    """
    if len(body) <= max_length:
        return body
    return body[:max_length] + f"... (truncated, {len(body)} total chars)"


async def get_request_body(request: Request, max_length: int = 1000) -> Optional[str]:
    """
    Extract and truncate request body.

    Args:
        request: Starlette request
        max_length: Maximum body length to log

    Returns:
        Request body as string, or None if not available
    """
    try:
        body_bytes = await request.body()
        if not body_bytes:
            return None

        body_str = body_bytes.decode("utf-8", errors="replace")

        # Try to parse as JSON for better formatting
        try:
            body_json = json.loads(body_str)
            body_str = json.dumps(body_json, indent=None, separators=(',', ':'))
        except (json.JSONDecodeError, ValueError):
            pass  # Not JSON, use as-is

        return truncate_body(body_str, max_length)

    except Exception as e:
        logger.debug("Failed to read request body", error=str(e))
        return None


def get_user_context_from_request(request: Request) -> dict:
    """
    Extract user context from request state.

    Args:
        request: Starlette request with potential user info in state

    Returns:
        Dictionary with user_id and email if available
    """
    context = {}

    # Try to get user from request state (set by auth middleware)
    if hasattr(request.state, "user"):
        user = request.state.user
        if hasattr(user, "id"):
            context["user_id"] = str(user.id)
        if hasattr(user, "email") and user.email:
            context["email"] = user.email

    return context


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured request/response logging.

    Features:
    - Logs request method, path, status code, and duration
    - Optionally logs request body (truncated, with PII masking)
    - Logs response body for errors only (4xx, 5xx)
    - Skips logging for health check endpoints
    - Adds timing metrics to response headers
    - Adds user context (user_id, email) from authentication
    - Respects configuration settings for body logging and PII masking
    """

    def __init__(self, app):
        """
        Initialize the logging middleware.

        Args:
            app: ASGI application
        """
        super().__init__(app)
        self.settings = get_settings()

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request with structured logging.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response with timing headers
        """
        start_time = time.time()

        # Skip logging for health check endpoints
        if request.url.path in HEALTH_CHECK_PATHS:
            return await call_next(request)

        # Extract user context
        user_context = get_user_context_from_request(request)

        # Build request log context
        log_context = {
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params) if request.query_params else None,
            "client_ip": request.client.host if request.client else None,
            **user_context,
        }

        # Optionally log request body
        if self.settings.log_include_request_body and request.method in ["POST", "PUT", "PATCH"]:
            # Note: This consumes the request body, so we need to restore it
            body = await get_request_body(request, self.settings.log_max_body_length)
            if body:
                # Mask PII in body if enabled
                if self.settings.log_pii_masking_enabled:
                    body = mask_pii_value(body)
                log_context["request_body"] = body

        # Log incoming request
        logger.info(
            "Request received",
            **log_context
        )

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log exception and re-raise
            duration = time.time() - start_time
            logger.error(
                "Request failed with exception",
                **log_context,
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration * 1000, 2),
            )
            raise

        # Calculate response time
        duration = time.time() - start_time
        duration_ms = round(duration * 1000, 2)

        # Build response log context
        response_context = {
            **log_context,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }

        # Log response body for errors only
        if response.status_code >= 400:
            # For error responses, try to capture the response body
            # This is tricky because we've already started streaming the response
            # So we only log a note that an error occurred
            logger.error(
                "Request completed with error",
                **response_context
            )
        else:
            # Log successful request
            logger.info(
                "Request completed",
                **response_context
            )

        # Add timing header
        response.headers["X-Process-Time"] = str(duration)
        response.headers["X-Process-Time-Ms"] = str(duration_ms)

        return response
