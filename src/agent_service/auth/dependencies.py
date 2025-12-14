"""
FastAPI authentication and authorization dependencies.

This module provides FastAPI dependency injection functions and classes for:
- Token extraction from HTTP headers
- User authentication via JWT or API key
- Role-based access control (RBAC)
- Permission-based authorization
- API key scope verification

Usage:
    Basic authentication:
        >>> from fastapi import Depends, APIRouter
        >>> from agent_service.auth.dependencies import get_current_user
        >>> from agent_service.auth.schemas import UserInfo
        >>>
        >>> router = APIRouter()
        >>>
        >>> @router.get("/protected")
        >>> async def protected_route(user: UserInfo = Depends(get_current_user)):
        ...     return {"user_id": user.id, "email": user.email}

    Role-based access:
        >>> from agent_service.auth.dependencies import require_roles
        >>>
        >>> @router.post("/admin")
        >>> async def admin_only(user: UserInfo = Depends(require_roles("admin"))):
        ...     return {"message": "Admin access granted"}

    Multiple authentication methods:
        >>> from agent_service.auth.dependencies import get_current_user_any
        >>>
        >>> @router.get("/flexible")
        >>> async def flexible_auth(user: UserInfo = Depends(get_current_user_any)):
        ...     return {"authenticated_via": user.provider}

Security Features:
    - JWT validation with Azure AD and AWS Cognito support
    - API key authentication with secure hashing
    - Proper HTTP 401/403 responses with WWW-Authenticate headers
    - Role, permission, and scope checking
    - Optional authentication support
"""

from typing import Callable, Optional, List, Set
from functools import wraps

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import UserInfo, AuthProvider
from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    InvalidTokenError,
    TokenExpiredError,
)
from .providers import IAuthProvider, create_auth_provider
from .services import APIKeyService


# Security schemes for OpenAPI documentation
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    auto_error=False,  # Don't auto-error to support multiple auth methods
)

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,  # Don't auto-error to support multiple auth methods
)


# Global auth provider instance (should be configured at startup)
_auth_provider: Optional[IAuthProvider] = None


def set_auth_provider(provider: IAuthProvider) -> None:
    """
    Set the global authentication provider.

    This should be called once during application startup to configure
    the authentication provider (Azure AD, Cognito, etc.).

    Args:
        provider: The authentication provider instance to use

    Example:
        >>> from agent_service.auth import create_auth_provider, AuthConfig, AuthProvider
        >>> from agent_service.auth.dependencies import set_auth_provider
        >>>
        >>> # In your FastAPI startup event
        >>> @app.on_event("startup")
        >>> async def startup():
        ...     config = AuthConfig(provider=AuthProvider.AZURE_AD, ...)
        ...     auth_provider = create_auth_provider(config)
        ...     set_auth_provider(auth_provider)
    """
    global _auth_provider
    _auth_provider = provider


def get_auth_provider() -> IAuthProvider:
    """
    Get the configured authentication provider.

    Returns:
        The global authentication provider instance

    Raises:
        HTTPException: If auth provider is not configured
    """
    if _auth_provider is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication provider not configured",
        )
    return _auth_provider


# Database session dependency (should be overridden by application)
async def get_db_session() -> AsyncSession:
    """
    Get database session for API key validation.

    This is a placeholder that should be overridden by the application
    with its actual database session dependency.

    Raises:
        HTTPException: If database session is not configured

    Note:
        Override this dependency in your FastAPI app:
        >>> from agent_service.auth import dependencies
        >>> dependencies.get_db_session = your_actual_get_db_function
    """
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Database session not configured",
    )


# ============================================================================
# Token Extraction Functions
# ============================================================================


def get_token_from_header(authorization: str = Header(None)) -> Optional[str]:
    """
    Extract Bearer token from Authorization header.

    Expects header format: "Bearer <token>"

    Args:
        authorization: Authorization header value

    Returns:
        Token string if valid Bearer token found, None otherwise

    Example:
        >>> token = get_token_from_header("Bearer eyJhbGciOi...")
        >>> # token = "eyJhbGciOi..."
    """
    if not authorization:
        return None

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]


def get_api_key_from_header(x_api_key: str = Header(None)) -> Optional[str]:
    """
    Extract API key from X-API-Key header.

    Args:
        x_api_key: X-API-Key header value

    Returns:
        API key string if present, None otherwise

    Example:
        >>> api_key = get_api_key_from_header("sk_abc123...")
        >>> # api_key = "sk_abc123..."
    """
    return x_api_key if x_api_key else None


