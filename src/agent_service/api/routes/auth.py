"""
Authentication API routes.

This module provides comprehensive authentication and API key management endpoints:

User Info Routes:
    - GET /auth/me - Get current authenticated user information
    - GET /auth/permissions - Get user roles and permissions

API Key Management Routes (requires authentication):
    - POST /api/v1/auth/api-keys - Create new API key
    - GET /api/v1/auth/api-keys - List user's API keys
    - GET /api/v1/auth/api-keys/{key_id} - Get API key details
    - DELETE /api/v1/auth/api-keys/{key_id} - Revoke API key
    - POST /api/v1/auth/api-keys/{key_id}/rotate - Rotate API key

Token Validation Endpoint:
    - POST /auth/validate - Validate token/API key (for external services)

Security Features:
    - Rate limiting on sensitive endpoints
    - Comprehensive OpenAPI documentation
    - Raw API keys only returned once during creation
    - Proper error handling and validation

Configuration Required:
    1. Database Session: Override get_db_session dependency
    2. Auth Provider: Configure authentication provider in dependencies

Example Configuration (in app.py or startup):
    ```python
    from agent_service.api.routes import auth
    from your_app.database import get_session

    # Override database session dependency
    auth.get_db_session = get_session

    # Or use dependency override in FastAPI:
    app.dependency_overrides[auth.get_db_session] = get_session
    ```
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from agent_service.auth.dependencies import (
    get_current_user,
    get_current_user_any,
)
from agent_service.auth.schemas import UserInfo, AuthProvider
from agent_service.auth.schemas.api_key import (
    APIKeyCreate,
    APIKeyResponse,
    APIKeyInfo,
)
from agent_service.auth.services import APIKeyService
from agent_service.auth.exceptions import AuthorizationError


# Router for user info routes (no prefix - mounted at root level)
router = APIRouter()

# Router for API key management routes (no prefix - will be versioned)
api_keys_router = APIRouter(tags=["API Keys"])


# ============================================================================
# Request/Response Models
# ============================================================================


class UserPermissionsResponse(BaseModel):
    """Response model for user permissions endpoint."""

    model_config = {"str_strip_whitespace": True}

    user_id: str = Field(
        ...,
        description="Unique user identifier",
        examples=["user123", "azure|abc-def-123"]
    )
    roles: List[str] = Field(
        default_factory=list,
        description="User roles for authorization",
        examples=[["admin", "user"], ["viewer"]]
    )
    groups: List[str] = Field(
        default_factory=list,
        description="User groups for authorization",
        examples=[["engineering", "managers"], []]
    )
    scopes: List[str] = Field(
        default_factory=list,
        description="API key scopes (if authenticated via API key)",
        examples=[["read", "write"], ["admin"]]
    )
    provider: str = Field(
        ...,
        description="Authentication provider used",
        examples=["azure_ad", "aws_cognito", "custom"]
    )


class TokenValidationRequest(BaseModel):
    """Request model for token validation endpoint."""

    model_config = {"str_strip_whitespace": True}

    token: str = Field(
        ...,
        description="JWT token or API key to validate",
        min_length=1,
        examples=["eyJhbGciOiJSUzI1...", "sk_test_EXAMPLE_KEY_REPLACE_ME..."]
    )
    token_type: Optional[str] = Field(
        default="bearer",
        description="Type of token: 'bearer' for JWT, 'api_key' for API keys",
        pattern="^(bearer|api_key)$",
        examples=["bearer", "api_key"]
    )


class TokenValidationResponse(BaseModel):
    """Response model for token validation endpoint."""

    model_config = {"str_strip_whitespace": True}

    valid: bool = Field(
        ...,
        description="Whether the token is valid",
        examples=[True, False]
    )
    user_id: Optional[str] = Field(
        default=None,
        description="User ID if token is valid",
        examples=["user123", "azure|abc-def-123"]
    )
    email: Optional[str] = Field(
        default=None,
        description="User email if available",
        examples=["user@example.com"]
    )
    roles: Optional[List[str]] = Field(
        default=None,
        description="User roles if token is valid",
        examples=[["admin", "user"]]
    )
    provider: Optional[str] = Field(
        default=None,
        description="Authentication provider",
        examples=["azure_ad", "custom"]
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if token is invalid",
        examples=["Token expired", "Invalid signature"]
    )


class APIKeyRotateResponse(BaseModel):
    """Response model for API key rotation."""

    model_config = {"str_strip_whitespace": True}

    old_key_id: UUID = Field(
        ...,
        description="ID of the revoked key"
    )
    new_key: APIKeyResponse = Field(
        ...,
        description="New API key details (includes raw key - shown only once)"
    )
    message: str = Field(
        default="API key rotated successfully. Old key revoked, new key created.",
        description="Success message"
    )


# ============================================================================
# Rate Limiting Helpers
# ============================================================================

# Simple in-memory rate limiter (replace with Redis in production)
# This is a placeholder for demonstration - use proper rate limiting middleware
from collections import defaultdict
from datetime import datetime, timedelta
from threading import Lock

_rate_limit_store = defaultdict(list)
_rate_limit_lock = Lock()


def check_rate_limit(
    identifier: str,
    max_requests: int = 10,
    window_seconds: int = 60
) -> bool:
    """
    Simple rate limiter (in-memory).

    In production, replace with Redis-based rate limiting.

    Args:
        identifier: Unique identifier (user_id, IP, etc.)
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds

    Returns:
        True if request is allowed, False if rate limit exceeded
    """
    with _rate_limit_lock:
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window_seconds)

        # Remove old entries
        _rate_limit_store[identifier] = [
            timestamp for timestamp in _rate_limit_store[identifier]
            if timestamp > cutoff
        ]

        # Check limit
        if len(_rate_limit_store[identifier]) >= max_requests:
            return False

        # Add current request
        _rate_limit_store[identifier].append(now)
        return True


def rate_limit_dependency(max_requests: int = 10, window_seconds: int = 60):
    """
    Dependency factory for rate limiting.

    Args:
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds

    Returns:
        Dependency function
    """
    async def rate_limiter(
        user: UserInfo = Depends(get_current_user_any),
    ):
        identifier = f"{user.id}:{user.provider}"

        if not check_rate_limit(identifier, max_requests, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds.",
                headers={"Retry-After": str(window_seconds)},
            )

    return rate_limiter


# Placeholder for database session dependency
# This should be replaced with actual database session from the application
async def get_db_session() -> AsyncSession:
    """
    Get database session for API key operations.

    This is a placeholder that should be overridden by the application.
    """
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Database session not configured. Please configure get_db_session dependency.",
    )


# ============================================================================
# User Info Routes
# ============================================================================


@router.get(
    "/auth/me",
    response_model=UserInfo,
    tags=["Authentication"],
    summary="Get current user information",
    description="""
    Get authenticated user information from JWT token or API key.

    Returns the user's identity, roles, groups, and metadata.
    Supports both JWT (Bearer token) and API key authentication.

    **Authentication Methods:**
    - Bearer token: `Authorization: Bearer <jwt_token>`
    - API key: `X-API-Key: sk_test_EXAMPLE_KEY_REPLACE_ME...`

    **Example Response:**
    ```json
    {
        "id": "user123",
        "email": "user@example.com",
        "name": "John Doe",
        "roles": ["admin", "user"],
        "groups": ["engineering"],
        "provider": "azure_ad",
        "tenant_id": "tenant-123",
        "metadata": {}
    }
    ```
    """,
    responses={
        200: {
            "description": "Current user information",
            "content": {
                "application/json": {
                    "example": {
                        "id": "azure|abc-def-123",
                        "email": "john.doe@company.com",
                        "name": "John Doe",
                        "roles": ["admin", "user"],
                        "groups": ["engineering", "managers"],
                        "provider": "azure_ad",
                        "tenant_id": "company-tenant",
                        "metadata": {}
                    }
                }
            }
        },
        401: {
            "description": "Not authenticated - missing or invalid token/API key"
        }
    }
)
async def get_current_user_info(
    current_user: UserInfo = Depends(get_current_user_any),
) -> UserInfo:
    """
    Get current authenticated user information.

    Returns complete user information including identity, roles, and permissions.
    """
    return current_user


@router.get(
    "/auth/permissions",
    response_model=UserPermissionsResponse,
    tags=["Authentication"],
    summary="Get current user's roles and permissions",
    description="""
    Get the current user's authorization information including roles, groups, and scopes.

    Useful for frontend applications to determine what actions the user can perform.

    **Authentication Methods:**
    - Bearer token: `Authorization: Bearer <jwt_token>`
    - API key: `X-API-Key: sk_test_EXAMPLE_KEY_REPLACE_ME...`

    **Example Response:**
    ```json
    {
        "user_id": "user123",
        "roles": ["admin", "user"],
        "groups": ["engineering"],
        "scopes": ["read", "write"],
        "provider": "azure_ad"
    }
    ```
    """,
    responses={
        200: {
            "description": "User permissions and roles",
            "content": {
                "application/json": {
                    "example": {
                        "user_id": "azure|abc-def-123",
                        "roles": ["admin", "user"],
                        "groups": ["engineering", "managers"],
                        "scopes": [],
                        "provider": "azure_ad"
                    }
                }
            }
        },
        401: {
            "description": "Not authenticated"
        }
    }
)
async def get_user_permissions(
    current_user: UserInfo = Depends(get_current_user_any),
) -> UserPermissionsResponse:
    """
    Get current user's roles and permissions.

    Returns authorization data for the authenticated user.
    """
    # Extract scopes from metadata (for API keys)
    scopes = current_user.metadata.get("scopes", [])

    return UserPermissionsResponse(
        user_id=current_user.id,
        roles=current_user.roles,
        groups=current_user.groups,
        scopes=scopes,
        provider=current_user.provider.value,
    )


# ============================================================================
# Token Validation Endpoint (for external services)
# ============================================================================


@router.post(
    "/auth/validate",
    response_model=TokenValidationResponse,
    tags=["Authentication"],
    summary="Validate a token or API key",
    description="""
    Validate a JWT token or API key and return user information.

    This endpoint is designed for use by external services that need to validate
    tokens without performing the full authentication flow.

    **Rate Limiting:** 100 requests per minute per token

    **Request Body:**
    ```json
    {
        "token": "eyJhbGciOiJSUzI1...",
        "token_type": "bearer"
    }
    ```

    **Example Response (Valid Token):**
    ```json
    {
        "valid": true,
        "user_id": "user123",
        "email": "user@example.com",
        "roles": ["admin"],
        "provider": "azure_ad",
        "error": null
    }
    ```

    **Example Response (Invalid Token):**
    ```json
    {
        "valid": false,
        "user_id": null,
        "email": null,
        "roles": null,
        "provider": null,
        "error": "Token has expired"
    }
    ```
    """,
    responses={
        200: {
            "description": "Validation result (always returns 200, check 'valid' field)",
        },
        429: {
            "description": "Rate limit exceeded"
        }
    }
)
async def validate_token(
    request: TokenValidationRequest,
    # Rate limit: 100 requests per minute
    _rate_limit: None = Depends(rate_limit_dependency(max_requests=100, window_seconds=60)),
) -> TokenValidationResponse:
    """
    Validate a token or API key.

    Returns validation result with user information if valid.
    Always returns 200 - check the 'valid' field in response.
    """
    # Note: In a real implementation, this would use the auth providers
    # For now, return a placeholder response
    # TODO: Implement actual token validation using auth providers

    return TokenValidationResponse(
        valid=False,
        error="Token validation not yet implemented. Please configure auth providers."
    )


# ============================================================================
# API Key Management Routes
# ============================================================================


@api_keys_router.post(
    "",
    response_model=APIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new API key",
    description="""
    Create a new API key for the authenticated user.

    **CRITICAL SECURITY NOTE:** The raw API key is returned ONLY ONCE in this response.
    It is never stored or returned again. Save it immediately.

    **Rate Limiting:** 10 API key creations per hour

    **Request Body:**
    ```json
    {
        "name": "Production API",
        "scopes": ["read", "write"],
        "rate_limit_tier": "pro",
        "expires_in_days": 365
    }
    ```

    **Example Response:**
    ```json
    {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "user_id": "user123",
        "name": "Production API",
        "key": "sk_test_EXAMPLE_KEY_REPLACE_ME",
        "key_prefix": "sk_live",
        "scopes": ["read", "write"],
        "rate_limit_tier": "pro",
        "expires_at": "2025-12-13T00:00:00Z",
        "created_at": "2024-12-13T00:00:00Z"
    }
    ```

    **Scopes:**
    - `read`: Read-only access
    - `write`: Write access
    - `admin`: Administrative access
    - Custom scopes: Define your own

    **Rate Limit Tiers:**
    - `free`: 100 requests/hour
    - `pro`: 1000 requests/hour
    - `enterprise`: Unlimited
    """,
    responses={
        201: {
            "description": "API key created successfully (raw key shown only once)",
        },
        400: {
            "description": "Invalid request parameters"
        },
        401: {
            "description": "Not authenticated"
        },
        429: {
            "description": "Rate limit exceeded"
        }
    }
)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: UserInfo = Depends(get_current_user_any),
    db_session: AsyncSession = Depends(get_db_session),
    # Rate limit: 10 key creations per hour
    _rate_limit: None = Depends(rate_limit_dependency(max_requests=10, window_seconds=3600)),
) -> APIKeyResponse:
    """
    Create a new API key.

    Returns the raw key ONCE - it is never stored or returned again.
    """
    service = APIKeyService(db_session)

    try:
        # Convert user_id to UUID
        user_uuid = UUID(current_user.id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user ID format: {current_user.id}",
        )

    try:
        api_key = await service.create_api_key(
            user_id=user_uuid,
            name=key_data.name,
            scopes=key_data.scopes,
            expires_in_days=key_data.expires_in_days,
            rate_limit_tier=key_data.rate_limit_tier,
            prefix=key_data.prefix,
        )

        # Commit the transaction
        await db_session.commit()

        return api_key

    except ValueError as e:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {str(e)}",
        )


@api_keys_router.get(
    "",
    response_model=List[APIKeyInfo],
    summary="List user's API keys",
    description="""
    List all API keys for the authenticated user.

    Returns metadata for all non-deleted keys. Raw keys are never included.

    **Example Response:**
    ```json
    [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "user_id": "user123",
            "name": "Production API",
            "key_prefix": "sk_live",
            "scopes": ["read", "write"],
            "rate_limit_tier": "pro",
            "expires_at": "2025-12-13T00:00:00Z",
            "last_used_at": "2024-12-12T15:30:00Z",
            "created_at": "2024-12-13T00:00:00Z",
            "updated_at": "2024-12-13T00:00:00Z",
            "is_active": true,
            "is_expired": false
        }
    ]
    ```
    """,
    responses={
        200: {
            "description": "List of user's API keys (no raw keys)"
        },
        401: {
            "description": "Not authenticated"
        }
    }
)
async def list_api_keys(
    current_user: UserInfo = Depends(get_current_user_any),
    db_session: AsyncSession = Depends(get_db_session),
) -> List[APIKeyInfo]:
    """
    List all API keys for the authenticated user.

    Returns metadata only - raw keys are never included.
    """
    service = APIKeyService(db_session)

    try:
        user_uuid = UUID(current_user.id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user ID format: {current_user.id}",
        )

    try:
        keys = await service.list_api_keys(user_uuid)
        return keys
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list API keys: {str(e)}",
        )


@api_keys_router.get(
    "/{key_id}",
    response_model=APIKeyInfo,
    summary="Get API key details",
    description="""
    Get details about a specific API key.

    Returns metadata only - the raw key is never included.
    Only the key owner can access this endpoint.

    **Example Response:**
    ```json
    {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "user_id": "user123",
        "name": "Production API",
        "key_prefix": "sk_live",
        "scopes": ["read", "write"],
        "rate_limit_tier": "pro",
        "expires_at": "2025-12-13T00:00:00Z",
        "last_used_at": "2024-12-12T15:30:00Z",
        "created_at": "2024-12-13T00:00:00Z",
        "updated_at": "2024-12-13T00:00:00Z",
        "is_active": true,
        "is_expired": false
    }
    ```
    """,
    responses={
        200: {
            "description": "API key details (no raw key)"
        },
        401: {
            "description": "Not authenticated"
        },
        403: {
            "description": "Not authorized to access this key"
        },
        404: {
            "description": "API key not found"
        }
    }
)
async def get_api_key(
    key_id: UUID,
    current_user: UserInfo = Depends(get_current_user_any),
    db_session: AsyncSession = Depends(get_db_session),
) -> APIKeyInfo:
    """
    Get details about a specific API key.

    Only the key owner can access this endpoint.
    """
    service = APIKeyService(db_session)

    try:
        user_uuid = UUID(current_user.id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user ID format: {current_user.id}",
        )

    try:
        key_info = await service.get_api_key(key_id, user_uuid)

        if not key_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key {key_id} not found",
            )

        return key_info

    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get API key: {str(e)}",
        )


@api_keys_router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke API key",
    description="""
    Revoke (soft delete) an API key.

    The key is marked as deleted and can no longer be used for authentication.
    The key remains in the database for audit purposes but is no longer active.

    Only the key owner can revoke their keys.

    **Returns:** 204 No Content on success
    """,
    responses={
        204: {
            "description": "API key revoked successfully"
        },
        401: {
            "description": "Not authenticated"
        },
        403: {
            "description": "Not authorized to revoke this key"
        },
        404: {
            "description": "API key not found"
        }
    }
)
async def revoke_api_key(
    key_id: UUID,
    current_user: UserInfo = Depends(get_current_user_any),
    db_session: AsyncSession = Depends(get_db_session),
) -> None:
    """
    Revoke an API key.

    Only the key owner can revoke their keys.
    """
    service = APIKeyService(db_session)

    try:
        user_uuid = UUID(current_user.id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user ID format: {current_user.id}",
        )

    try:
        success = await service.revoke_api_key(key_id, user_uuid)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key {key_id} not found",
            )

        # Commit the transaction
        await db_session.commit()

    except AuthorizationError as e:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except HTTPException:
        await db_session.rollback()
        raise
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke API key: {str(e)}",
        )


@api_keys_router.post(
    "/{key_id}/rotate",
    response_model=APIKeyRotateResponse,
    summary="Rotate API key",
    description="""
    Rotate an API key by creating a new key and revoking the old one.

    The new key inherits all properties from the old key (name, scopes, rate limit tier)
    but has a new cryptographic value.

    **CRITICAL SECURITY NOTE:** The new raw API key is returned ONLY ONCE.
    Save it immediately - it will never be shown again.

    **Rate Limiting:** 10 rotations per hour

    **Example Response:**
    ```json
    {
        "old_key_id": "550e8400-e29b-41d4-a716-446655440000",
        "new_key": {
            "id": "660e8400-e29b-41d4-a716-446655440001",
            "user_id": "user123",
            "name": "Production API",
            "key": "sk_test_EXAMPLE_KEY_REPLACE_ME",
            "key_prefix": "sk_live",
            "scopes": ["read", "write"],
            "rate_limit_tier": "pro",
            "expires_at": "2025-12-13T00:00:00Z",
            "created_at": "2024-12-13T01:00:00Z"
        },
        "message": "API key rotated successfully. Old key revoked, new key created."
    }
    ```
    """,
    responses={
        200: {
            "description": "API key rotated successfully (new raw key shown only once)"
        },
        401: {
            "description": "Not authenticated"
        },
        403: {
            "description": "Not authorized to rotate this key"
        },
        404: {
            "description": "API key not found"
        },
        429: {
            "description": "Rate limit exceeded"
        }
    }
)
async def rotate_api_key(
    key_id: UUID,
    current_user: UserInfo = Depends(get_current_user_any),
    db_session: AsyncSession = Depends(get_db_session),
    # Rate limit: 10 rotations per hour
    _rate_limit: None = Depends(rate_limit_dependency(max_requests=10, window_seconds=3600)),
) -> APIKeyRotateResponse:
    """
    Rotate an API key.

    Creates a new key with same properties and revokes the old one.
    Returns the new raw key ONCE - it is never stored or returned again.
    """
    service = APIKeyService(db_session)

    try:
        user_uuid = UUID(current_user.id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user ID format: {current_user.id}",
        )

    try:
        new_key = await service.rotate_api_key(key_id, user_uuid)

        # Commit the transaction
        await db_session.commit()

        return APIKeyRotateResponse(
            old_key_id=key_id,
            new_key=new_key,
        )

    except ValueError as e:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except AuthorizationError as e:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rotate API key: {str(e)}",
        )


# ============================================================================
# Router Export
# ============================================================================

# Export both routers for registration in main app
__all__ = ["router", "api_keys_router"]
