"""
Comprehensive error handling middleware for FastAPI.

This module provides:
- Exception handlers for all AppError subclasses
- HTTP status code mapping
- Structured error responses with error codes
- Request ID tracking in error responses
- Contextual logging with user and request information
- Sentry integration for 5xx errors
- Production-safe error messages (hides internal details)
- Validation error handling with field-level details

The error handling system ensures:
1. All errors are logged with appropriate context
2. 5xx errors are sent to Sentry for monitoring
3. Error responses include request_id for tracing
4. Production environments hide sensitive internal details
5. Validation errors provide field-level feedback

Usage:
    from fastapi import FastAPI
    from agent_service.api.middleware.errors import register_error_handlers

    app = FastAPI()
    register_error_handlers(app)
"""

import logging
import traceback
import uuid
from typing import Any, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from agent_service.api.schemas.errors import ErrorCode, ErrorDetail, FieldError
from agent_service.config.settings import get_settings
from agent_service.domain.exceptions import AppError

try:
    from agent_service.infrastructure.observability.error_tracking import (
        capture_exception,
        set_request_context,
        set_user_context,
    )
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False


logger = logging.getLogger(__name__)


def _get_request_id(request: Request) -> str:
    """
    Extract or generate request ID for error tracking.

    Args:
        request: FastAPI Request object

    Returns:
        Request ID string
    """
    # Check if request_id exists in request state (set by request ID middleware)
    if hasattr(request.state, "request_id"):
        return request.state.request_id

    # Check if provided in headers
    request_id = request.headers.get("x-request-id")
    if request_id:
        return request_id

    # Generate new request ID
    return str(uuid.uuid4())


def _get_user_info(request: Request) -> Optional[dict[str, Any]]:
    """
    Extract user information from request for logging context.

    Args:
        request: FastAPI Request object

    Returns:
        Dictionary with user info or None
    """
    user_info = {}

    # Check if user exists in request state (set by auth middleware)
    if hasattr(request.state, "user"):
        user = request.state.user
        if hasattr(user, "id"):
            user_info["user_id"] = str(user.id)
        if hasattr(user, "email"):
            user_info["email"] = user.email
        if hasattr(user, "username"):
            user_info["username"] = user.username

    return user_info if user_info else None


def _should_log_error(status_code: int) -> bool:
    """
    Determine if an error should be logged based on status code.

    Args:
        status_code: HTTP status code

    Returns:
        True if error should be logged
    """
    # Always log 5xx errors
    if status_code >= 500:
        return True

    # Log auth failures (401, 403) for security monitoring
    if status_code in (401, 403):
        return True

    # Don't log 4xx client errors (except 401/403)
    return False


def _should_send_to_sentry(status_code: int) -> bool:
    """
    Determine if an error should be sent to Sentry.

    Args:
        status_code: HTTP status code

    Returns:
        True if error should be sent to Sentry
    """
    # Only send 5xx server errors to Sentry
    return status_code >= 500


def _create_error_response(
    error_code: ErrorCode,
    message: str,
    request_id: str,
    status_code: int,
    details: Optional[list[FieldError]] = None,
    context: Optional[dict[str, Any]] = None,
    suggested_action: Optional[str] = None,
    is_production: bool = False,
) -> JSONResponse:
    """
    Create standardized error response.

    Args:
        error_code: Machine-readable error code
        message: Human-readable error message
        request_id: Request ID for tracing
        status_code: HTTP status code
        details: Optional field-level error details
        context: Optional additional context
        suggested_action: Optional user-friendly suggestion
        is_production: Whether running in production (hides internal details)

    Returns:
        JSONResponse with error information
    """
    # In production, use generic messages for 5xx errors
    if is_production and status_code >= 500:
        message = "An internal error occurred. Please try again later."
        # Remove sensitive context in production
        context = None

    # Build error detail
    error_detail = ErrorDetail(
        code=error_code,
        message=message,
        details=details,
        context=context,
    )

    # Build response content
    response_content: dict[str, Any] = {
        "error": error_detail.model_dump(exclude_none=True),
        "request_id": request_id,
    }

    # Add suggested action if provided
    if suggested_action:
        response_content["suggested_action"] = suggested_action

    return JSONResponse(
        status_code=status_code,
        content=response_content,
    )


