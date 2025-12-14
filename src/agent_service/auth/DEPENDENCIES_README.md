# FastAPI Authentication Dependencies

Comprehensive FastAPI dependency injection system for authentication and authorization supporting multiple identity providers (Azure AD, AWS Cognito) and API key authentication.

## Features

- **Multiple Authentication Methods**:
  - JWT token validation (Azure AD, AWS Cognito)
  - API key authentication with secure hashing
  - Flexible authentication (accept either JWT or API key)
  - Optional authentication support

- **Authorization Controls**:
  - Role-Based Access Control (RBAC)
  - Permission-based authorization
  - API key scope verification
  - Reusable checker classes

- **Security Best Practices**:
  - Proper HTTP 401/403 status codes
  - WWW-Authenticate headers
  - Constant-time hash comparison
  - Secure token validation

## Installation

The dependencies module is part of the `agent_service.auth` package:

```python
from agent_service.auth import (
    # Authentication dependencies
    get_current_user,
    get_current_user_from_api_key,
    get_current_user_any,
    optional_auth,

    # Authorization
    require_roles,
    require_permissions,
    require_scopes,
    RoleChecker,
    PermissionChecker,
    ScopeChecker,

    # Setup
    set_auth_provider,
    oauth2_scheme,
    api_key_header,
)
```

## Quick Start

### 1. Application Setup

Configure the authentication provider during application startup:

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
    # Configure authentication provider
    config = AuthConfig(
        provider=AuthProvider.AZURE_AD,
        azure_ad=AzureADConfig(
            tenant_id="your-tenant-id",
            client_id="your-client-id",
        )
    )

    auth_provider = create_auth_provider(config)
    set_auth_provider(auth_provider)
```

### 2. Configure Database Session (for API Keys)

```python
from agent_service.auth import dependencies

# Override the database session dependency
dependencies.get_db_session = your_actual_get_db_function
```

### 3. Use in Routes

```python
from fastapi import APIRouter, Depends
from agent_service.auth import UserInfo, get_current_user

router = APIRouter()

@router.get("/me")
async def get_me(user: UserInfo = Depends(get_current_user)):
    return {"user_id": user.id, "email": user.email}
```

## API Reference

### Authentication Dependencies

#### `get_current_user(token, provider) -> UserInfo`

Validates JWT token and returns authenticated user information.

**Parameters:**
- `token`: JWT token from Authorization header (Bearer scheme)
- `provider`: Authentication provider instance (auto-injected)

**Returns:** `UserInfo` with user identity and authorization data

**Raises:**
- `HTTPException 401`: Missing, invalid, or expired token

**Example:**
```python
@router.get("/protected")
async def protected_route(user: UserInfo = Depends(get_current_user)):
    return {"user_id": user.id}
```

**Request:**
```bash
curl -X GET http://localhost:8000/protected \
  -H "Authorization: Bearer eyJhbGciOi..."
```

---

#### `get_current_user_from_api_key(api_key, db_session) -> UserInfo`

Validates API key and returns authenticated user information.

**Parameters:**
- `api_key`: API key from X-API-Key header
- `db_session`: Database session (auto-injected)

**Returns:** `UserInfo` with user identity and API key scopes

**Raises:**
- `HTTPException 401`: Missing, invalid, or expired API key

**Example:**
```python
@router.get("/api/data")
async def get_data(user: UserInfo = Depends(get_current_user_from_api_key)):
    return {"user_id": user.id, "scopes": user.metadata["scopes"]}
```

**Request:**
```bash
curl -X GET http://localhost:8000/api/data \
  -H "X-API-Key: sk_abc123..."
```

---

#### `get_current_user_any(token, api_key, provider, db_session) -> UserInfo`

Authenticates user via either JWT token or API key.

**Parameters:**
- `token`: JWT token from Authorization header (optional)
- `api_key`: API key from X-API-Key header (optional)
- `provider`: Authentication provider instance (auto-injected)
- `db_session`: Database session (auto-injected)

**Returns:** `UserInfo` from whichever authentication method succeeded

**Raises:**
- `HTTPException 401`: Both authentication methods failed or missing

**Example:**
```python
@router.get("/flexible")
async def flexible_route(user: UserInfo = Depends(get_current_user_any)):
    return {"authenticated_via": user.provider}
