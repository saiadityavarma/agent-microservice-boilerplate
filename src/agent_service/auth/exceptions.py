"""
Authentication and authorization exceptions.

This module defines custom exceptions for authentication and authorization
operations, providing specific error types for different failure scenarios.
"""

from typing import Optional


class AuthenticationError(Exception):
    """Base exception for authentication failures."""

    def __init__(
        self,
        message: str = "Authentication failed",
        *,
        provider: Optional[str] = None,
        original_error: Optional[Exception] = None
    ) -> None:
        """
        Initialize authentication error.

        Args:
            message: Error message describing the authentication failure
            provider: Name of the authentication provider (e.g., 'azure_ad', 'cognito')
            original_error: Original exception that caused this error, if any
        """
        self.message = message
        self.provider = provider
        self.original_error = original_error
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation of the error."""
        error_parts = [self.message]
        if self.provider:
            error_parts.append(f"Provider: {self.provider}")
        if self.original_error:
            error_parts.append(f"Cause: {str(self.original_error)}")
        return " | ".join(error_parts)


class TokenExpiredError(AuthenticationError):
    """Exception raised when an authentication token has expired."""

    def __init__(
        self,
        message: str = "Token has expired",
        *,
        provider: Optional[str] = None,
        expired_at: Optional[int] = None,
        original_error: Optional[Exception] = None
    ) -> None:
        """
        Initialize token expired error.

        Args:
            message: Error message describing the expiration
            provider: Name of the authentication provider
            expired_at: Unix timestamp when the token expired
            original_error: Original exception that caused this error, if any
        """
        super().__init__(message, provider=provider, original_error=original_error)
        self.expired_at = expired_at

    def __str__(self) -> str:
        """Return string representation of the error."""
        error_str = super().__str__()
        if self.expired_at:
            error_str += f" | Expired at: {self.expired_at}"
        return error_str


class InvalidTokenError(AuthenticationError):
    """Exception raised when a token is invalid or malformed."""

    def __init__(
        self,
        message: str = "Token is invalid",
        *,
        provider: Optional[str] = None,
        reason: Optional[str] = None,
        original_error: Optional[Exception] = None
    ) -> None:
        """
        Initialize invalid token error.

        Args:
            message: Error message describing the validation failure
            provider: Name of the authentication provider
            reason: Specific reason why the token is invalid
            original_error: Original exception that caused this error, if any
        """
        super().__init__(message, provider=provider, original_error=original_error)
        self.reason = reason

    def __str__(self) -> str:
        """Return string representation of the error."""
        error_str = super().__str__()
        if self.reason:
            error_str += f" | Reason: {self.reason}"
        return error_str


class ProviderConfigError(Exception):
    """Exception raised when authentication provider configuration is invalid."""

    def __init__(
        self,
        message: str = "Provider configuration is invalid",
        *,
        provider: Optional[str] = None,
        missing_fields: Optional[list[str]] = None,
        original_error: Optional[Exception] = None
    ) -> None:
        """
        Initialize provider configuration error.

        Args:
            message: Error message describing the configuration issue
            provider: Name of the authentication provider
            missing_fields: List of missing required configuration fields
            original_error: Original exception that caused this error, if any
        """
        self.message = message
        self.provider = provider
        self.missing_fields = missing_fields or []
        self.original_error = original_error
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation of the error."""
        error_parts = [self.message]
        if self.provider:
            error_parts.append(f"Provider: {self.provider}")
        if self.missing_fields:
            error_parts.append(f"Missing fields: {', '.join(self.missing_fields)}")
        if self.original_error:
            error_parts.append(f"Cause: {str(self.original_error)}")
        return " | ".join(error_parts)


class AuthorizationError(Exception):
    """Exception raised when user lacks required permissions."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        *,
        required_roles: Optional[list[str]] = None,
        user_roles: Optional[list[str]] = None,
        resource: Optional[str] = None
    ) -> None:
        """
        Initialize authorization error.

        Args:
            message: Error message describing the authorization failure
            required_roles: List of roles required for the operation
            user_roles: List of roles the user has
            resource: Resource that was being accessed
        """
        self.message = message
        self.required_roles = required_roles or []
        self.user_roles = user_roles or []
        self.resource = resource
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation of the error."""
        error_parts = [self.message]
        if self.resource:
            error_parts.append(f"Resource: {self.resource}")
        if self.required_roles:
            error_parts.append(f"Required roles: {', '.join(self.required_roles)}")
        if self.user_roles:
            error_parts.append(f"User roles: {', '.join(self.user_roles)}")
        return " | ".join(error_parts)
