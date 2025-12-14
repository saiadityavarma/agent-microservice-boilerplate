"""
Comprehensive exception hierarchy for the agent service.

This module provides a structured exception hierarchy that:
- Maps to HTTP status codes
- Includes error codes for programmatic handling
- Supports user-friendly messages
- Provides context for error handling and logging

All exceptions inherit from AppError which provides:
- error_code: Machine-readable error code (from ErrorCode enum)
- status_code: HTTP status code for API responses
- message: Human-readable error message
- details: Optional dictionary with additional context
- suggested_action: Optional user-friendly suggestion for resolution

Usage:
    from agent_service.domain.exceptions import (
        InvalidCredentials,
        AgentNotFound,
        ValidationError,
    )

    # Raise with default message
    raise InvalidCredentials()

    # Raise with custom message
    raise AgentNotFound("Agent with ID 'abc123' not found")

    # Raise with additional context
    raise ValidationError(
        "Invalid agent configuration",
        details={"field": "max_tokens", "value": -1, "expected": "> 0"}
    )
"""

from typing import Any, Optional
from agent_service.api.schemas.errors import ErrorCode


class AppError(Exception):
    """
    Base exception for all application errors.

    Provides structured error information including:
    - Error code for programmatic handling
    - HTTP status code for API responses
    - Human-readable message
    - Optional additional context
    - Optional suggested action for users

    All custom exceptions should inherit from this class.

    Attributes:
        error_code: Machine-readable error code (from ErrorCode enum)
        status_code: HTTP status code (default: 500)
        message: Human-readable error message
        details: Optional dictionary with additional error context
        suggested_action: Optional user-friendly suggestion for resolution
    """

    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR
    status_code: int = 500
    default_message: str = "An unexpected error occurred"
    default_suggested_action: Optional[str] = None

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        suggested_action: Optional[str] = None,
    ):
        """
        Initialize the exception.

        Args:
            message: Custom error message (uses default_message if not provided)
            details: Additional context about the error
            suggested_action: User-friendly suggestion (uses default_suggested_action if not provided)
        """
        self.message = message or self.default_message
        self.details = details or {}
        self.suggested_action = suggested_action or self.default_suggested_action
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation of the error."""
        return f"{self.error_code.value}: {self.message}"

    def __repr__(self) -> str:
        """Return detailed representation of the error."""
        return (
            f"{self.__class__.__name__}("
            f"error_code={self.error_code.value}, "
            f"status_code={self.status_code}, "
            f"message={self.message!r}, "
            f"details={self.details!r})"
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert exception to dictionary for serialization.

        Returns:
            Dictionary with error information
        """
        result = {
            "error_code": self.error_code.value,
            "message": self.message,
        }

        if self.details:
            result["details"] = self.details

        if self.suggested_action:
            result["suggested_action"] = self.suggested_action

        return result


# ========================================
# Authentication Errors (401)
# ========================================


class AuthError(AppError):
    """Base class for authentication errors."""

    status_code = 401
    error_code = ErrorCode.UNAUTHORIZED
    default_message = "Authentication required"
    default_suggested_action = "Please provide valid authentication credentials"


class InvalidCredentials(AuthError):
    """Invalid username/password or API key."""

    error_code = ErrorCode.INVALID_CREDENTIALS
    default_message = "Invalid credentials provided"
    default_suggested_action = "Please check your username, password, or API key and try again"


class TokenExpired(AuthError):
    """Authentication token has expired."""

    error_code = ErrorCode.TOKEN_EXPIRED
    default_message = "Authentication token has expired"
    default_suggested_action = "Please refresh your token or log in again"


class TokenInvalid(AuthError):
    """Authentication token is invalid."""

    error_code = ErrorCode.TOKEN_INVALID
    default_message = "Authentication token is invalid"
    default_suggested_action = "Please log in again to obtain a valid token"


class ApiKeyInvalid(AuthError):
    """API key is invalid or revoked."""

    error_code = ErrorCode.API_KEY_INVALID
    default_message = "API key is invalid or has been revoked"
    default_suggested_action = "Please check your API key or generate a new one"


# ========================================
# Authorization Errors (403)
# ========================================


class InsufficientPermissions(AppError):
    """User lacks required permissions."""

    status_code = 403
    error_code = ErrorCode.INSUFFICIENT_PERMISSIONS
    default_message = "You do not have permission to perform this action"
    default_suggested_action = "Please contact your administrator to request the necessary permissions"


class ResourceAccessDenied(AppError):
    """Access to specific resource denied."""

    status_code = 403
    error_code = ErrorCode.RESOURCE_ACCESS_DENIED
    default_message = "Access to this resource is denied"
    default_suggested_action = "You do not have permission to access this resource"


# ========================================
# Validation Errors (400)
# ========================================


class ValidationError(AppError):
    """Request validation failed."""

    status_code = 400
    error_code = ErrorCode.VALIDATION_ERROR
    default_message = "Request validation failed"
    default_suggested_action = "Please check your input and try again"


class InvalidRequest(AppError):
    """Request format or content is invalid."""

    status_code = 400
    error_code = ErrorCode.INVALID_REQUEST
    default_message = "Invalid request"
    default_suggested_action = "Please check the request format and content"


class InvalidParameter(AppError):
    """Invalid query or path parameter."""

    status_code = 400
    error_code = ErrorCode.INVALID_PARAMETER
    default_message = "Invalid parameter provided"
    default_suggested_action = "Please check the parameter values and try again"


class MissingField(AppError):
    """Required field is missing."""

    status_code = 400
    error_code = ErrorCode.MISSING_FIELD
    default_message = "Required field is missing"
    default_suggested_action = "Please provide all required fields"


# ========================================
# Resource Errors (404, 409)
# ========================================