```

**Accepts either:**
```bash
# JWT token
curl -X GET http://localhost:8000/flexible \
  -H "Authorization: Bearer eyJhbGciOi..."

# API key
curl -X GET http://localhost:8000/flexible \
  -H "X-API-Key: sk_abc123..."
```

---

#### `optional_auth(token, api_key, provider, db_session) -> UserInfo | None`

Returns user if authenticated, None otherwise. Does not raise errors for missing/invalid auth.

**Parameters:**
- `token`: JWT token from Authorization header (optional)
- `api_key`: API key from X-API-Key header (optional)
- `provider`: Authentication provider instance (auto-injected)
- `db_session`: Database session (auto-injected)

**Returns:** `UserInfo` if authenticated, `None` if not

**Example:**
```python
from typing import Optional

@router.get("/public")
async def public_route(user: Optional[UserInfo] = Depends(optional_auth)):
    if user:
        return {"message": f"Hello, {user.email}"}
    return {"message": "Hello, anonymous"}
```

### Authorization Classes

#### `RoleChecker(allowed_roles, require_all=False)`

FastAPI dependency for role-based access control.

**Parameters:**
- `allowed_roles`: List of roles that are allowed access
- `require_all`: If True, user must have ALL roles; if False, ANY role (default)

**Raises:**
- `HTTPException 403`: User lacks required roles

**Example:**
```python
admin_only = RoleChecker(["admin"])

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(admin_only)
):
    return {"deleted": user_id}
```

---

#### `PermissionChecker(required_permissions, require_all=True)`

FastAPI dependency for permission-based access control.

**Parameters:**
- `required_permissions`: List of permissions required for access
- `require_all`: If True, user needs ALL permissions; if False, ANY permission

**Raises:**
- `HTTPException 403`: User lacks required permissions

**Example:**
```python
write_permission = PermissionChecker(["users:write"])

@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(write_permission)
):
    return {"updated": user_id}
```

---

#### `ScopeChecker(required_scopes, require_all=True)`

FastAPI dependency for API key scope verification.

**Parameters:**
- `required_scopes`: List of scopes required for access
- `require_all`: If True, key needs ALL scopes; if False, ANY scope

**Raises:**
- `HTTPException 403`: API key lacks required scopes

**Example:**
```python
write_scope = ScopeChecker(["write"])

@router.post("/api/data")
async def create_data(
    user: UserInfo = Depends(get_current_user_from_api_key),
    _: None = Depends(write_scope)
):
    return {"created": True}
```

### Authorization Factories

#### `require_roles(*roles, require_all=False) -> RoleChecker`

Convenience function to create a RoleChecker dependency.

**Parameters:**
- `*roles`: Variable number of role names required
- `require_all`: If True, user must have ALL roles; if False, ANY role

**Returns:** `RoleChecker` dependency instance

**Example:**
```python
@router.post("/admin/settings")
async def update_settings(
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_roles("admin"))
):
    return {"updated": True}

@router.get("/staff/reports")
async def get_reports(
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_roles("admin", "staff"))  # ANY of these roles
):
    return {"reports": []}
```

---

#### `require_permissions(*permissions, require_all=True) -> PermissionChecker`

Convenience function to create a PermissionChecker dependency.

**Parameters:**
- `*permissions`: Variable number of permission names required
- `require_all`: If True, user needs ALL permissions; if False, ANY permission

**Returns:** `PermissionChecker` dependency instance

**Example:**
```python
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_permissions("users:delete"))
):
    return {"deleted": user_id}
```

---

#### `require_scopes(*scopes, require_all=True) -> ScopeChecker`

Convenience function to create a ScopeChecker dependency.

**Parameters:**
- `*scopes`: Variable number of scope names required
- `require_all`: If True, key needs ALL scopes; if False, ANY scope

**Returns:** `ScopeChecker` dependency instance

**Example:**
```python
@router.post("/api/data")
async def create_data(
    user: UserInfo = Depends(get_current_user_from_api_key),
    _: None = Depends(require_scopes("write"))
):
    return {"created": True}
