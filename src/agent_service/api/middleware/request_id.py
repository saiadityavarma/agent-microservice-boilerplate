"""
Request ID and correlation tracking middleware.

Provides unique request identification for distributed tracing and log correlation.
"""
import uuid
import functools
import inspect
from contextvars import ContextVar
from typing import Callable, Any, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog

# Context variable for request ID (accessible in non-request contexts)
request_id_var: ContextVar[str] = ContextVar("request_id", default=None)
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default=None)

logger = structlog.get_logger(__name__)


def is_valid_uuid(value: str) -> bool:
    """
    Validate if a string is a valid UUID4.

    Args:
        value: String to validate

    Returns:
        True if valid UUID4, False otherwise
    """
    try:
        uuid_obj = uuid.UUID(value, version=4)
        # Ensure it's actually a UUID4 (not just any UUID)
        return str(uuid_obj) == value and uuid_obj.version == 4
    except (ValueError, AttributeError):
        return False


def get_request_id() -> Optional[str]:
    """
    Get current request ID from context.

    Returns:
        Request ID if available, None otherwise
    """
    return request_id_var.get(None)


def set_request_id(request_id: str) -> None:
    """
    Set request ID in context (for background tasks).

    Args:
        request_id: Request ID to set
    """
    request_id_var.set(request_id)


def get_correlation_id() -> Optional[str]:
    """
    Get current correlation ID from context.

    Returns:
        Correlation ID if available, None otherwise
    """
    return correlation_id_var.get(None)


def set_correlation_id(correlation_id: str) -> None:
    """
    Set correlation ID in context.

    Args:
        correlation_id: Correlation ID to set
    """
    correlation_id_var.set(correlation_id)


def add_request_id_to_log(
    logger: Any, method_name: str, event_dict: dict
) -> dict:
    """
    Structlog processor to add request ID and correlation ID to log entries.

    This processor automatically adds request_id and correlation_id to all
    log entries when available in the context.

    Args:
        logger: Logger instance
        method_name: Name of the log method
        event_dict: Log event dictionary

    Returns:
        Modified event dictionary with request_id and correlation_id
    """
    request_id = get_request_id()
    if request_id:
        event_dict["request_id"] = request_id

    correlation_id = get_correlation_id()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id

    return event_dict


def preserve_request_id(func: Callable) -> Callable:
    """
    Decorator to preserve request ID in background tasks and async operations.

    This ensures that async tasks spawned from a request maintain the same
    request ID for proper log correlation.

    Usage:
        @preserve_request_id
        async def background_task():
            logger.info("This will have the request_id")

    Args:
        func: Async function to decorate

    Returns:
        Wrapped function that preserves request ID
    """
    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        # Capture current request ID and correlation ID
        request_id = get_request_id()
        correlation_id = get_correlation_id()

        # Set them in the new async context
        if request_id:
            set_request_id(request_id)
        if correlation_id:
            set_correlation_id(correlation_id)

        return await func(*args, **kwargs)

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        # Capture current request ID and correlation ID
        request_id = get_request_id()
        correlation_id = get_correlation_id()

        # Set them in the new context
        if request_id:
            set_request_id(request_id)
        if correlation_id:
            set_correlation_id(correlation_id)

        return func(*args, **kwargs)

    # Return appropriate wrapper based on function type
    if inspect.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request ID and correlation tracking.

    Features:
    - Generates unique UUID4 request ID for each request
    - Accepts incoming X-Request-ID header for distributed tracing
    - Accepts X-Correlation-ID from upstream services
    - Validates incoming IDs to prevent injection attacks
    - Stores IDs in request.state and context variables
    - Adds X-Request-ID and X-Correlation-ID to response headers

    Headers:
        X-Request-ID: Unique identifier for this specific request
        X-Correlation-ID: Identifier that follows a request across services
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request and add request/correlation IDs.

        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain

        Returns:
            Response with request ID headers
        """
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID")

        if request_id:
            # Validate incoming request ID to prevent injection
            if not is_valid_uuid(request_id):
                logger.warning(
                    "Invalid X-Request-ID received, generating new one",
                    invalid_id=request_id,
                    client_ip=request.client.host if request.client else None
                )
                request_id = str(uuid.uuid4())
        else:
            # Generate new request ID
            request_id = str(uuid.uuid4())

        # Get correlation ID (or use request ID if not present)
        correlation_id = request.headers.get("X-Correlation-ID")

        if correlation_id:
            # Validate incoming correlation ID
            if not is_valid_uuid(correlation_id):
                logger.warning(
                    "Invalid X-Correlation-ID received, using request ID",
                    invalid_id=correlation_id,
                    client_ip=request.client.host if request.client else None
                )
                correlation_id = request_id
        else:
            # Use request ID as correlation ID if none provided
            correlation_id = request_id

        # Store in request state
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id

        # Store in context variables (for non-request contexts like background tasks)
        set_request_id(request_id)
        set_correlation_id(correlation_id)

        # Log request received
        logger.debug(
            "Request received",
            method=request.method,
            path=request.url.path,
            request_id=request_id,
            correlation_id=correlation_id
        )

        # Process request
        response = await call_next(request)

        # Add request ID and correlation ID to response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id

        return response
