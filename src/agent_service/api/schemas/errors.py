"""Error response schemas and error codes."""

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    """
    Standard error codes for API responses.

    Error codes are categorized by HTTP status code ranges:
    - 4xx: Client errors
    - 5xx: Server errors

    Use these codes consistently across the API for better error handling.
    """

    # ===== Validation Errors (400) =====
    VALIDATION_ERROR = "VALIDATION_ERROR"
    """Input validation failed (400)"""

    INVALID_REQUEST = "INVALID_REQUEST"
    """Request format or content is invalid (400)"""

    INVALID_PARAMETER = "INVALID_PARAMETER"
    """Invalid query parameter or path parameter (400)"""

    MISSING_FIELD = "MISSING_FIELD"
    """Required field is missing (400)"""

    # ===== Authentication Errors (401) =====
    UNAUTHORIZED = "UNAUTHORIZED"
    """Authentication required (401)"""

    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    """Invalid username/password or API key (401)"""

    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    """Authentication token has expired (401)"""

    TOKEN_INVALID = "TOKEN_INVALID"
    """Authentication token is invalid (401)"""

    API_KEY_INVALID = "API_KEY_INVALID"
    """API key is invalid or revoked (401)"""

    # ===== Authorization Errors (403) =====
    FORBIDDEN = "FORBIDDEN"
    """Access forbidden - insufficient permissions (403)"""

    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    """User lacks required permissions (403)"""

    RESOURCE_ACCESS_DENIED = "RESOURCE_ACCESS_DENIED"
    """Access to specific resource denied (403)"""

    # ===== Not Found Errors (404) =====
    NOT_FOUND = "NOT_FOUND"
    """Resource not found (404)"""

    ENDPOINT_NOT_FOUND = "ENDPOINT_NOT_FOUND"
    """API endpoint not found (404)"""

    USER_NOT_FOUND = "USER_NOT_FOUND"
    """User not found (404)"""

    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    """Agent not found (404)"""

    # ===== Conflict Errors (409) =====
    CONFLICT = "CONFLICT"
    """Resource conflict (409)"""

    DUPLICATE_RESOURCE = "DUPLICATE_RESOURCE"
    """Resource already exists (409)"""

    RESOURCE_LOCKED = "RESOURCE_LOCKED"
    """Resource is locked for modifications (409)"""

    # ===== Rate Limiting (429) =====
    RATE_LIMITED = "RATE_LIMITED"
    """Rate limit exceeded (429)"""

    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    """Usage quota exceeded (429)"""

    # ===== Server Errors (500) =====
    INTERNAL_ERROR = "INTERNAL_ERROR"
    """Internal server error (500)"""

    DATABASE_ERROR = "DATABASE_ERROR"
    """Database operation failed (500)"""

    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    """External service call failed (500)"""

    # ===== Service Unavailable (503) =====
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    """Service temporarily unavailable (503)"""

    MAINTENANCE_MODE = "MAINTENANCE_MODE"
    """Service in maintenance mode (503)"""

    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    """Database unavailable (503)"""

    # ===== Timeout Errors (504) =====
    TIMEOUT = "TIMEOUT"
    """Request timeout (504)"""

    UPSTREAM_TIMEOUT = "UPSTREAM_TIMEOUT"
    """Upstream service timeout (504)"""


class FieldError(BaseModel):
    """
    Detailed error information for a specific field.

    Used in validation errors to provide field-level error details.
    """

    model_config = {"str_strip_whitespace": True}

    field: str = Field(
        ...,
        description="Field name or path (e.g., 'email', 'user.address.zip')",
        examples=["email", "password", "items[0].quantity"]
    )
    message: str = Field(
        ...,
        description="Human-readable error message for this field",
        examples=[
            "Email format is invalid",
            "Password must be at least 8 characters",
            "Quantity must be greater than 0"
        ]
    )
    code: str | None = Field(
        default=None,
        description="Optional machine-readable error code for this field",
        examples=["INVALID_EMAIL", "PASSWORD_TOO_SHORT", "VALUE_OUT_OF_RANGE"]
    )
    value: Any | None = Field(
        default=None,
        description="The invalid value that was provided (may be omitted for security)",
        examples=["invalid-email", "abc", -1]
    )


class ErrorDetail(BaseModel):
    """
    Detailed error information.

    Provides structured error details including:
    - Error code for programmatic handling
    - Human-readable message
    - Optional field-level validation errors
    - Optional additional context

    Example:
        ```python
        error = ErrorDetail(
            code=ErrorCode.VALIDATION_ERROR,
            message="Request validation failed",
            details=[
                FieldError(
                    field="email",
                    message="Invalid email format",
                    code="INVALID_EMAIL",
                    value="not-an-email"
                ),
                FieldError(
                    field="age",
                    message="Age must be at least 18",
                    code="VALUE_OUT_OF_RANGE",
                    value=15
                )
            ]
        )
        ```
    """

    model_config = {"str_strip_whitespace": True}

    code: ErrorCode = Field(
        ...,
        description="Machine-readable error code",
        examples=[
            ErrorCode.VALIDATION_ERROR,
            ErrorCode.NOT_FOUND,
            ErrorCode.UNAUTHORIZED
        ]
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
        examples=[
            "Request validation failed",
            "Resource not found",
            "Authentication required"
        ]
    )
    details: list[FieldError] | None = Field(
        default=None,
        description="Field-level error details (primarily for validation errors)",
        examples=[
            [
                {
                    "field": "email",
                    "message": "Invalid email format",
                    "code": "INVALID_EMAIL"
                }
            ]
        ]
    )
    context: dict[str, Any] | None = Field(
        default=None,
        description="Additional error context (e.g., resource IDs, retry info)",
        examples=[
            {"resource_id": "123", "resource_type": "agent"},
            {"retry_after": 60, "limit": 100, "window": "1 hour"}
        ]
    )

    @classmethod
    def from_validation_error(
        cls,
        validation_errors: list[dict[str, Any]]
    ) -> "ErrorDetail":
        """
        Create ErrorDetail from Pydantic validation errors.

        Args:
            validation_errors: List of Pydantic validation error dicts

        Returns:
            ErrorDetail with field-level validation errors

        Example:
            ```python
            from pydantic import ValidationError

            try:
                MyModel(**data)
            except ValidationError as e:
                error_detail = ErrorDetail.from_validation_error(
                    e.errors()
                )
            ```
        """
        field_errors = []

        for err in validation_errors:
            # Extract field path from location tuple
            field_path = ".".join(str(loc) for loc in err.get("loc", []))

            field_errors.append(
                FieldError(
                    field=field_path,
                    message=err.get("msg", "Validation error"),
                    code=err.get("type", "VALIDATION_ERROR").upper(),
                    value=err.get("input")
                )
            )

        return cls(
            code=ErrorCode.VALIDATION_ERROR,
            message="Request validation failed",
            details=field_errors
        )

    @classmethod
    def from_exception(
        cls,
        exc: Exception,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR
    ) -> "ErrorDetail":
        """
        Create ErrorDetail from a generic exception.

        Args:
            exc: Exception that occurred
            code: Error code to use (defaults to INTERNAL_ERROR)

        Returns:
            ErrorDetail with exception information

        Example:
            ```python
            try:
                # Some operation
                ...
            except ValueError as e:
                error_detail = ErrorDetail.from_exception(
                    e,
                    code=ErrorCode.INVALID_PARAMETER
                )
            ```
        """
        return cls(
            code=code,
            message=str(exc),
            context={
                "exception_type": type(exc).__name__
            }
        )
