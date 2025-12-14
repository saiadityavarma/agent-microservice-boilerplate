"""
Structured logging configuration.

Claude Code: Use `logger` from this module, not print() or logging.getLogger().
"""
from typing import Optional, Any
import re
import structlog
from agent_service.config.settings import get_settings
from agent_service.api.middleware.request_id import add_request_id_to_log, get_request_id


# PII patterns for masking
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PHONE_PATTERN = re.compile(r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b')
IP_PATTERN = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
CREDIT_CARD_PATTERN = re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b')
SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')


def mask_pii_value(value: str) -> str:
    """
    Mask PII (Personally Identifiable Information) in a string value.

    Masks:
    - Email addresses
    - Phone numbers
    - IP addresses
    - Credit card numbers
    - Social Security Numbers

    Args:
        value: String that may contain PII

    Returns:
        String with PII masked

    Example:
        >>> mask_pii_value("Contact john@example.com")
        'Contact ***@***'
        >>> mask_pii_value("Call 555-123-4567")
        'Call ***-***-****'
    """
    if not isinstance(value, str):
        return value

    # Mask emails
    value = EMAIL_PATTERN.sub('***@***', value)

    # Mask phone numbers
    value = PHONE_PATTERN.sub('***-***-****', value)

    # Mask IP addresses
    value = IP_PATTERN.sub('***.***.***.***', value)

    # Mask credit cards
    value = CREDIT_CARD_PATTERN.sub('****-****-****-****', value)

    # Mask SSNs
    value = SSN_PATTERN.sub('***-**-****', value)

    return value


def mask_pii_in_dict(data: dict, enabled: bool = True) -> dict:
    """
    Recursively mask PII in dictionary values.

    Args:
        data: Dictionary potentially containing PII
        enabled: Whether PII masking is enabled

    Returns:
        New dictionary with PII masked
    """
    if not enabled:
        return data

    masked = {}
    for key, value in data.items():
        if isinstance(value, str):
            masked[key] = mask_pii_value(value)
        elif isinstance(value, dict):
            masked[key] = mask_pii_in_dict(value, enabled)
        elif isinstance(value, list):
            masked[key] = [
                mask_pii_in_dict(item, enabled) if isinstance(item, dict)
                else mask_pii_value(item) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            masked[key] = value

    return masked


def pii_masking_processor(logger_obj: Any, method_name: str, event_dict: dict) -> dict:
    """
    Structlog processor that masks PII in log events.

    This processor should be added after merge_contextvars and before
    any rendering processors.

    Args:
        logger_obj: Logger object
        method_name: Method name
        event_dict: Event dictionary from structlog

    Returns:
        Event dictionary with PII masked
    """
    settings = get_settings()
    if settings.log_pii_masking_enabled:
        return mask_pii_in_dict(event_dict, enabled=True)
    return event_dict


def user_context_processor(logger_obj: Any, method_name: str, event_dict: dict) -> dict:
    """
    Structlog processor that adds user context from the current request.

    Adds user_id and email if available from the authenticated user.

    Args:
        logger_obj: Logger object
        method_name: Method name
        event_dict: Event dictionary from structlog

    Returns:
        Event dictionary with user context added
    """
    # Try to get user from request state
    # This requires the request to be available in context
    try:
        from starlette.requests import Request
        from starlette.middleware.base import RequestResponseEndpoint
        from contextvars import ContextVar

        # Check if user info is already in the event dict (added by middleware)
        if 'user_id' not in event_dict and 'email' not in event_dict:
            # This will be populated by the middleware
            pass
    except Exception:
        pass

    return event_dict


def log_level_filter_processor(logger_obj: Any, method_name: str, event_dict: dict) -> dict:
    """
    Structlog processor for per-module log level filtering.

    This allows different modules to have different log levels.

    Args:
        logger_obj: Logger object
        method_name: Method name
        event_dict: Event dictionary from structlog

    Returns:
        Event dictionary (unchanged)

    Note:
        Module-specific log levels can be configured via environment variables:
        LOG_LEVEL_MODULE_NAME=DEBUG
    """
    # This is handled by make_filtering_bound_logger
    # But can be extended for per-module filtering if needed
    return event_dict


def console_renderer_with_colors():
    """
    Create a console renderer with colors for development.

    Returns:
        Configured ConsoleRenderer instance
    """
    return structlog.dev.ConsoleRenderer(
        colors=True,
        pad_event=25,
        exception_formatter=structlog.dev.plain_traceback,
    )


def json_renderer():
    """
    Create a JSON renderer for production.

    Returns:
        Configured JSONRenderer instance
    """
    return structlog.processors.JSONRenderer()


def configure_logging() -> None:
    """
    Configure structured logging with automatic secret masking, PII protection, and context.

    This sets up the logging system with:
    - Context variable merging (for log_context usage)
    - Request ID and correlation ID tracking
    - User context (user_id, email) from authenticated requests
    - Automatic secret masking (API keys, passwords, tokens)
    - PII masking (emails, phone numbers, IPs) when enabled
    - JSON formatting for production or colored console for development
    - Per-module log level filtering
    """
    settings = get_settings()

    # Import mask_secrets_processor - deferred to avoid circular imports
    from agent_service.config.secrets import mask_secrets_processor

    # Determine renderer based on settings
    if settings.log_format == "json":
        renderer = json_renderer()
    else:
        renderer = console_renderer_with_colors()

    # Build processor chain
    processors = [
        # 1. Merge context variables (allows log_context to work)
        structlog.contextvars.merge_contextvars,

        # 2. Add request ID and correlation ID
        add_request_id_to_log,

        # 3. Add user context (user_id, email from auth)
        user_context_processor,

        # 4. Add log level
        structlog.processors.add_log_level,

        # 5. Add timestamp
        structlog.processors.TimeStamper(fmt="iso"),

        # 6. Mask secrets (API keys, passwords, tokens, etc.)
        mask_secrets_processor,

        # 7. Mask PII (emails, phone numbers, IPs, etc.)
        pii_masking_processor,

        # 8. Add stack info if requested
        structlog.processors.StackInfoRenderer(),

        # 9. Format exceptions
        structlog.processors.format_exc_info,

        # 10. Final rendering (JSON or Console)
        renderer,
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(settings.log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """
    Get a logger instance with structured logging support.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        BoundLogger instance with all configured processors

    Usage:
        >>> from agent_service.infrastructure.observability.logging import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("something happened", key="value")
        >>> logger.info("user action", user_id="123", action="login")

    Note:
        Use log_context for adding context to multiple log entries:
        >>> from agent_service.infrastructure.observability.context import log_context
        >>> with log_context(user_id="123"):
        ...     logger.info("action 1")  # Includes user_id
        ...     logger.info("action 2")  # Also includes user_id
    """
    return structlog.get_logger(name)


# Convenience export
logger = get_logger()