class ResourceError(AppError):
    """Base class for resource-related errors."""

    pass


class NotFound(ResourceError):
    """Resource not found."""

    status_code = 404
    error_code = ErrorCode.NOT_FOUND
    default_message = "Resource not found"
    default_suggested_action = "Please check the resource ID and try again"


class UserNotFound(NotFound):
    """User not found."""

    error_code = ErrorCode.USER_NOT_FOUND
    default_message = "User not found"
    default_suggested_action = "Please verify the user ID is correct"


class AlreadyExists(ResourceError):
    """Resource already exists."""

    status_code = 409
    error_code = ErrorCode.DUPLICATE_RESOURCE
    default_message = "Resource already exists"
    default_suggested_action = "This resource already exists. Please use a different identifier or update the existing resource"


class ResourceLocked(ResourceError):
    """Resource is locked for modifications."""

    status_code = 409
    error_code = ErrorCode.RESOURCE_LOCKED
    default_message = "Resource is currently locked"
    default_suggested_action = "This resource is being modified by another process. Please try again later"


# ========================================
# Agent-Specific Errors
# ========================================


class AgentError(AppError):
    """Base class for agent-related errors."""

    default_message = "An error occurred with the agent"


class AgentNotFound(AgentError):
    """Agent not found."""

    status_code = 404
    error_code = ErrorCode.AGENT_NOT_FOUND
    default_message = "Agent not found"
    default_suggested_action = "Please verify the agent ID is correct or create a new agent"


class InvocationFailed(AgentError):
    """Agent invocation failed."""

    status_code = 500
    error_code = ErrorCode.INTERNAL_ERROR
    default_message = "Agent invocation failed"
    default_suggested_action = "The agent encountered an error during execution. Please try again or contact support if the issue persists"


class AgentTimeout(AgentError):
    """Agent execution timed out."""

    status_code = 504
    error_code = ErrorCode.TIMEOUT
    default_message = "Agent execution timed out"
    default_suggested_action = "The agent took too long to respond. Please try again with a simpler request or contact support"


class AgentConfigurationError(AgentError):
    """Agent configuration is invalid."""

    status_code = 400
    error_code = ErrorCode.VALIDATION_ERROR
    default_message = "Agent configuration is invalid"
    default_suggested_action = "Please check the agent configuration and ensure all required parameters are provided correctly"


# ========================================
# External Service Errors
# ========================================


class ExternalError(AppError):
    """Base class for external service errors."""

    default_message = "An external service error occurred"
    default_suggested_action = "An external service is currently unavailable. Please try again later"


class LLMError(ExternalError):
    """LLM service error."""

    status_code = 502
    error_code = ErrorCode.EXTERNAL_SERVICE_ERROR
    default_message = "Language model service error"
    default_suggested_action = "The AI service is currently unavailable. Please try again in a few moments"


class LLMRateLimitError(ExternalError):
    """LLM rate limit exceeded."""

    status_code = 429
    error_code = ErrorCode.RATE_LIMITED
    default_message = "Language model rate limit exceeded"
    default_suggested_action = "Too many requests to the AI service. Please wait a moment and try again"


class DatabaseError(ExternalError):
    """Database operation failed."""

    status_code = 503
    error_code = ErrorCode.DATABASE_UNAVAILABLE
    default_message = "Database operation failed"
    default_suggested_action = "The database is currently unavailable. Please try again later"


class DatabaseConnectionError(DatabaseError):
    """Database connection failed."""

    error_code = ErrorCode.DATABASE_UNAVAILABLE
    default_message = "Failed to connect to database"
    default_suggested_action = "Unable to connect to the database. Please try again later or contact support"


class CacheError(ExternalError):
    """Cache operation failed."""

    status_code = 503
    error_code = ErrorCode.SERVICE_UNAVAILABLE
    default_message = "Cache service error"
    default_suggested_action = "The cache service is currently unavailable. Your request will be processed but may be slower than usual"


# ========================================
# Rate Limiting Errors (429)
# ========================================


class RateLimitError(AppError):
    """Rate limit exceeded."""

    status_code = 429
    error_code = ErrorCode.RATE_LIMITED
    default_message = "Rate limit exceeded"
    default_suggested_action = "You have made too many requests. Please wait before trying again"


class QuotaExceeded(AppError):
    """Usage quota exceeded."""

    status_code = 429
    error_code = ErrorCode.QUOTA_EXCEEDED
    default_message = "Usage quota exceeded"
    default_suggested_action = "You have exceeded your usage quota. Please upgrade your plan or wait until your quota resets"


# ========================================
# Timeout Errors (504)
# ========================================


class TimeoutError(AppError):
    """Request timeout."""

    status_code = 504
    error_code = ErrorCode.TIMEOUT
    default_message = "Request timeout"
    default_suggested_action = "The request took too long to process. Please try again with a simpler request"


class UpstreamTimeout(AppError):
    """Upstream service timeout."""

    status_code = 504
    error_code = ErrorCode.UPSTREAM_TIMEOUT
    default_message = "Upstream service timeout"
    default_suggested_action = "An external service took too long to respond. Please try again later"


# ========================================
# Service Availability Errors (503)
# ========================================


class ServiceUnavailable(AppError):
    """Service temporarily unavailable."""

    status_code = 503
    error_code = ErrorCode.SERVICE_UNAVAILABLE
    default_message = "Service temporarily unavailable"
    default_suggested_action = "The service is temporarily unavailable. Please try again in a few moments"


class MaintenanceMode(AppError):
    """Service in maintenance mode."""

    status_code = 503
    error_code = ErrorCode.MAINTENANCE_MODE
    default_message = "Service is currently under maintenance"
    default_suggested_action = "The service is currently under maintenance. Please check back shortly"