```

### Token Extraction Functions

#### `get_token_from_header(authorization) -> str | None`

Extracts Bearer token from Authorization header.

**Parameters:**
- `authorization`: Authorization header value

**Returns:** Token string if valid Bearer token found, None otherwise

**Example:**
```python
token = get_token_from_header("Bearer eyJhbGciOi...")
# token = "eyJhbGciOi..."
```

---

#### `get_api_key_from_header(x_api_key) -> str | None`

Extracts API key from X-API-Key header.

**Parameters:**
- `x_api_key`: X-API-Key header value

**Returns:** API key string if present, None otherwise

**Example:**
```python
api_key = get_api_key_from_header("sk_abc123...")
# api_key = "sk_abc123..."
```

### Setup Functions

#### `set_auth_provider(provider)`

Sets the global authentication provider.

**Parameters:**
- `provider`: The authentication provider instance to use

**Example:**
```python
from agent_service.auth import create_auth_provider, set_auth_provider

auth_provider = create_auth_provider(config)
set_auth_provider(auth_provider)
```

---

#### `get_auth_provider() -> IAuthProvider`

Gets the configured authentication provider.

**Returns:** The global authentication provider instance

**Raises:**
- `HTTPException 500`: If auth provider is not configured

## Usage Patterns

### Pattern 1: Simple JWT Authentication

```python
from fastapi import APIRouter, Depends
from agent_service.auth import UserInfo, get_current_user

router = APIRouter()

@router.get("/profile")
async def get_profile(user: UserInfo = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
    }
```

### Pattern 2: Role-Based Access

```python
from agent_service.auth import require_roles

@router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_roles("admin"))
):
    return {"deleted": user_id}
```

### Pattern 3: Multiple Authorization Checks

```python
from agent_service.auth import RoleChecker, PermissionChecker

admin_role = RoleChecker(["admin"])
delete_permission = PermissionChecker(["users:delete"])

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    user: UserInfo = Depends(get_current_user),
    _role: None = Depends(admin_role),
    _perm: None = Depends(delete_permission)
):
    # User must be admin AND have delete permission
    return {"deleted": user_id}
```

### Pattern 4: Flexible Authentication

```python
from agent_service.auth import get_current_user_any

@router.get("/data")
async def get_data(user: UserInfo = Depends(get_current_user_any)):
    # Accepts both JWT and API key
    return {
        "data": [...],
        "authenticated_via": user.provider,
    }
```

### Pattern 5: Optional Authentication

```python
from typing import Optional
from agent_service.auth import optional_auth

@router.get("/content")
async def get_content(user: Optional[UserInfo] = Depends(optional_auth)):
    # Public endpoint with personalization for authenticated users
    if user:
        return {"content": "personalized", "user_id": user.id}
    return {"content": "generic"}
```

## Error Responses

### 401 Unauthorized

Missing, invalid, or expired authentication:

```json
{
  "detail": "Not authenticated"
}
```
**Headers:** `WWW-Authenticate: Bearer`

```json
{
  "detail": "Invalid or expired API key"
}
```
**Headers:** `WWW-Authenticate: ApiKey realm="X-API-Key"`

### 403 Forbidden

Valid authentication but insufficient permissions:

```json
{
  "detail": "Required roles: admin"
}
```

```json
{
  "detail": "Missing required permissions: users:delete"
}
```

```json
{
  "detail": "Missing required scopes: write, admin"
}
```

## Security Considerations

1. **Token Security**:
   - JWT tokens are validated using public keys from the identity provider
   - Token expiration is checked
   - Issuer and audience are validated

2. **API Key Security**:
   - Raw keys are never stored (only SHA256 hashes)
   - Constant-time comparison prevents timing attacks
   - Keys can be revoked and rotated

3. **Authorization**:
   - Authorization checks happen after authentication
   - Multiple authorization methods can be combined
   - Admin role typically grants all permissions

## Testing

Mock the auth provider for testing:

```python
from agent_service.auth import set_auth_provider, UserInfo, AuthProvider

class MockAuthProvider:
    def get_user_info(self, token):
        return UserInfo(
            id="test-user",
            email="test@example.com",
            roles=["admin"],
            provider=AuthProvider.CUSTOM,
        )

# In test setup
set_auth_provider(MockAuthProvider())
```

## See Also

- [DEPENDENCIES_USAGE.md](./DEPENDENCIES_USAGE.md) - Comprehensive usage examples
- [API_KEY_README.md](./API_KEY_README.md) - API key management guide
- [test_dependencies_example.py](./test_dependencies_example.py) - Working examples with tests