# ============================================================================
# Authentication Dependencies
# ============================================================================


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    provider: IAuthProvider = Depends(get_auth_provider),
) -> UserInfo:
    """
    Validate JWT token and return authenticated user information.

    This dependency validates the JWT token using the configured authentication
    provider (Azure AD or Cognito) and returns the user information.

    Args:
        token: JWT token from Authorization header
        provider: Authentication provider instance

    Returns:
        UserInfo with user identity and authorization data

    Raises:
        HTTPException: 401 if token is missing, invalid, or expired

    Example:
        >>> @router.get("/me")
        >>> async def get_me(user: UserInfo = Depends(get_current_user)):
        ...     return {"id": user.id, "email": user.email}
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_info = provider.get_user_info(token)
        return user_info

    except TokenExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token has expired: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_from_api_key(
    api_key: Optional[str] = Depends(api_key_header),
    db_session: AsyncSession = Depends(get_db_session),
) -> UserInfo:
    """
    Validate API key and return authenticated user information.

    This dependency validates the API key against the database and returns
    the user information associated with the key.

    Args:
        api_key: API key from X-API-Key header
        db_session: Database session for key validation

    Returns:
        UserInfo with user identity and API key scopes

    Raises:
        HTTPException: 401 if API key is missing, invalid, or expired

    Example:
        >>> @router.get("/api/data")
        >>> async def get_data(user: UserInfo = Depends(get_current_user_from_api_key)):
        ...     return {"user_id": user.id}
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": 'ApiKey realm="X-API-Key"'},
        )

    try:
        # Validate the API key
        api_key_service = APIKeyService(db_session)
        validation = await api_key_service.validate_api_key(api_key)

        if not validation:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired API key",
                headers={"WWW-Authenticate": 'ApiKey realm="X-API-Key"'},
            )

        # Create UserInfo from API key validation
        # Note: API keys don't have email/name, so we use the user_id
        return UserInfo(
            id=str(validation.user_id),
            email=None,
            name=None,
            roles=validation.scopes,  # Scopes map to roles for API keys
            groups=[],
            provider=AuthProvider.CUSTOM,  # API keys are custom auth
            metadata={
                "api_key_id": str(validation.id),
                "rate_limit_tier": validation.rate_limit_tier,
                "scopes": validation.scopes,
            },
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key validation failed",
            headers={"WWW-Authenticate": 'ApiKey realm="X-API-Key"'},
        )


async def get_current_user_any(
    token: Optional[str] = Depends(oauth2_scheme),
    api_key: Optional[str] = Depends(api_key_header),
    provider: IAuthProvider = Depends(get_auth_provider),
    db_session: AsyncSession = Depends(get_db_session),
) -> UserInfo:
    """
    Authenticate user via either JWT token or API key.

    This dependency tries JWT authentication first, then API key authentication.
    It's useful for endpoints that should accept multiple authentication methods.

    Args:
        token: JWT token from Authorization header (optional)
        api_key: API key from X-API-Key header (optional)
        provider: Authentication provider instance
        db_session: Database session for API key validation

    Returns:
        UserInfo from whichever authentication method succeeded

    Raises:
        HTTPException: 401 if both authentication methods fail or are missing

    Example:
        >>> @router.get("/flexible")
        >>> async def flexible_route(user: UserInfo = Depends(get_current_user_any)):
        ...     return {"authenticated": True, "provider": user.provider}
    """
    # Try JWT token first
    if token:
        try:
            user_info = provider.get_user_info(token)
            return user_info
        except (AuthenticationError, InvalidTokenError, TokenExpiredError):
            # If token provided but invalid, don't fall back to API key
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Try API key second
    if api_key:
        try:
            api_key_service = APIKeyService(db_session)
            validation = await api_key_service.validate_api_key(api_key)

            if validation:
                return UserInfo(
                    id=str(validation.user_id),
                    email=None,
                    name=None,
                    roles=validation.scopes,
                    groups=[],
                    provider=AuthProvider.CUSTOM,
                    metadata={
                        "api_key_id": str(validation.id),
                        "rate_limit_tier": validation.rate_limit_tier,
                        "scopes": validation.scopes,
                    },
                )
        except Exception:
            pass  # Fall through to error below

    # Neither authentication method provided or succeeded
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required: provide Bearer token or API key",
        headers={"WWW-Authenticate": 'Bearer, ApiKey realm="X-API-Key"'},
    )


