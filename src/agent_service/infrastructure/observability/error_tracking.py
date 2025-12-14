"""
Sentry error tracking integration.

This module provides:
- Sentry SDK initialization with environment-specific configuration
- User and request context management
- Error and message capture with filtering
- Integration with FastAPI, SQLAlchemy, Redis, and logging
- Performance monitoring with configurable sampling
- Sensitive data filtering from breadcrumbs

Usage:
    from agent_service.infrastructure.observability.error_tracking import (
        init_sentry,
        set_user_context,
        set_request_context,
        capture_exception,
        capture_message,
    )

    # Initialize at startup
    init_sentry(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        release=settings.app_version,
    )

    # Add context
    set_user_context(user_id="123", email="user@example.com")
    set_request_context(request)

    # Capture errors
    try:
        risky_operation()
    except Exception as e:
        capture_exception(e, extra={"context": "additional info"})
"""

import logging
from typing import Any, Literal, Optional
from fastapi import Request

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False


# Sensitive header names to filter
SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "x-api-key",
    "x-auth-token",
    "x-csrf-token",
    "x-session-id",
}

# Sensitive query parameter names to filter
SENSITIVE_PARAMS = {
    "password",
    "token",
    "api_key",
    "secret",
    "access_token",
    "refresh_token",
}


def _should_ignore_error(event: dict, hint: dict) -> Optional[dict]:
    """
    Filter out errors that should not be sent to Sentry.

    Filters:
    - Expected client errors (400-level)
    - Rate limit errors (429)
    - Certain exception types that are expected

    Args:
        event: Sentry event dictionary
        hint: Sentry hint dictionary with exception info

    Returns:
        Event if it should be sent, None if it should be ignored
    """
    # Check if there's an exception in the hint
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]

        # Don't send expected HTTP client errors
        if hasattr(exc_value, "status_code"):
            status_code = exc_value.status_code
            # Ignore 400-level errors except 401 (unauthorized) and 403 (forbidden)
            # which might indicate security issues
            if 400 <= status_code < 500 and status_code not in (401, 403):
                return None

        # Don't send rate limit errors (too noisy)
        if exc_type.__name__ in ("RateLimitExceeded", "TooManyRequests"):
            return None

        # Don't send validation errors (expected user input errors)
        if exc_type.__name__ in ("ValidationError", "RequestValidationError"):
            return None

    # Check response status code in the event
    if "request" in event:
        status_code = event.get("request", {}).get("status_code")
        if status_code and 400 <= status_code < 500 and status_code not in (401, 403):
            return None

    return event


def _filter_sensitive_data(event: dict, hint: dict) -> dict:
    """
    Filter sensitive data from breadcrumbs and request data.

    Args:
        event: Sentry event dictionary
        hint: Sentry hint dictionary

    Returns:
        Filtered event dictionary
    """
    # Filter sensitive headers from request
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        filtered_headers = {}
        for key, value in headers.items():
            if key.lower() in SENSITIVE_HEADERS:
                filtered_headers[key] = "[Filtered]"
            else:
                filtered_headers[key] = value
        event["request"]["headers"] = filtered_headers

    # Filter sensitive query parameters
    if "request" in event and "query_string" in event["request"]:
        query_string = event["request"].get("query_string", "")
        if query_string:
            # Parse and filter query parameters
            filtered_params = []
            for param in query_string.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    if key.lower() in SENSITIVE_PARAMS:
                        filtered_params.append(f"{key}=[Filtered]")
                    else:
                        filtered_params.append(param)
                else:
                    filtered_params.append(param)
            event["request"]["query_string"] = "&".join(filtered_params)

    # Filter sensitive data from breadcrumbs
    if "breadcrumbs" in event and "values" in event["breadcrumbs"]:
        for breadcrumb in event["breadcrumbs"]["values"]:
            # Filter sensitive data from breadcrumb data
            if "data" in breadcrumb:
                data = breadcrumb["data"]
                for key in list(data.keys()):
                    if key.lower() in SENSITIVE_PARAMS or key.lower() in SENSITIVE_HEADERS:
                        data[key] = "[Filtered]"

            # Filter sensitive data from breadcrumb message
            if "message" in breadcrumb:
                message = breadcrumb["message"]
                # Simple filtering - replace common sensitive patterns
                for sensitive_word in ["password", "token", "secret", "api_key"]:
                    if sensitive_word in message.lower():
                        breadcrumb["message"] = "[Filtered: contains sensitive data]"
                        break

    return event


def _before_send(event: dict, hint: dict) -> Optional[dict]:
    """
    Process events before sending to Sentry.

    Combines error filtering and sensitive data filtering.

    Args:
        event: Sentry event dictionary
        hint: Sentry hint dictionary

    Returns:
        Processed event or None if event should be dropped
    """
    # First check if we should ignore this error
    event = _should_ignore_error(event, hint)
    if event is None:
        return None

    # Filter sensitive data
    event = _filter_sensitive_data(event, hint)

    return event


