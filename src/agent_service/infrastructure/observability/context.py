"""
Log context management for adding contextual information to structured logs.

This module provides context managers and utilities for adding context to logs
that automatically gets included in all log entries within that context.

Usage:
    from agent_service.infrastructure.observability.context import log_context

    with log_context(user_id="123", action="create_resource"):
        logger.info("Resource created")  # Includes user_id and action
"""
from typing import Any, Optional
from contextlib import contextmanager
import structlog


@contextmanager
def log_context(**kwargs: Any):
    """
    Context manager for adding context to logs.

    All key-value pairs passed to this context manager will be automatically
    included in all log entries made within the context.

    Args:
        **kwargs: Key-value pairs to add to log context

    Yields:
        None

    Example:
        >>> from agent_service.infrastructure.observability.context import log_context
        >>> from agent_service.infrastructure.observability.logging import get_logger
        >>>
        >>> logger = get_logger(__name__)
        >>>
        >>> with log_context(user_id="123", action="create"):
        ...     logger.info("Starting operation")  # Includes user_id and action
        ...     do_work()
        ...     logger.info("Operation complete")  # Also includes user_id and action
        >>>
        >>> # Context is cleared after exiting the with block
        >>> logger.info("Outside context")  # Does not include user_id or action
    """
    # Bind the context variables
    structlog.contextvars.bind_contextvars(**kwargs)
    try:
        yield
    finally:
        # Unbind the context variables
        structlog.contextvars.unbind_contextvars(*kwargs.keys())


def bind_context(**kwargs: Any) -> None:
    """
    Bind context variables to the current context.

    Unlike log_context, this does not automatically unbind when done.
    Use clear_context() to remove all context or unbind_context() for specific keys.

    Args:
        **kwargs: Key-value pairs to add to log context

    Example:
        >>> from agent_service.infrastructure.observability.context import bind_context
        >>> from agent_service.infrastructure.observability.logging import get_logger
        >>>
        >>> logger = get_logger(__name__)
        >>> bind_context(request_id="abc123", user_id="456")
        >>> logger.info("Processing request")  # Includes request_id and user_id
        >>> logger.info("Still in context")  # Still includes request_id and user_id
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def unbind_context(*keys: str) -> None:
    """
    Unbind specific context variables.

    Args:
        *keys: Keys to remove from log context

    Example:
        >>> from agent_service.infrastructure.observability.context import bind_context, unbind_context
        >>> from agent_service.infrastructure.observability.logging import get_logger
        >>>
        >>> logger = get_logger(__name__)
        >>> bind_context(user_id="123", session_id="abc")
        >>> logger.info("With both")  # Includes user_id and session_id
        >>> unbind_context("session_id")
        >>> logger.info("Without session")  # Only includes user_id
    """
    structlog.contextvars.unbind_contextvars(*keys)


def clear_context() -> None:
    """
    Clear all context variables.

    This removes all previously bound context from the current context.

    Example:
        >>> from agent_service.infrastructure.observability.context import bind_context, clear_context
        >>> from agent_service.infrastructure.observability.logging import get_logger
        >>>
        >>> logger = get_logger(__name__)
        >>> bind_context(user_id="123", action="create")
        >>> logger.info("With context")  # Includes user_id and action
        >>> clear_context()
        >>> logger.info("Without context")  # No additional context
    """
    structlog.contextvars.clear_contextvars()


def get_current_context() -> dict:
    """
    Get the current log context as a dictionary.

    Returns:
        Dictionary of current context variables

    Example:
        >>> from agent_service.infrastructure.observability.context import bind_context, get_current_context
        >>>
        >>> bind_context(user_id="123", action="create")
        >>> context = get_current_context()
        >>> print(context)  # {'user_id': '123', 'action': 'create'}
    """
    # This is a workaround since structlog doesn't expose this directly
    # We'll use an internal processor to capture the context
    from structlog.contextvars import merge_contextvars

    try:
        event_dict = merge_contextvars(None, None, {})
        return event_dict
    except Exception:
        return {}


@contextmanager
def user_context(user_id: Optional[str] = None, email: Optional[str] = None, **kwargs: Any):
    """
    Specialized context manager for user-related operations.

    Automatically adds user_id and email to logs, plus any additional context.

    Args:
        user_id: User ID to add to context
        email: User email to add to context
        **kwargs: Additional key-value pairs to add to context

    Yields:
        None

    Example:
        >>> from agent_service.infrastructure.observability.context import user_context
        >>> from agent_service.infrastructure.observability.logging import get_logger
        >>>
        >>> logger = get_logger(__name__)
        >>>
        >>> with user_context(user_id="123", email="user@example.com", action="update_profile"):
        ...     logger.info("Updating user profile")
        ...     # Log includes: user_id, email, action
    """
    context = {}
    if user_id is not None:
        context["user_id"] = user_id
    if email is not None:
        context["email"] = email
    context.update(kwargs)

    with log_context(**context):
        yield


@contextmanager
def operation_context(operation: str, resource_type: Optional[str] = None, **kwargs: Any):
    """
    Specialized context manager for operation tracking.

    Automatically adds operation and resource_type to logs.

    Args:
        operation: Operation being performed (e.g., "create", "update", "delete")
        resource_type: Type of resource being operated on (e.g., "user", "post")
        **kwargs: Additional key-value pairs to add to context

    Yields:
        None

    Example:
        >>> from agent_service.infrastructure.observability.context import operation_context
        >>> from agent_service.infrastructure.observability.logging import get_logger
        >>>
        >>> logger = get_logger(__name__)
        >>>
        >>> with operation_context(operation="delete", resource_type="user", user_id="123"):
        ...     logger.info("Starting deletion")
        ...     delete_user()
        ...     logger.info("Deletion complete")
    """
    context = {"operation": operation}
    if resource_type is not None:
        context["resource_type"] = resource_type
    context.update(kwargs)

    with log_context(**context):
        yield


__all__ = [
    "log_context",
    "bind_context",
    "unbind_context",
    "clear_context",
    "get_current_context",
    "user_context",
    "operation_context",
]