async def optional_auth(
    token: Optional[str] = Depends(oauth2_scheme),
    api_key: Optional[str] = Depends(api_key_header),
    provider: IAuthProvider = Depends(get_auth_provider),
    db_session: AsyncSession = Depends(get_db_session),
) -> Optional[UserInfo]:
    """
    Optional authentication - returns user if authenticated, None otherwise.

    This dependency is useful for endpoints that have different behavior for
    authenticated vs anonymous users, but don't require authentication.

    Args:
        token: JWT token from Authorization header (optional)
        api_key: API key from X-API-Key header (optional)
        provider: Authentication provider instance
        db_session: Database session for API key validation

    Returns:
        UserInfo if authenticated via any method, None if no auth provided

    Example:
        >>> @router.get("/optional")
        >>> async def optional_route(user: Optional[UserInfo] = Depends(optional_auth)):
        ...     if user:
        ...         return {"message": f"Hello, {user.email}"}
        ...     return {"message": "Hello, anonymous"}
    """
    # Try JWT token
    if token:
        try:
            user_info = provider.get_user_info(token)
            return user_info
        except (AuthenticationError, InvalidTokenError, TokenExpiredError):
            pass  # Invalid token, treat as unauthenticated

    # Try API key
    if api_key:
        try:
            api_key_service = APIKeyService(db_session)
            validation = await api_key_service.validate_api_key(api_key)

            if validation:
                return UserInfo(
                    id=str(validation.user_id),
                    email=None,
                    name=None,
                    roles=validation.scopes,
                    groups=[],
                    provider=AuthProvider.CUSTOM,
                    metadata={
                        "api_key_id": str(validation.id),
                        "rate_limit_tier": validation.rate_limit_tier,
                        "scopes": validation.scopes,
                    },
                )
        except Exception:
            pass  # Invalid API key, treat as unauthenticated

    # No valid authentication found
    return None


# ============================================================================
# Authorization Helper Classes
# ============================================================================


class RoleChecker:
    """
    FastAPI dependency for role-based access control.

    Verifies that the authenticated user has at least one of the required roles.

    Example:
        >>> role_checker = RoleChecker(["admin", "moderator"])
        >>>
        >>> @router.delete("/users/{user_id}")
        >>> async def delete_user(
        ...     user_id: str,
        ...     user: UserInfo = Depends(get_current_user),
        ...     _: None = Depends(role_checker)
        ... ):
        ...     # Only admins and moderators can access this
        ...     return {"deleted": user_id}
    """

    def __init__(self, allowed_roles: List[str], require_all: bool = False):
        """
        Initialize role checker.

        Args:
            allowed_roles: List of roles that are allowed access
            require_all: If True, user must have ALL roles; if False, ANY role (default)
        """
        self.allowed_roles = set(allowed_roles)
        self.require_all = require_all

    async def __call__(self, user: UserInfo = Depends(get_current_user)) -> None:
        """
        Verify user has required roles.

        Args:
            user: Authenticated user information

        Raises:
            HTTPException: 403 if user lacks required roles
        """
        user_roles = set(user.roles)

        if self.require_all:
            # User must have ALL required roles
            if not self.allowed_roles.issubset(user_roles):
                missing_roles = self.allowed_roles - user_roles
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required roles: {', '.join(missing_roles)}",
                )
        else:
            # User must have AT LEAST ONE required role
            if not self.allowed_roles.intersection(user_roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Required roles: {', '.join(self.allowed_roles)}",
                )


class PermissionChecker:
    """
    FastAPI dependency for permission-based access control.

    Verifies that the authenticated user has specific permissions.
    Permissions are checked against user roles and groups.

    Example:
        >>> permission_checker = PermissionChecker(["users:write", "users:delete"])
        >>>
        >>> @router.put("/users/{user_id}")
        >>> async def update_user(
        ...     user_id: str,
        ...     user: UserInfo = Depends(get_current_user),
        ...     _: None = Depends(permission_checker)
        ... ):
        ...     # Only users with write permission can access this
        ...     return {"updated": user_id}
    """

    def __init__(self, required_permissions: List[str], require_all: bool = True):
        """
        Initialize permission checker.

        Args:
            required_permissions: List of permissions required for access
            require_all: If True, user needs ALL permissions; if False, ANY permission
        """
        self.required_permissions = set(required_permissions)
        self.require_all = require_all

    async def __call__(self, user: UserInfo = Depends(get_current_user)) -> None:
        """
        Verify user has required permissions.

        Permissions can be defined in user roles (e.g., "admin" role grants all permissions)
        or in user metadata.

        Args:
            user: Authenticated user information

        Raises:
            HTTPException: 403 if user lacks required permissions
        """
        # Extract user permissions from metadata
        user_permissions = set(user.metadata.get("permissions", []))

        # Admin role grants all permissions
        if "admin" in user.roles:
            return

        if self.require_all:
            # User must have ALL required permissions
            if not self.required_permissions.issubset(user_permissions):
                missing_perms = self.required_permissions - user_permissions
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permissions: {', '.join(missing_perms)}",
                )
        else:
            # User must have AT LEAST ONE required permission
            if not self.required_permissions.intersection(user_permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Required permissions: {', '.join(self.required_permissions)}",
                )