def init_sentry(
    dsn: Optional[str] = None,
    environment: Optional[str] = None,
    release: Optional[str] = None,
    sample_rate: float = 1.0,
    traces_sample_rate: float = 0.1,
    enable_tracing: bool = True,
) -> bool:
    """
    Initialize Sentry SDK with comprehensive configuration.

    Args:
        dsn: Sentry DSN (Data Source Name). If None, Sentry is disabled.
        environment: Environment name (e.g., "production", "staging", "dev")
        release: Release version/identifier (e.g., git commit SHA or version number)
        sample_rate: Error sampling rate (0.0 to 1.0). Default 1.0 (all errors)
        traces_sample_rate: Performance tracing sample rate (0.0 to 1.0). Default 0.1 (10%)
        enable_tracing: Enable performance monitoring. Default True.

    Returns:
        True if Sentry was initialized successfully, False otherwise

    Example:
        >>> init_sentry(
        ...     dsn="https://key@sentry.io/project",
        ...     environment="production",
        ...     release="v1.2.3",
        ...     sample_rate=1.0,
        ...     traces_sample_rate=0.1,
        ... )
        True
    """
    if not SENTRY_AVAILABLE:
        logging.warning("Sentry SDK not available. Install with: pip install sentry-sdk[fastapi]")
        return False

    if not dsn:
        logging.info("Sentry DSN not provided. Error tracking disabled.")
        return False

    try:
        # Configure integrations
        integrations = [
            # FastAPI integration for automatic request tracking
            FastApiIntegration(
                transaction_style="endpoint",  # Group transactions by endpoint, not URL
                failed_request_status_codes=[500, 599],  # Only track server errors
            ),
            # Logging integration to capture log messages as breadcrumbs
            LoggingIntegration(
                level=logging.INFO,  # Capture info and above as breadcrumbs
                event_level=logging.ERROR,  # Send error logs as events
            ),
            # Redis integration for Redis operation tracking
            RedisIntegration(),
            # SQLAlchemy integration for database query tracking
            SqlalchemyIntegration(),
        ]

        # Initialize Sentry SDK
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=release,
            integrations=integrations,
            # Error sampling
            sample_rate=sample_rate,
            # Performance monitoring
            enable_tracing=enable_tracing,
            traces_sample_rate=traces_sample_rate,
            # Profiling (optional, can be enabled separately)
            profiles_sample_rate=0.0,  # Disabled by default (requires separate package)
            # Event processing
            before_send=_before_send,
            # Additional options
            attach_stacktrace=True,  # Attach stack traces to messages
            send_default_pii=False,  # Don't send PII by default
            max_breadcrumbs=50,  # Maximum number of breadcrumbs to store
            # Debug mode (only for development)
            debug=False,
        )

        logging.info(
            f"Sentry initialized successfully. Environment: {environment}, "
            f"Release: {release}, Sample rate: {sample_rate}, "
            f"Traces sample rate: {traces_sample_rate}"
        )
        return True

    except Exception as e:
        logging.error(f"Failed to initialize Sentry: {e}")
        return False


def set_user_context(
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    username: Optional[str] = None,
    **extra: Any,
) -> None:
    """
    Set user context for error tracking.

    This information will be attached to all subsequent error events
    until the context is cleared or updated.

    Args:
        user_id: Unique user identifier
        email: User email address
        username: Username
        **extra: Additional user attributes (e.g., role, subscription_tier)

    Example:
        >>> set_user_context(
        ...     user_id="user_123",
        ...     email="user@example.com",
        ...     username="john_doe",
        ...     role="admin",
        ... )
    """
    if not SENTRY_AVAILABLE:
        return

    user_data = {}

    if user_id:
        user_data["id"] = user_id
    if email:
        user_data["email"] = email
    if username:
        user_data["username"] = username

    # Add any extra user attributes
    user_data.update(extra)

    if user_data:
        sentry_sdk.set_user(user_data)


def set_request_context(request: Request) -> None:
    """
    Set request context for error tracking.

    Extracts relevant information from FastAPI request object
    and adds it to Sentry scope.

    Args:
        request: FastAPI Request object

    Example:
        >>> @app.get("/example")
        ... async def example_endpoint(request: Request):
        ...     set_request_context(request)
        ...     # ... endpoint logic
    """
    if not SENTRY_AVAILABLE:
        return

    try:
        # Set basic request info
        sentry_sdk.set_context("request", {
            "path": str(request.url.path),
            "method": request.method,
            "query_params": dict(request.query_params),
        })

        # Add request ID if available
        if hasattr(request.state, "request_id"):
            sentry_sdk.set_tag("request_id", request.state.request_id)

        # Add client info
        if request.client:
            sentry_sdk.set_context("client", {
                "host": request.client.host,
                "port": request.client.port,
            })

        # Add user agent if available
        user_agent = request.headers.get("user-agent")
        if user_agent:
            sentry_sdk.set_tag("user_agent", user_agent)

    except Exception as e:
        logging.warning(f"Failed to set request context in Sentry: {e}")


