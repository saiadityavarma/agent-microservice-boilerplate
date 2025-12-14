# RBAC Quick Reference Guide

## Common Patterns

### Import Statements

```python
from fastapi import Depends, APIRouter
from agent_service.auth.dependencies import get_current_user
from agent_service.auth.schemas import UserInfo
from agent_service.auth.rbac import (
    Permission,
    Role,
    require_role,
    require_permission,
    require_role_or_permission,
    get_rbac_service,
)
```

### Route Protection Examples

#### Single Role

```python
@router.get("/admin/dashboard")
async def admin_dashboard(
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_role(Role.ADMIN))
):
    return {"message": "Admin only"}
```

#### Multiple Roles (OR)

```python
@router.get("/moderator-tools")
async def moderator_tools(
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_role(Role.ADMIN, Role.DEVELOPER))  # ADMIN OR DEVELOPER
):
    return {"tools": [...]}
```

#### Multiple Roles (AND)

```python
@router.get("/special-access")
async def special_access(
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_role(Role.ADMIN, Role.DEVELOPER, require_all=True))  # BOTH
):
    return {"data": [...]}
```

#### Single Permission

```python
@router.post("/agents")
async def create_agent(
    agent_data: dict,
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_permission(Permission.AGENTS_WRITE))
):
    return {"created": True}
```

#### Multiple Permissions (AND - default)

```python
@router.post("/complex-operation")
async def complex_op(
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_permission(
        Permission.AGENTS_EXECUTE,
        Permission.TOOLS_EXECUTE  # Requires BOTH
    ))
):
    return {"executed": True}
```

#### Multiple Permissions (OR)

```python
@router.put("/update-config")
async def update_config(
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_permission(
        Permission.AGENTS_WRITE,
        Permission.ADMIN_FULL,
        require_all=False  # Requires EITHER
    ))
):
    return {"updated": True}
```

#### Role OR Permission

```python
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_role_or_permission(
        roles=[Role.ADMIN],
        permissions=[Permission.USERS_DELETE]
    ))
):
    return {"deleted": user_id}
```

### Direct RBAC Service Usage

#### Check Single Permission

```python
@router.get("/conditional")
async def conditional(user: UserInfo = Depends(get_current_user)):
    rbac = get_rbac_service()

    if rbac.has_permission(user, Permission.AGENTS_READ):
        return {"data": [...]}
    else:
        raise HTTPException(status_code=403, detail="Access denied")
```

#### Check Multiple Permissions

```python
rbac = get_rbac_service()

# Check if user has ANY of the permissions
if rbac.has_any_permission(user, [Permission.AGENTS_WRITE, Permission.ADMIN_FULL]):
    # Allow access

# Check if user has ALL of the permissions
if rbac.has_all_permissions(user, [Permission.AGENTS_READ, Permission.AGENTS_EXECUTE]):
    # Allow access
```

#### Check Roles

```python
rbac = get_rbac_service()

# Check single role
if rbac.has_role(user, Role.ADMIN):
    # Admin access

# Check multiple roles (ANY)
if rbac.has_any_role(user, [Role.ADMIN, Role.DEVELOPER]):
    # Admin or Developer access

# Check multiple roles (ALL)
if rbac.has_all_roles(user, [Role.ADMIN, Role.DEVELOPER]):
    # Has both roles
```

#### Get User Information

```python
rbac = get_rbac_service()

# Get all roles
roles = rbac.get_user_roles(user)
# Returns: {Role.ADMIN, Role.DEVELOPER}

# Get all permissions
permissions = rbac.get_user_permissions(user)
# Returns: {Permission.AGENTS_READ, Permission.AGENTS_WRITE, ...}

# Get highest role
highest = rbac.get_highest_user_role(user)
# Returns: Role.ADMIN
```

## Roles & Permissions Quick Lookup

### Roles (from least to most privileged)

| Role | Value | Description |
|------|-------|-------------|
| VIEWER | `"viewer"` | Read-only access |
| USER | `"user"` | Read + Execute |
| DEVELOPER | `"developer"` | Read + Write + Execute + Delete (agents/tools) |
| ADMIN | `"admin"` | DEVELOPER + User management |
| SUPER_ADMIN | `"super_admin"` | Full admin access |

### Permissions by Category

#### Agents
- `Permission.AGENTS_READ` = `"agents:read"`
- `Permission.AGENTS_WRITE` = `"agents:write"`
- `Permission.AGENTS_DELETE` = `"agents:delete"`
- `Permission.AGENTS_EXECUTE` = `"agents:execute"`

#### Tools
- `Permission.TOOLS_READ` = `"tools:read"`
- `Permission.TOOLS_WRITE` = `"tools:write"`
- `Permission.TOOLS_DELETE` = `"tools:delete"`
- `Permission.TOOLS_EXECUTE` = `"tools:execute"`

#### Users
- `Permission.USERS_READ` = `"users:read"`
- `Permission.USERS_WRITE` = `"users:write"`
- `Permission.USERS_DELETE` = `"users:delete"`