def _log_error(
    request: Request,
    error: Exception,
    status_code: int,
    request_id: str,
    user_info: Optional[dict[str, Any]] = None,
) -> None:
    """
    Log error with context.

    Args:
        request: FastAPI Request object
        error: Exception that occurred
        status_code: HTTP status code
        request_id: Request ID for tracing
        user_info: Optional user information
    """
    # Build log context
    log_context = {
        "request_id": request_id,
        "path": request.url.path,
        "method": request.method,
        "status_code": status_code,
        "error_type": type(error).__name__,
    }

    # Add user info if available
    if user_info:
        log_context.update(user_info)

    # Add query params if present
    if request.query_params:
        log_context["query_params"] = dict(request.query_params)

    # Determine log level and include traceback for 5xx errors
    if status_code >= 500:
        logger.error(
            f"Server error: {error}",
            extra=log_context,
            exc_info=True,  # Include traceback
        )
    elif status_code in (401, 403):
        logger.warning(
            f"Authentication/Authorization error: {error}",
            extra=log_context,
        )
    else:
        logger.info(
            f"Client error: {error}",
            extra=log_context,
        )


def _send_to_sentry(
    request: Request,
    error: Exception,
    user_info: Optional[dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> None:
    """
    Send error to Sentry with context.

    Args:
        request: FastAPI Request object
        error: Exception that occurred
        user_info: Optional user information
        request_id: Optional request ID
    """
    if not SENTRY_AVAILABLE:
        return

    try:
        # Set user context if available
        if user_info:
            set_user_context(**user_info)

        # Set request context
        set_request_context(request)

        # Build extra context
        extra = {
            "path": request.url.path,
            "method": request.method,
            "error_type": type(error).__name__,
        }

        if request_id:
            extra["request_id"] = request_id

        # Capture exception
        capture_exception(error, extra=extra)

    except Exception as e:
        logger.error(f"Failed to send error to Sentry: {e}")


def register_error_handlers(app: FastAPI) -> None:
    """
    Register all error handlers for the FastAPI application.

    This should be called during application initialization.

    Args:
        app: FastAPI application instance

    Example:
        >>> from fastapi import FastAPI
        >>> from agent_service.api.middleware.errors import register_error_handlers
        >>>
        >>> app = FastAPI()
        >>> register_error_handlers(app)
    """
    settings = get_settings()

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        """
        Handle all AppError subclass exceptions.

        Provides structured error responses with:
        - Error code and message
        - Request ID for tracing
        - Field-level details for validation errors
        - User-friendly suggested actions
        - Contextual logging
        - Sentry integration for 5xx errors
        """
        request_id = _get_request_id(request)
        user_info = _get_user_info(request)

        # Log error if needed
        if _should_log_error(exc.status_code):
            _log_error(request, exc, exc.status_code, request_id, user_info)

        # Send to Sentry if needed
        if _should_send_to_sentry(exc.status_code):
            _send_to_sentry(request, exc, user_info, request_id)

        # Create error response
        return _create_error_response(
            error_code=exc.error_code,
            message=exc.message,
            request_id=request_id,
            status_code=exc.status_code,
            context=exc.details if exc.details else None,
            suggested_action=exc.suggested_action,
            is_production=settings.is_production,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """
        Handle FastAPI request validation errors.

        Converts Pydantic validation errors to structured field-level errors
        with user-friendly messages.
        """
        request_id = _get_request_id(request)
        user_info = _get_user_info(request)

        # Convert Pydantic errors to FieldError objects
        field_errors = []
        for error in exc.errors():
            # Extract field path from location tuple
            field_path = ".".join(str(loc) for loc in error.get("loc", []))

            # Create user-friendly error message
            error_type = error.get("type", "")
            error_msg = error.get("msg", "Validation error")

            # Enhance error messages for common validation types
            if error_type == "missing":
                error_msg = f"This field is required"
            elif error_type == "string_type":
                error_msg = "Must be a valid string"
            elif error_type == "int_type":
                error_msg = "Must be a valid integer"
            elif error_type == "float_type":
                error_msg = "Must be a valid number"
            elif error_type == "bool_type":
                error_msg = "Must be true or false"
            elif error_type == "value_error.email":
                error_msg = "Must be a valid email address"
            elif error_type == "value_error.url":
                error_msg = "Must be a valid URL"

            field_errors.append(
                FieldError(
                    field=field_path,
                    message=error_msg,
                    code=error_type.upper().replace(".", "_"),
                    value=error.get("input"),
                )
            )

        # Log validation error
        logger.info(
            f"Validation error: {len(field_errors)} field(s) failed validation",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "field_count": len(field_errors),
                **(user_info or {}),
            },
        )

        # Create error response
        return _create_error_response(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Request validation failed",
            request_id=request_id,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=field_errors,
            suggested_action="Please check your input and ensure all required fields are provided correctly",
            is_production=settings.is_production,
        )

    @app.exception_handler(PydanticValidationError)
    async def pydantic_validation_error_handler(
        request: Request,
        exc: PydanticValidationError,
    ) -> JSONResponse:
        """
        Handle Pydantic validation errors (for models not in request body).
        """
        request_id = _get_request_id(request)
        user_info = _get_user_info(request)

        # Convert to ErrorDetail
        error_detail = ErrorDetail.from_validation_error(exc.errors())

        # Log validation error
        logger.info(
            f"Pydantic validation error: {exc}",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                **(user_info or {}),
            },
        )

        # Create error response
        return _create_error_response(
            error_code=error_detail.code,
            message=error_detail.message,
            request_id=request_id,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=error_detail.details,
            suggested_action="Please check your input and try again",
            is_production=settings.is_production,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """
        Handle all unhandled exceptions.

        Provides a safe fallback for unexpected errors, ensuring:
        - All errors are logged
        - 5xx errors are sent to Sentry
        - Production environments hide internal details
        - Users receive helpful error messages
        """
        request_id = _get_request_id(request)
        user_info = _get_user_info(request)

        # Log unexpected error
        logger.error(
            f"Unhandled exception: {exc}",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "error_type": type(exc).__name__,
                **(user_info or {}),
            },
            exc_info=True,  # Include full traceback
        )

        # Send to Sentry
        _send_to_sentry(request, exc, user_info, request_id)

        # Create safe error response
        error_message = "An unexpected error occurred"
        suggested_action = "Please try again later. If the problem persists, contact support"

        # In development, include exception details
        context = None
        if not settings.is_production:
            error_message = f"An unexpected error occurred: {str(exc)}"
            context = {
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
            }

        return _create_error_response(
            error_code=ErrorCode.INTERNAL_ERROR,
            message=error_message,
            request_id=request_id,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            context=context,
            suggested_action=suggested_action,
            is_production=settings.is_production,
        )


# Legacy error classes for backward compatibility
# These are deprecated - use exceptions from domain.exceptions instead
class NotFoundError(AppError):
    """
    Deprecated: Use domain.exceptions.NotFound instead.

    This class is kept for backward compatibility.
    """

    def __init__(self, message: str = "Resource not found"):
        from agent_service.domain.exceptions import NotFound
        exc = NotFound(message)
        super().__init__(
            message=exc.message,
            details=exc.details,
            suggested_action=exc.suggested_action,
        )


class ValidationError(AppError):
    """
    Deprecated: Use domain.exceptions.ValidationError instead.

    This class is kept for backward compatibility.
    """

    def __init__(self, message: str):
        from agent_service.domain.exceptions import ValidationError as DomainValidationError
        exc = DomainValidationError(message)
        super().__init__(
            message=exc.message,
            details=exc.details,
            suggested_action=exc.suggested_action,
        )