def capture_exception(
    error: Exception,
    extra: Optional[dict[str, Any]] = None,
    level: Literal["fatal", "error", "warning", "info", "debug"] = "error",
) -> Optional[str]:
    """
    Capture an exception and send it to Sentry.

    Args:
        error: The exception to capture
        extra: Additional context to attach to the error event
        level: Severity level of the error

    Returns:
        Event ID if the error was sent to Sentry, None otherwise

    Example:
        >>> try:
        ...     risky_operation()
        ... except ValueError as e:
        ...     capture_exception(
        ...         e,
        ...         extra={
        ...             "operation": "data_processing",
        ...             "input_size": 1000,
        ...         },
        ...         level="error",
        ...     )
    """
    if not SENTRY_AVAILABLE:
        return None

    try:
        # Set scope with extra context
        with sentry_sdk.push_scope() as scope:
            # Set severity level
            scope.level = level

            # Add extra context
            if extra:
                for key, value in extra.items():
                    scope.set_extra(key, value)

            # Capture the exception
            event_id = sentry_sdk.capture_exception(error)
            return event_id

    except Exception as e:
        logging.error(f"Failed to capture exception in Sentry: {e}")
        return None


def capture_message(
    message: str,
    level: Literal["fatal", "error", "warning", "info", "debug"] = "info",
    extra: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    """
    Capture a message and send it to Sentry.

    Use this for important events or non-exception errors that you want to track.

    Args:
        message: The message to capture
        level: Severity level of the message
        extra: Additional context to attach to the message event

    Returns:
        Event ID if the message was sent to Sentry, None otherwise

    Example:
        >>> capture_message(
        ...     "User exceeded daily quota",
        ...     level="warning",
        ...     extra={
        ...         "user_id": "user_123",
        ...         "quota_limit": 1000,
        ...         "current_usage": 1050,
        ...     },
        ... )
    """
    if not SENTRY_AVAILABLE:
        return None

    try:
        # Set scope with extra context
        with sentry_sdk.push_scope() as scope:
            # Set severity level
            scope.level = level

            # Add extra context
            if extra:
                for key, value in extra.items():
                    scope.set_extra(key, value)

            # Capture the message
            event_id = sentry_sdk.capture_message(message, level=level)
            return event_id

    except Exception as e:
        logging.error(f"Failed to capture message in Sentry: {e}")
        return None


def clear_user_context() -> None:
    """
    Clear user context from Sentry scope.

    Call this when a user logs out or when processing ends.

    Example:
        >>> @app.post("/logout")
        ... async def logout():
        ...     clear_user_context()
        ...     # ... logout logic
    """
    if not SENTRY_AVAILABLE:
        return

    sentry_sdk.set_user(None)


def add_breadcrumb(
    message: str,
    category: str = "default",
    level: Literal["fatal", "error", "warning", "info", "debug"] = "info",
    data: Optional[dict[str, Any]] = None,
) -> None:
    """
    Add a breadcrumb to the current Sentry scope.

    Breadcrumbs are a trail of events that led up to an error,
    helping with debugging and understanding context.

    Args:
        message: Breadcrumb message
        category: Category of the breadcrumb (e.g., "auth", "query", "navigation")
        level: Severity level
        data: Additional data to attach to the breadcrumb

    Example:
        >>> add_breadcrumb(
        ...     message="User started checkout process",
        ...     category="ecommerce",
        ...     level="info",
        ...     data={"cart_items": 3, "total": 99.99},
        ... )
    """
    if not SENTRY_AVAILABLE:
        return

    try:
        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data or {},
        )
    except Exception as e:
        logging.warning(f"Failed to add breadcrumb to Sentry: {e}")


def set_tag(key: str, value: str) -> None:
    """
    Set a tag in the current Sentry scope.

    Tags are key/value pairs that can be used to filter and search errors.

    Args:
        key: Tag key
        value: Tag value

    Example:
        >>> set_tag("payment_provider", "stripe")
        >>> set_tag("feature_flag", "new_checkout")
    """
    if not SENTRY_AVAILABLE:
        return

    try:
        sentry_sdk.set_tag(key, value)
    except Exception as e:
        logging.warning(f"Failed to set tag in Sentry: {e}")


def set_context(key: str, value: dict[str, Any]) -> None:
    """
    Set a context in the current Sentry scope.

    Contexts are structured data associated with an event.

    Args:
        key: Context key/name
        value: Context data (dictionary)

    Example:
        >>> set_context("shopping_cart", {
        ...     "item_count": 3,
        ...     "total_value": 99.99,
        ...     "currency": "USD",
        ... })
    """
    if not SENTRY_AVAILABLE:
        return

    try:
        sentry_sdk.set_context(key, value)
    except Exception as e:
        logging.warning(f"Failed to set context in Sentry: {e}")


def flush(timeout: float = 2.0) -> bool:
    """
    Flush pending Sentry events.

    Useful before application shutdown to ensure all events are sent.

    Args:
        timeout: Maximum time to wait for events to be sent (in seconds)

    Returns:
        True if all events were sent successfully within timeout

    Example:
        >>> # During application shutdown
        >>> flush(timeout=5.0)
    """
    if not SENTRY_AVAILABLE:
        return False

    try:
        return sentry_sdk.flush(timeout=timeout)
    except Exception as e:
        logging.error(f"Failed to flush Sentry events: {e}")
        return False