#### API Keys
- `Permission.API_KEYS_READ` = `"api_keys:read"`
- `Permission.API_KEYS_WRITE` = `"api_keys:write"`
- `Permission.API_KEYS_DELETE` = `"api_keys:delete"`

#### Admin
- `Permission.ADMIN_FULL` = `"admin:full"` (grants all permissions)
- `Permission.AUDIT_READ` = `"audit:read"`

### Role → Permissions Matrix

| Permission | VIEWER | USER | DEVELOPER | ADMIN | SUPER_ADMIN |
|------------|:------:|:----:|:---------:|:-----:|:-----------:|
| agents:read | ✓ | ✓ | ✓ | ✓ | ✓ |
| agents:execute | | ✓ | ✓ | ✓ | ✓ |
| agents:write | | | ✓ | ✓ | ✓ |
| agents:delete | | | ✓ | ✓ | ✓ |
| tools:read | ✓ | ✓ | ✓ | ✓ | ✓ |
| tools:execute | | ✓ | ✓ | ✓ | ✓ |
| tools:write | | | ✓ | ✓ | ✓ |
| tools:delete | | | ✓ | ✓ | ✓ |
| users:read | ✓ | ✓ | ✓ | ✓ | ✓ |
| users:write | | | | ✓ | ✓ |
| users:delete | | | | ✓ | ✓ |
| api_keys:read | ✓ | ✓ | ✓ | ✓ | ✓ |
| api_keys:write | | | ✓ | ✓ | ✓ |
| api_keys:delete | | | ✓ | ✓ | ✓ |
| audit:read | ✓ | ✓ | ✓ | ✓ | ✓ |
| admin:full | | | | | ✓ |

## Group Mappings

### Azure AD Groups

```
"AgentService.Viewers" → Role.VIEWER
"AgentService.Users" → Role.USER
"AgentService.Developers" → Role.DEVELOPER
"AgentService.Admins" → Role.ADMIN
"AgentService.SuperAdmins" → Role.SUPER_ADMIN
```

### AWS Cognito Groups

```
"agent-service-viewers" → Role.VIEWER
"agent-service-users" → Role.USER
"agent-service-developers" → Role.DEVELOPER
"agent-service-admins" → Role.ADMIN
"agent-service-super-admins" → Role.SUPER_ADMIN
```

### Add Custom Mappings

```python
from agent_service.auth.rbac import update_group_to_role_mapping, Role

update_group_to_role_mapping({
    "MyCompany-Admins": Role.ADMIN,
    "MyCompany-Developers": Role.DEVELOPER,
})
```

## Common Use Cases

### Admin-Only Route

```python
@router.delete("/system/reset")
async def reset_system(
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_role(Role.ADMIN))
):
    return {"reset": True}
```

### Read Permission Required

```python
@router.get("/agents")
async def list_agents(
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_permission(Permission.AGENTS_READ))
):
    return {"agents": [...]}
```

### Write Permission Required

```python
@router.post("/agents")
async def create_agent(
    agent_data: dict,
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_permission(Permission.AGENTS_WRITE))
):
    return {"created": True}
```

### Execute Permission Required

```python
@router.post("/agents/{agent_id}/run")
async def run_agent(
    agent_id: str,
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_permission(Permission.AGENTS_EXECUTE))
):
    return {"running": True}
```

### Delete Permission Required

```python
@router.delete("/agents/{agent_id}")
async def delete_agent(
    agent_id: str,
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_permission(Permission.AGENTS_DELETE))
):
    return {"deleted": True}
```

### Conditional Features Based on Permissions

```python
@router.get("/dashboard")
async def dashboard(user: UserInfo = Depends(get_current_user)):
    rbac = get_rbac_service()

    features = {
        "can_view_agents": rbac.has_permission(user, Permission.AGENTS_READ),
        "can_create_agents": rbac.has_permission(user, Permission.AGENTS_WRITE),
        "can_delete_agents": rbac.has_permission(user, Permission.AGENTS_DELETE),
        "can_manage_users": rbac.has_permission(user, Permission.USERS_WRITE),
        "is_admin": rbac.has_role(user, Role.ADMIN),
    }

    return {"features": features}
```

## Setup in FastAPI App

```python
from fastapi import FastAPI
from agent_service.auth.rbac import set_rbac_service, RBACService

app = FastAPI()

@app.on_event("startup")
async def startup():
    # Optional: Configure custom RBAC service
    rbac = RBACService(
        enable_hierarchy=True,        # Roles inherit permissions
        enable_custom_permissions=True # Allow per-user overrides
    )
    set_rbac_service(rbac)
```

## Error Responses

### 401 Unauthorized
- No authentication provided
- Invalid/expired token

### 403 Forbidden
- User authenticated but lacks required role/permission
- Examples:
  - `"Missing required roles: admin"`
  - `"Missing required permissions: agents:write"`
  - `"Required roles: admin OR permissions: users:delete"`
