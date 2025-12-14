# Role-Based Access Control (RBAC) System

A comprehensive RBAC system for the Agent Service that provides fine-grained access control through roles and permissions, with seamless integration for Azure AD and AWS Cognito.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Roles](#roles)
- [Permissions](#permissions)
- [Usage](#usage)
- [Integration with Azure AD and Cognito](#integration-with-azure-ad-and-cognito)
- [API Reference](#api-reference)

## Overview

The RBAC system provides:

- **Role-based access control**: Assign users to roles with predefined permissions
- **Permission-based access control**: Fine-grained control over specific operations
- **Role hierarchy**: Higher roles inherit permissions from lower roles
- **Custom permissions**: Per-user permission overrides
- **Provider integration**: Automatic role extraction from Azure AD groups and Cognito groups
- **FastAPI decorators**: Easy-to-use route protection

## Architecture

### Components

1. **permissions.py**: Defines all system permissions
2. **roles.py**: Defines roles and role-to-permission mappings
3. **rbac.py**: Core RBAC service with permission checking logic
4. **decorators.py**: FastAPI dependencies for route protection

### Permission Model

```
Permission → Role → User/Group
```

- **Permissions** are atomic access rights (e.g., `agents:read`, `agents:write`)
- **Roles** are collections of permissions (e.g., `ADMIN`, `DEVELOPER`)
- **Users** are assigned roles through JWT claims or group membership

## Roles

### Role Hierarchy

```
VIEWER → USER → DEVELOPER → ADMIN → SUPER_ADMIN
```

Each role inherits permissions from roles below it in the hierarchy.

### Role Definitions

| Role | Description | Example Permissions |
|------|-------------|-------------------|
| **VIEWER** | Read-only access to all resources | `agents:read`, `tools:read`, `users:read` |
| **USER** | VIEWER + execute agents and tools | VIEWER + `agents:execute`, `tools:execute` |
| **DEVELOPER** | USER + create/modify agents and tools | USER + `agents:write`, `agents:delete`, `tools:write` |
| **ADMIN** | DEVELOPER + manage users and API keys | DEVELOPER + `users:write`, `users:delete`, `api_keys:write` |
| **SUPER_ADMIN** | Full administrative access | All permissions + `admin:full` |

## Permissions

### Permission Categories

#### Agent Permissions
- `AGENTS_READ`: View agents
- `AGENTS_WRITE`: Create/update agents
- `AGENTS_DELETE`: Delete agents
- `AGENTS_EXECUTE`: Execute agents

#### Tool Permissions
- `TOOLS_READ`: View tools
- `TOOLS_WRITE`: Create/update tools
- `TOOLS_DELETE`: Delete tools
- `TOOLS_EXECUTE`: Execute tools

#### User Permissions
- `USERS_READ`: View users
- `USERS_WRITE`: Create/update users
- `USERS_DELETE`: Delete users

#### API Key Permissions
- `API_KEYS_READ`: View API keys
- `API_KEYS_WRITE`: Create/update API keys
- `API_KEYS_DELETE`: Delete API keys

#### Administrative Permissions
- `ADMIN_FULL`: Full administrative access (grants all permissions)
- `AUDIT_READ`: View audit logs

## Usage

### Basic Route Protection by Role

```python
from fastapi import APIRouter, Depends
from agent_service.auth.dependencies import get_current_user
from agent_service.auth.schemas import UserInfo
from agent_service.auth.rbac import Role, require_role

router = APIRouter()

@router.get("/admin/dashboard")
async def admin_dashboard(
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_role(Role.ADMIN))
):
    return {"message": "Admin dashboard"}
```

### Route Protection by Permission

```python
from agent_service.auth.rbac import Permission, require_permission

@router.post("/agents")
async def create_agent(
    agent_data: dict,
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_permission(Permission.AGENTS_WRITE))
):
    return {"message": "Agent created"}
```

### Multiple Roles (OR Logic)

```python
@router.get("/developer/tools")
async def developer_tools(
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_role(Role.DEVELOPER, Role.ADMIN))
):
    # Accessible by DEVELOPER OR ADMIN
    return {"message": "Developer tools"}
```

### Multiple Permissions (AND Logic)

```python
@router.post("/agents/privileged-execute")
async def privileged_execute(
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_permission(
        Permission.AGENTS_EXECUTE,
        Permission.TOOLS_EXECUTE,
        require_all=True  # Requires BOTH permissions
    ))
):
    return {"message": "Executed"}
```

### Multiple Permissions (OR Logic)

```python
@router.put("/agents/{agent_id}/permissions")
async def update_permissions(
    agent_id: str,
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_permission(
        Permission.AGENTS_WRITE,
        Permission.ADMIN_FULL,
        require_all=False  # Requires EITHER permission
    ))
):
    return {"message": "Permissions updated"}
```

### Role OR Permission

```python
from agent_service.auth.rbac import require_role_or_permission

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_role_or_permission(
        roles=[Role.ADMIN],
        permissions=[Permission.USERS_DELETE]
    ))
):
    return {"message": "User deleted"}
```

### Using RBAC Service Directly

```python
from agent_service.auth.rbac import get_rbac_service, Permission

@router.get("/conditional-access")
async def conditional_access(
    user: UserInfo = Depends(get_current_user)
):
    rbac = get_rbac_service()

    response = {"features": []}

    if rbac.has_permission(user, Permission.AGENTS_READ):
        response["features"].append("view_agents")

    if rbac.has_permission(user, Permission.AGENTS_WRITE):
        response["features"].append("create_agents")

    return response
```

### Get User Permissions

```python
@router.get("/user/permissions")
async def get_permissions(
    user: UserInfo = Depends(get_current_user)
):
    rbac = get_rbac_service()

    roles = rbac.get_user_roles(user)
    permissions = rbac.get_user_permissions(user)

    return {
        "roles": [role.value for role in roles],
        "permissions": [perm.value for perm in permissions]
    }
```

## Integration with Azure AD and Cognito

### Azure AD Groups

The RBAC system automatically maps Azure AD groups to roles:

```python
# Default Azure AD group mappings
"AgentService.Viewers" → Role.VIEWER
"AgentService.Users" → Role.USER
"AgentService.Developers" → Role.DEVELOPER
"AgentService.Admins" → Role.ADMIN
"AgentService.SuperAdmins" → Role.SUPER_ADMIN
```

### AWS Cognito Groups

Similarly, Cognito groups are mapped to roles:

```python
# Default Cognito group mappings
"agent-service-viewers" → Role.VIEWER
"agent-service-users" → Role.USER
"agent-service-developers" → Role.DEVELOPER
"agent-service-admins" → Role.ADMIN
"agent-service-super-admins" → Role.SUPER_ADMIN
```

### Custom Group Mappings

Customize group-to-role mappings for your organization:

```python
from agent_service.auth.rbac import update_group_to_role_mapping, Role

# In your FastAPI startup event
@app.on_event("startup")
async def startup():
    update_group_to_role_mapping({
        # Azure AD groups
        "MyCompany-AgentService-Admins": Role.ADMIN,
        "MyCompany-AgentService-Developers": Role.DEVELOPER,
        # Cognito groups
        "mycompany-agent-admins": Role.ADMIN,
        "mycompany-agent-devs": Role.DEVELOPER,
    })
```

### How It Works

1. User authenticates with Azure AD or Cognito
2. JWT token includes `roles` and/or `groups` claims
3. RBAC service extracts roles from:
   - Direct role claims in the token
   - Group memberships mapped to roles
4. Permissions are derived from the user's roles
5. Route decorators check permissions before allowing access

## API Reference

### Decorators

#### `require_role(*roles, require_all=False)`

Require one or more roles.

```python
require_role(Role.ADMIN)  # Requires ADMIN role
require_role(Role.ADMIN, Role.DEVELOPER)  # Requires ADMIN OR DEVELOPER
require_role(Role.ADMIN, Role.DEVELOPER, require_all=True)  # Requires BOTH
```

#### `require_permission(*permissions, require_all=True)`

Require one or more permissions.

```python
require_permission(Permission.AGENTS_WRITE)  # Requires agents:write
require_permission(Permission.AGENTS_WRITE, Permission.AGENTS_DELETE)  # Requires BOTH
require_permission(Permission.AGENTS_WRITE, Permission.ADMIN_FULL, require_all=False)  # Requires EITHER
```

#### `require_role_or_permission(roles=None, permissions=None)`

Require either a role OR a permission.

```python
require_role_or_permission(
    roles=[Role.ADMIN],
    permissions=[Permission.USERS_DELETE]
)
```

### RBACService Methods

#### `get_user_roles(user: UserInfo) -> set[Role]`

Get all roles for a user.

#### `get_user_permissions(user: UserInfo) -> set[Permission]`

Get all permissions for a user based on their roles.

#### `has_permission(user: UserInfo, permission: Permission) -> bool`

Check if user has a specific permission.

#### `has_any_permission(user: UserInfo, permissions: list[Permission]) -> bool`

Check if user has at least one of the specified permissions.

#### `has_all_permissions(user: UserInfo, permissions: list[Permission]) -> bool`

Check if user has all of the specified permissions.

#### `has_role(user: UserInfo, role: Role) -> bool`

Check if user has a specific role.

#### `has_any_role(user: UserInfo, roles: list[Role]) -> bool`

Check if user has at least one of the specified roles.

#### `has_all_roles(user: UserInfo, roles: list[Role]) -> bool`

Check if user has all of the specified roles.

#### `get_highest_user_role(user: UserInfo) -> Optional[Role]`

Get the highest role a user has in the hierarchy.

## Application Setup

### FastAPI Application

```python
from fastapi import FastAPI
from agent_service.auth.dependencies import set_auth_provider
from agent_service.auth.providers import create_auth_provider
from agent_service.auth.schemas import AuthConfig, AuthProvider
from agent_service.auth.rbac import set_rbac_service, RBACService

app = FastAPI()

@app.on_event("startup")
async def startup():
    # Configure authentication provider
    auth_config = AuthConfig(
        provider=AuthProvider.AZURE_AD,
        # ... your config
    )
    auth_provider = create_auth_provider(auth_config)
    set_auth_provider(auth_provider)

    # Configure RBAC (optional, uses default if not set)
    rbac_service = RBACService(
        enable_hierarchy=True,  # Enable role hierarchy
        enable_custom_permissions=True  # Enable per-user permissions
    )
    set_rbac_service(rbac_service)
```

## Custom Permissions

Add custom permissions at runtime:

```python
rbac = get_rbac_service()

# Add custom permission to user
rbac.add_custom_permission(user, Permission.AGENTS_DELETE)

# Remove custom permission from user
rbac.remove_custom_permission(user, Permission.AGENTS_DELETE)
```

Note: Custom permissions are stored in the `UserInfo.metadata["permissions"]` field and are not persisted to a database. They're meant for runtime permission grants.

## Examples

See `examples.py` for comprehensive examples of all RBAC features.

## Testing

```python
from agent_service.auth.schemas import UserInfo, AuthProvider
from agent_service.auth.rbac import get_rbac_service, Permission, Role

# Create test user
user = UserInfo(
    id="test-user",
    email="test@example.com",
    roles=["admin"],  # Will be mapped to Role.ADMIN
    groups=["AgentService.Admins"],  # Will also be mapped to Role.ADMIN
    provider=AuthProvider.AZURE_AD,
)

# Check permissions
rbac = get_rbac_service()
assert rbac.has_role(user, Role.ADMIN)
assert rbac.has_permission(user, Permission.USERS_DELETE)
```

## License

Internal use only. Not for distribution.
