"""
Authentication and authorization module.

This module provides a unified authentication interface supporting multiple
identity providers including Azure AD and AWS Cognito, as well as API key
authentication for service-to-service and programmatic access.

Key Features:
- Multiple authentication providers (Azure AD, AWS Cognito)
- JWT token validation with caching
- API key authentication with secure hashing
- Role and group-based authorization
- Token refresh support
- Extensible provider system

Basic Usage:
    >>> from agent_service.auth import create_auth_provider, AuthConfig, AuthProvider, AzureADConfig
    >>>
    >>> # Configure Azure AD authentication
    >>> config = AuthConfig(
    ...     provider=AuthProvider.AZURE_AD,
    ...     azure_ad=AzureADConfig(
    ...         tenant_id="your-tenant-id",
    ...         client_id="your-client-id"
    ...     )
    ... )
    >>>
    >>> # Create provider and verify token
    >>> auth_provider = create_auth_provider(config)
    >>> user_info = auth_provider.get_user_info(token)
    >>>
    >>> # Check user permissions
    >>> if user_info.has_role("admin"):
    ...     print("User is an admin")

Advanced Usage with Cognito:
    >>> from agent_service.auth import create_auth_provider, AuthConfig, AuthProvider, CognitoConfig
    >>>
    >>> config = AuthConfig(
    ...     provider=AuthProvider.AWS_COGNITO,
    ...     cognito=CognitoConfig(
    ...         region="us-east-1",
    ...         user_pool_id="us-east-1_XXXXXXXXX",
    ...         client_id="your-client-id"
    ...     )
    ... )
    >>>
    >>> auth_provider = create_auth_provider(config)
    >>> token_payload = auth_provider.verify_token(token)
    >>> print(f"Token expires in: {token_payload.expires_in} seconds")

API Key Authentication:
    >>> from agent_service.auth import APIKeyService
    >>> from sqlalchemy.ext.asyncio import AsyncSession
    >>>
    >>> # Create an API key
    >>> service = APIKeyService(session)
    >>> key_response = await service.create_api_key(
    ...     user_id=user_uuid,
    ...     name="Production API",
    ...     scopes=["read", "write"],
    ...     expires_in_days=365
    ... )
    >>> print(f"Save this key: {key_response.key}")  # Show ONCE
    >>>
    >>> # Validate an API key
    >>> validation = await service.validate_api_key(raw_key)
    >>> if validation:
    ...     print(f"Valid key for user {validation.user_id}")
"""

import logging

# Import exceptions
from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    InvalidTokenError,
    ProviderConfigError,
    TokenExpiredError,
)

# Import schemas
from .schemas import (
    AuthConfig,
    AuthProvider,
    AzureADConfig,
    CognitoConfig,
    TokenPayload,
    TokenResponse,
    UserInfo,
)

# Import provider interfaces and factory
from .providers import (
    IAuthProvider,
    AzureADAuthProvider,
    CognitoAuthProvider,
    create_auth_provider,
    register_provider,
    list_providers,
)

# Import API key functionality
from .api_key import (
    generate_api_key,
    hash_api_key,
    verify_api_key,
    parse_api_key,
    validate_api_key_format,
    APIKeyParts as APIKeyPartsUtil,
)

# Import API key models
from .models import (
    APIKey,
    RateLimitTier,
)

# Import API key schemas (rename to avoid conflict)
from .schemas.api_key import (
    APIKeyCreate,
    APIKeyResponse,
    APIKeyInfo,
    APIKeyParts as APIKeyPartsSchema,
    APIKeyUpdate,
    APIKeyValidation,
)

# Import API key service
from .services import (
    APIKeyService,
)

# Import FastAPI dependencies
from .dependencies import (
    # Security schemes
    oauth2_scheme,
    api_key_header,
    # Setup functions
    set_auth_provider,
    get_auth_provider,
    get_db_session,
    # Token extraction
    get_token_from_header,
    get_api_key_from_header,
    # Authentication dependencies
    get_current_user,
    get_current_user_from_api_key,
    get_current_user_any,
    optional_auth,
    # Authorization classes
    RoleChecker,
    PermissionChecker,
    ScopeChecker,
    # Authorization factories
    require_roles,
    require_permissions,
    require_scopes,
)

# Configure logging for the auth module
logger = logging.getLogger(__name__)

# Version information
__version__ = "1.0.0"

# Public API
__all__ = [
    # Factory functions
    "create_auth_provider",
    "register_provider",
    "list_providers",
    # Provider interfaces
    "IAuthProvider",
    "AzureADAuthProvider",
    "CognitoAuthProvider",
    # Configuration schemas
    "AuthConfig",
    "AuthProvider",
    "AzureADConfig",
    "CognitoConfig",
    # Data models
    "TokenPayload",
    "TokenResponse",
    "UserInfo",
    # Exceptions
    "AuthenticationError",
    "AuthorizationError",
    "InvalidTokenError",
    "TokenExpiredError",
    "ProviderConfigError",
    # API Key utilities
    "generate_api_key",
    "hash_api_key",
    "verify_api_key",
    "parse_api_key",
    "validate_api_key_format",
    "APIKeyPartsUtil",
    # API Key models
    "APIKey",
    "RateLimitTier",
    # API Key schemas
    "APIKeyCreate",
    "APIKeyResponse",
    "APIKeyInfo",
    "APIKeyPartsSchema",
    "APIKeyUpdate",
    "APIKeyValidation",
    # API Key service
    "APIKeyService",
    # FastAPI dependencies - Security schemes
    "oauth2_scheme",
    "api_key_header",
    # FastAPI dependencies - Setup
    "set_auth_provider",
    "get_auth_provider",
    "get_db_session",
    # FastAPI dependencies - Token extraction
    "get_token_from_header",
    "get_api_key_from_header",
    # FastAPI dependencies - Authentication
    "get_current_user",
    "get_current_user_from_api_key",
    "get_current_user_any",
    "optional_auth",
    # FastAPI dependencies - Authorization classes
    "RoleChecker",
    "PermissionChecker",
    "ScopeChecker",
    # FastAPI dependencies - Authorization factories
    "require_roles",
    "require_permissions",
    "require_scopes",
    # Version
    "__version__",
]


def configure_logging(
    level: int = logging.INFO,
    format_string: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
) -> None:
    """
    Configure logging for the authentication module.

    Args:
        level: Logging level (e.g., logging.DEBUG, logging.INFO)
        format_string: Log message format string

    Example:
        >>> from agent_service.auth import configure_logging
        >>> import logging
        >>>
        >>> configure_logging(level=logging.DEBUG)
    """
    handler = logging.StreamHandler()
    handler.setLevel(level)
    formatter = logging.Formatter(format_string)
    handler.setFormatter(formatter)

    logger.setLevel(level)
    logger.addHandler(handler)

    logger.info(f"Authentication module logging configured at level: {logging.getLevelName(level)}")
