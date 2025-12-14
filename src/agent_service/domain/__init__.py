"""Domain models, events, and exceptions."""

from agent_service.domain.exceptions import (
    AppError,
    AuthError,
    InvalidCredentials,
    TokenExpired,
    TokenInvalid,
    ApiKeyInvalid,
    InsufficientPermissions,
    ResourceAccessDenied,
    ValidationError,
    InvalidRequest,
    InvalidParameter,
    MissingField,
    ResourceError,
    NotFound,
    UserNotFound,
    AlreadyExists,
    ResourceLocked,
    AgentError,
    AgentNotFound,
    InvocationFailed,
    AgentTimeout,
    AgentConfigurationError,
    ExternalError,
    LLMError,
    LLMRateLimitError,
    DatabaseError,
    DatabaseConnectionError,
    CacheError,
    RateLimitError,
    QuotaExceeded,
    TimeoutError,
    UpstreamTimeout,
    ServiceUnavailable,
    MaintenanceMode,
)

__all__ = [
    # Base exceptions
    "AppError",
    "AuthError",
    "ResourceError",
    "AgentError",
    "ExternalError",
    # Authentication errors (401)
    "InvalidCredentials",
    "TokenExpired",
    "TokenInvalid",
    "ApiKeyInvalid",
    # Authorization errors (403)
    "InsufficientPermissions",
    "ResourceAccessDenied",
    # Validation errors (400)
    "ValidationError",
    "InvalidRequest",
    "InvalidParameter",
    "MissingField",
    # Resource errors (404, 409)
    "NotFound",
    "UserNotFound",
    "AlreadyExists",
    "ResourceLocked",
    # Agent errors
    "AgentNotFound",
    "InvocationFailed",
    "AgentTimeout",
    "AgentConfigurationError",
    # External service errors
    "LLMError",
    "LLMRateLimitError",
    "DatabaseError",
    "DatabaseConnectionError",
    "CacheError",
    # Rate limiting errors
    "RateLimitError",
    "QuotaExceeded",
    # Timeout errors
    "TimeoutError",
    "UpstreamTimeout",
    # Service availability errors
    "ServiceUnavailable",
    "MaintenanceMode",
]