class ScopeChecker:
    """
    FastAPI dependency for API key scope verification.

    Verifies that the API key has the required scopes for the operation.
    This is specifically for API key authentication.

    Example:
        >>> scope_checker = ScopeChecker(["read", "write"])
        >>>
        >>> @router.post("/data")
        >>> async def create_data(
        ...     user: UserInfo = Depends(get_current_user_from_api_key),
        ...     _: None = Depends(scope_checker)
        ... ):
        ...     # Only API keys with write scope can access this
        ...     return {"created": True}
    """

    def __init__(self, required_scopes: List[str], require_all: bool = True):
        """
        Initialize scope checker.

        Args:
            required_scopes: List of scopes required for access
            require_all: If True, key needs ALL scopes; if False, ANY scope
        """
        self.required_scopes = set(required_scopes)
        self.require_all = require_all

    async def __call__(
        self, user: UserInfo = Depends(get_current_user_any)
    ) -> None:
        """
        Verify API key has required scopes.

        Args:
            user: Authenticated user information (from API key or JWT)

        Raises:
            HTTPException: 403 if API key lacks required scopes
        """
        # Get scopes from metadata (for API keys) or roles (fallback)
        api_key_scopes = set(user.metadata.get("scopes", user.roles))

        if self.require_all:
            # API key must have ALL required scopes
            if not self.required_scopes.issubset(api_key_scopes):
                missing_scopes = self.required_scopes - api_key_scopes
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required scopes: {', '.join(missing_scopes)}",
                )
        else:
            # API key must have AT LEAST ONE required scope
            if not self.required_scopes.intersection(api_key_scopes):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Required scopes: {', '.join(self.required_scopes)}",
                )


# ============================================================================
# Authorization Dependency Factories
# ============================================================================


def require_roles(*roles: str, require_all: bool = False) -> RoleChecker:
    """
    Create a dependency that requires specific roles.

    This is a convenience function for creating RoleChecker instances.

    Args:
        *roles: Variable number of role names required
        require_all: If True, user must have ALL roles; if False, ANY role (default)

    Returns:
        RoleChecker dependency instance

    Example:
        >>> @router.post("/admin/settings")
        >>> async def update_settings(
        ...     user: UserInfo = Depends(get_current_user),
        ...     _: None = Depends(require_roles("admin"))
        ... ):
        ...     return {"message": "Settings updated"}
        >>>
        >>> @router.get("/moderator/reports")
        >>> async def get_reports(
        ...     user: UserInfo = Depends(get_current_user),
        ...     _: None = Depends(require_roles("admin", "moderator"))
        ... ):
        ...     # Accessible by admin OR moderator
        ...     return {"reports": []}
    """
    return RoleChecker(list(roles), require_all=require_all)


def require_permissions(
    *permissions: str, require_all: bool = True
) -> PermissionChecker:
    """
    Create a dependency that requires specific permissions.

    This is a convenience function for creating PermissionChecker instances.

    Args:
        *permissions: Variable number of permission names required
        require_all: If True, user needs ALL permissions; if False, ANY permission

    Returns:
        PermissionChecker dependency instance

    Example:
        >>> @router.delete("/users/{user_id}")
        >>> async def delete_user(
        ...     user_id: str,
        ...     user: UserInfo = Depends(get_current_user),
        ...     _: None = Depends(require_permissions("users:delete"))
        ... ):
        ...     return {"deleted": user_id}
    """
    return PermissionChecker(list(permissions), require_all=require_all)


def require_scopes(*scopes: str, require_all: bool = True) -> ScopeChecker:
    """
    Create a dependency that requires specific API key scopes.

    This is a convenience function for creating ScopeChecker instances.

    Args:
        *scopes: Variable number of scope names required
        require_all: If True, key needs ALL scopes; if False, ANY scope

    Returns:
        ScopeChecker dependency instance

    Example:
        >>> @router.post("/api/data")
        >>> async def create_data(
        ...     user: UserInfo = Depends(get_current_user_from_api_key),
        ...     _: None = Depends(require_scopes("write"))
        ... ):
        ...     return {"created": True}
        >>>
        >>> @router.get("/api/admin")
        >>> async def admin_api(
        ...     user: UserInfo = Depends(get_current_user_from_api_key),
        ...     _: None = Depends(require_scopes("admin", "read", require_all=True))
        ... ):
        ...     # Requires BOTH admin AND read scopes
        ...     return {"data": []}
    """
    return ScopeChecker(list(scopes), require_all=require_all)
