# FastAPI Authentication Dependencies Usage Guide

This guide demonstrates how to use the authentication and authorization dependencies in your FastAPI application.

## Table of Contents

1. [Setup and Configuration](#setup-and-configuration)
2. [Basic Authentication](#basic-authentication)
3. [Authorization (Roles, Permissions, Scopes)](#authorization)
4. [Multiple Authentication Methods](#multiple-authentication-methods)
5. [Optional Authentication](#optional-authentication)
6. [Complete Examples](#complete-examples)

## Setup and Configuration

### 1. Configure Authentication Provider

```python
from fastapi import FastAPI
from agent_service.auth import (
    create_auth_provider,
    AuthConfig,
    AuthProvider,
    AzureADConfig,
    set_auth_provider,
)

app = FastAPI()

@app.on_event("startup")
async def startup():
    # Configure Azure AD
    config = AuthConfig(
        provider=AuthProvider.AZURE_AD,
        azure_ad=AzureADConfig(
            tenant_id="your-tenant-id",
            client_id="your-client-id",
            validate_issuer=True,
            validate_audience=True,
        )
    )

    # Create and set the global auth provider
    auth_provider = create_auth_provider(config)
    set_auth_provider(auth_provider)
```

### 2. Configure Database Session (for API Keys)

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from agent_service.auth import dependencies

# Create your database engine and session
engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Override the default get_db_session dependency
async def get_db():
    async with async_session() as session:
        yield session

# Set the dependency
dependencies.get_db_session = get_db
```

## Basic Authentication

### JWT Token Authentication

```python
from fastapi import APIRouter, Depends
from agent_service.auth import UserInfo, get_current_user

router = APIRouter()

@router.get("/me")
async def get_current_user_info(user: UserInfo = Depends(get_current_user)):
    """
    Get information about the currently authenticated user.

    Requires: Authorization: Bearer <token>
    """
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "roles": user.roles,
        "provider": user.provider,
    }
```

**Request:**
```bash
curl -X GET http://localhost:8000/me \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### API Key Authentication

```python
from agent_service.auth import get_current_user_from_api_key

@router.get("/api/data")
async def get_data(user: UserInfo = Depends(get_current_user_from_api_key)):
    """
    Get data using API key authentication.

    Requires: X-API-Key: sk_xxxxx
    """
    return {
        "user_id": user.id,
        "scopes": user.metadata.get("scopes", []),
        "rate_limit_tier": user.metadata.get("rate_limit_tier"),
    }
```

**Request:**
```bash
curl -X GET http://localhost:8000/api/data \
  -H "X-API-Key: sk_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
```

## Authorization

### Role-Based Access Control (RBAC)

#### Using require_roles()

```python
from agent_service.auth import require_roles, get_current_user

# Single role required
@router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_roles("admin"))
):
    """
    Delete a user. Only accessible by admins.
    """
    return {"deleted": user_id}

# Any of multiple roles accepted
@router.get("/moderator/reports")
async def get_reports(
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_roles("admin", "moderator"))
):
    """
    Get reports. Accessible by admin OR moderator.
    """
    return {"reports": []}

# All roles required
@router.post("/super/action")
async def super_action(
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_roles("admin", "super_user", require_all=True))
):
    """
    Perform super action. Requires BOTH admin AND super_user roles.
    """
    return {"status": "action performed"}
```

#### Using RoleChecker Class

```python
from agent_service.auth import RoleChecker

# Create reusable role checkers
admin_only = RoleChecker(["admin"])
staff_access = RoleChecker(["admin", "staff", "moderator"])

@router.put("/settings")
async def update_settings(
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(admin_only)
):
    return {"updated": True}
```

### Permission-Based Access Control

```python
from agent_service.auth import require_permissions

@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_permissions("users:write"))
):
    """
    Update a user. Requires 'users:write' permission.
    """
    return {"updated": user_id}

@router.delete("/users/{user_id}")
async def delete_user_with_permissions(
    user_id: str,
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_permissions("users:delete", "users:admin", require_all=False))
):
    """
    Delete a user. Requires 'users:delete' OR 'users:admin' permission.
    """
    return {"deleted": user_id}
```

### API Key Scope Checking

```python
from agent_service.auth import require_scopes, get_current_user_from_api_key

@router.post("/api/data")
async def create_data(
    user: UserInfo = Depends(get_current_user_from_api_key),
    _: None = Depends(require_scopes("write"))
):
    """
    Create data using API key. Requires 'write' scope.
    """
    return {"created": True}

@router.get("/api/admin/metrics")
async def get_admin_metrics(
    user: UserInfo = Depends(get_current_user_from_api_key),
    _: None = Depends(require_scopes("admin", "read", require_all=True))
):
    """
    Get admin metrics. Requires BOTH 'admin' AND 'read' scopes.
    """
    return {"metrics": {}}
```

## Multiple Authentication Methods

### Accept Either JWT or API Key

```python
from agent_service.auth import get_current_user_any

@router.get("/flexible")
async def flexible_auth_route(user: UserInfo = Depends(get_current_user_any)):
    """
    This endpoint accepts either:
    - Authorization: Bearer <token>
    - X-API-Key: sk_xxxxx
    """
    return {
        "authenticated": True,
        "provider": user.provider,
        "user_id": user.id,
    }
```

**Request with JWT:**
```bash
curl -X GET http://localhost:8000/flexible \
  -H "Authorization: Bearer eyJhbGciOi..."
```

**Request with API Key:**
```bash
curl -X GET http://localhost:8000/flexible \
  -H "X-API-Key: sk_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
```

## Optional Authentication

### Endpoints with Different Behavior for Authenticated Users

```python
from typing import Optional
from agent_service.auth import optional_auth

@router.get("/public")
async def public_with_optional_auth(user: Optional[UserInfo] = Depends(optional_auth)):
    """
    Public endpoint that changes behavior based on authentication.
    """
    if user:
        return {
            "message": f"Hello, {user.email or user.id}",
            "authenticated": True,
            "user_id": user.id,
        }

    return {
        "message": "Hello, anonymous user",
        "authenticated": False,
    }
```

## Complete Examples

### Example 1: Protected Admin Route with Role Check

```python
from fastapi import APIRouter, HTTPException, status
from agent_service.auth import UserInfo, get_current_user, require_roles

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/users/{user_id}/ban")
async def ban_user(
    user_id: str,
    reason: str,
    admin: UserInfo = Depends(get_current_user),
    _: None = Depends(require_roles("admin"))
):
    """
    Ban a user from the platform.

    Requires:
    - Valid JWT token
    - 'admin' role
    """
    # Admin logic here
    return {
        "user_id": user_id,
        "banned_by": admin.id,
        "reason": reason,
        "status": "banned",
    }
```

### Example 2: API Key with Scope Requirements

```python
from pydantic import BaseModel
from agent_service.auth import get_current_user_from_api_key, require_scopes

router = APIRouter(prefix="/api/v1", tags=["api"])

class DataCreate(BaseModel):
    name: str
    value: float

@router.post("/data")
async def create_data(
    data: DataCreate,
    user: UserInfo = Depends(get_current_user_from_api_key),
    _: None = Depends(require_scopes("write"))
):
    """
    Create data via API key.

    Requires:
    - Valid API key with 'write' scope
    """
    return {
        "id": "data-123",
        "created_by": user.id,
        "rate_limit_tier": user.metadata.get("rate_limit_tier"),
        **data.dict(),
    }
```

### Example 3: Flexible Authentication with Permission Check

```python
from agent_service.auth import get_current_user_any, PermissionChecker

# Create reusable permission checker
read_permission = PermissionChecker(["data:read", "data:admin"], require_all=False)

@router.get("/data/{data_id}")
async def get_data(
    data_id: str,
    user: UserInfo = Depends(get_current_user_any),
    _: None = Depends(read_permission)
):
    """
    Get data by ID.

    Accepts:
    - JWT token OR API key

    Requires:
    - 'data:read' OR 'data:admin' permission
    """
    return {
        "id": data_id,
        "name": "Sample Data",
        "accessed_by": user.id,
        "auth_method": "api_key" if user.provider == "custom" else "jwt",
    }
```

### Example 4: User-Specific Resource Access

```python
@router.get("/users/{user_id}/profile")
async def get_user_profile(
    user_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Get user profile. Users can only access their own profile unless they're an admin.
    """
    # Check if user is accessing their own profile or is an admin
    if current_user.id != user_id and not current_user.has_role("admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own profile"
        )

    return {
        "user_id": user_id,
        "profile": "...",
    }
```

### Example 5: Combined Authorization Checks

```python
from agent_service.auth import RoleChecker, ScopeChecker

# Endpoint requiring specific role AND scope
admin_write_scope = ScopeChecker(["write", "admin"], require_all=True)
admin_role = RoleChecker(["admin"])

@router.put("/system/config")
async def update_system_config(
    config: dict,
    user: UserInfo = Depends(get_current_user_any),
    _role: None = Depends(admin_role),
    _scope: None = Depends(admin_write_scope)
):
    """
    Update system configuration.

    Requires:
    - JWT with 'admin' role OR API key with 'admin' + 'write' scopes
    """
    return {
        "updated_by": user.id,
        "config": config,
    }
```

## Error Handling

All dependencies properly return HTTP status codes:

- **401 Unauthorized**: Missing, invalid, or expired authentication
- **403 Forbidden**: Valid authentication but insufficient permissions/roles/scopes

### Example Error Responses

**401 - No token provided:**
```json
{
  "detail": "Not authenticated"
}
```
Headers: `WWW-Authenticate: Bearer`

**401 - Invalid API key:**
```json
{
  "detail": "Invalid or expired API key"
}
```
Headers: `WWW-Authenticate: ApiKey realm="X-API-Key"`

**403 - Missing role:**
```json
{
  "detail": "Required roles: admin"
}
```

**403 - Missing scope:**
```json
{
  "detail": "Missing required scopes: write, admin"
}
```

## Best Practices

1. **Use `get_current_user_any` for flexible endpoints** that should accept both JWT and API keys
2. **Use specific dependencies** (`get_current_user` or `get_current_user_from_api_key`) when you need to enforce a specific auth method
3. **Combine role/permission checks** by stacking multiple `Depends()` in your route
4. **Create reusable checker instances** for common authorization patterns
5. **Use `optional_auth`** for public endpoints that personalize for authenticated users
6. **Always validate resource ownership** in addition to role checks when appropriate

## Testing

```python
from fastapi.testclient import TestClient
from agent_service.auth import set_auth_provider

# Mock auth provider for testing
class MockAuthProvider:
    def get_user_info(self, token):
        return UserInfo(
            id="test-user",
            email="test@example.com",
            roles=["admin"],
            provider=AuthProvider.CUSTOM,
        )

# In your test setup
def setup_test_auth():
    set_auth_provider(MockAuthProvider())

def test_protected_route():
    client = TestClient(app)
    response = client.get(
        "/me",
        headers={"Authorization": "Bearer fake-token"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
```
