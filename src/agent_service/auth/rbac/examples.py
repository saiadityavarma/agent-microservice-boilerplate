"""
Example usage of the RBAC system.

This file demonstrates various ways to use the RBAC system in your FastAPI
application, including route protection, permission checking, and integration
with Azure AD and AWS Cognito.

NOTE: This is an examples file for reference. It's not meant to be imported
or run directly in production.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from ..dependencies import get_current_user
from ..schemas import UserInfo
from .decorators import (
    require_role,
    require_permission,
    require_role_or_permission,
    get_current_user_with_rbac,
)
from .permissions import Permission
from .rbac import get_rbac_service
from .roles import Role, update_group_to_role_mapping


# ============================================================================
# Example 1: Basic Role-Based Protection
# ============================================================================

router = APIRouter(prefix="/api/v1", tags=["examples"])


@router.get("/admin/dashboard")
async def admin_dashboard(
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_role(Role.ADMIN)),
):
    """
    Admin-only route.

    Only users with the ADMIN role can access this endpoint.
    """
    return {
        "message": "Welcome to admin dashboard",
        "user_id": user.id,
        "roles": user.roles,
    }


@router.get("/viewer/reports")
async def viewer_reports(
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_role(Role.VIEWER)),
):
    """
    Viewer-accessible route.

    Users with VIEWER role or higher (due to role hierarchy) can access this.
    """
    return {
        "message": "View-only reports",
        "user_id": user.id,
    }


# ============================================================================
# Example 2: Permission-Based Protection
# ============================================================================


@router.post("/agents")
async def create_agent(
    agent_data: dict,
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_permission(Permission.AGENTS_WRITE)),
):
    """
    Create a new agent.

    Requires AGENTS_WRITE permission, which is granted to DEVELOPER role and above.
    """
    return {
        "message": "Agent created successfully",
        "created_by": user.id,
        "agent": agent_data,
    }


@router.delete("/agents/{agent_id}")
async def delete_agent(
    agent_id: str,
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_permission(Permission.AGENTS_DELETE)),
):
    """
    Delete an agent.

    Requires AGENTS_DELETE permission, which is granted to DEVELOPER role and above.
    """
    return {
        "message": f"Agent {agent_id} deleted successfully",
        "deleted_by": user.id,
    }


@router.get("/agents")
async def list_agents(
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_permission(Permission.AGENTS_READ)),
):
    """
    List all agents.

    Requires AGENTS_READ permission, which is granted to all roles.
    """
    return {
        "message": "List of agents",
        "user_id": user.id,
        "agents": [],
    }


# ============================================================================
# Example 3: Multiple Permissions (ANY)
# ============================================================================


@router.put("/agents/{agent_id}/permissions")
async def update_agent_permissions(
    agent_id: str,
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(
        require_permission(
            Permission.AGENTS_WRITE,
            Permission.ADMIN_FULL,
            require_all=False,  # User needs EITHER permission
        )
    ),
):
    """
    Update agent permissions.

    Requires EITHER AGENTS_WRITE OR ADMIN_FULL permission.
    This allows both developers and admins to update permissions.
    """
    return {
        "message": f"Agent {agent_id} permissions updated",
        "updated_by": user.id,
    }


# ============================================================================
# Example 4: Multiple Permissions (ALL)
# ============================================================================


@router.post("/agents/{agent_id}/execute-privileged")
async def execute_privileged_agent(
    agent_id: str,
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(
        require_permission(
            Permission.AGENTS_EXECUTE,
            Permission.TOOLS_EXECUTE,
            require_all=True,  # User needs BOTH permissions
        )
    ),
):
    """
    Execute a privileged agent operation.

    Requires BOTH AGENTS_EXECUTE AND TOOLS_EXECUTE permissions.
    """
    return {
        "message": f"Agent {agent_id} executed with privileged access",
        "executed_by": user.id,
    }


# ============================================================================
# Example 5: Role OR Permission
# ============================================================================


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(
        require_role_or_permission(
            roles=[Role.ADMIN, Role.SUPER_ADMIN],
            permissions=[Permission.USERS_DELETE],
        )
    ),
):
    """
    Delete a user.

    Requires EITHER admin/super_admin role OR users:delete permission.
    This provides flexible access control.
    """
    return {
        "message": f"User {user_id} deleted successfully",
        "deleted_by": user.id,
    }


# ============================================================================
# Example 6: Multiple Roles (ANY)
# ============================================================================


@router.get("/developer/tools")
async def developer_tools(
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_role(Role.DEVELOPER, Role.ADMIN)),
):
    """
    Developer tools endpoint.

    Accessible by users with DEVELOPER OR ADMIN role.
    """
    return {
        "message": "Developer tools",
        "user_id": user.id,
    }


# ============================================================================
# Example 7: Using RBAC Service Directly
# ============================================================================


@router.get("/conditional-access")
async def conditional_access(
    user: UserInfo = Depends(get_current_user),
):
    """
    Route with conditional access based on permissions.

    Uses RBAC service directly for complex permission logic.
    """
    rbac = get_rbac_service()

    response = {
        "user_id": user.id,
        "access_level": "basic",
        "features": [],
    }

    # Check various permissions and add features accordingly
    if rbac.has_permission(user, Permission.AGENTS_READ):
        response["features"].append("view_agents")

    if rbac.has_permission(user, Permission.AGENTS_WRITE):
        response["features"].append("create_agents")
        response["access_level"] = "developer"

    if rbac.has_permission(user, Permission.AGENTS_DELETE):
        response["features"].append("delete_agents")

    if rbac.has_permission(user, Permission.ADMIN_FULL):
        response["features"].append("admin_panel")
        response["access_level"] = "admin"

    return response


# ============================================================================
# Example 8: Using get_current_user_with_rbac
# ============================================================================


@router.get("/user/permissions")
async def get_user_permissions(
    user_rbac: tuple[UserInfo, "RBACService"] = Depends(get_current_user_with_rbac),
):
    """
    Get current user's permissions.

    Uses get_current_user_with_rbac to get both user and RBAC service.
    """
    user, rbac = user_rbac

    roles = rbac.get_user_roles(user)
    permissions = rbac.get_user_permissions(user)
    highest_role = rbac.get_highest_user_role(user)

    return {
        "user_id": user.id,
        "email": user.email,
        "roles": [role.value for role in roles],
        "permissions": [perm.value for perm in permissions],
        "highest_role": highest_role.value if highest_role else None,
    }


# ============================================================================
# Example 9: Resource Owner Check with RBAC
# ============================================================================


async def is_resource_owner_or_admin(
    resource_owner_id: str,
    user: UserInfo = Depends(get_current_user),
) -> bool:
    """
    Check if user is the resource owner or has admin privileges.

    This demonstrates combining ownership checks with RBAC.
    """
    rbac = get_rbac_service()

    # Allow if user is the owner
    if user.id == resource_owner_id:
        return True

    # Allow if user has admin role
    if rbac.has_role(user, Role.ADMIN) or rbac.has_role(user, Role.SUPER_ADMIN):
        return True

    # Allow if user has admin full permission
    if rbac.has_permission(user, Permission.ADMIN_FULL):
        return True

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only the resource owner or admin can perform this action",
    )


@router.put("/agents/{agent_id}/update")
async def update_agent(
    agent_id: str,
    agent_data: dict,
    user: UserInfo = Depends(get_current_user),
):
    """
    Update an agent.

    Only the agent owner or admin can update.
    """
    # In a real app, you'd fetch the agent from database
    # For this example, we'll use a dummy owner ID
    agent_owner_id = "owner-user-id"

    # Check if user is owner or admin
    await is_resource_owner_or_admin(agent_owner_id, user)

    return {
        "message": f"Agent {agent_id} updated successfully",
        "updated_by": user.id,
    }


# ============================================================================
# Example 10: Customizing Group-to-Role Mapping
# ============================================================================


def setup_custom_rbac_mapping():
    """
    Configure custom group-to-role mappings for your organization.

    Call this during application startup to customize the mappings
    based on your Azure AD or Cognito group naming conventions.
    """
    # Azure AD example
    update_group_to_role_mapping(
        {
            # Your organization's Azure AD groups
            "MyCompany-AgentService-Admins": Role.ADMIN,
            "MyCompany-AgentService-Developers": Role.DEVELOPER,
            "MyCompany-AgentService-Users": Role.USER,
            "MyCompany-AgentService-Viewers": Role.VIEWER,
            # AWS Cognito groups
            "mycompany-agent-admins": Role.ADMIN,
            "mycompany-agent-devs": Role.DEVELOPER,
            "mycompany-agent-users": Role.USER,
        }
    )


# ============================================================================
# Example 11: Custom Permission Overrides
# ============================================================================


@router.post("/agents/{agent_id}/grant-permission")
async def grant_custom_permission(
    agent_id: str,
    permission: str,
    user_id: str,
    current_user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_role(Role.ADMIN)),
):
    """
    Grant a custom permission to a user for a specific agent.

    This shows how to add custom permissions at runtime.
    Only admins can grant permissions.
    """
    rbac = get_rbac_service()

    # In a real app, you'd fetch the target user from database
    # For this example, we'll modify the current_user object
    try:
        perm = Permission(permission)
        rbac.add_custom_permission(current_user, perm)

        return {
            "message": f"Permission {permission} granted to user {user_id}",
            "granted_by": current_user.id,
        }
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid permission: {permission}",
        )


# ============================================================================
# Example 12: Listing User Capabilities
# ============================================================================


@router.get("/user/capabilities")
async def get_user_capabilities(
    user: UserInfo = Depends(get_current_user),
):
    """
    Get detailed information about user's capabilities.

    Returns all roles, permissions, and what actions the user can perform.
    """
    rbac = get_rbac_service()

    roles = rbac.get_user_roles(user)
    permissions = rbac.get_user_permissions(user)

    capabilities = {
        "user_id": user.id,
        "email": user.email,
        "roles": [role.value for role in roles],
        "permissions": [perm.value for perm in permissions],
        "can_perform": {
            "read_agents": rbac.has_permission(user, Permission.AGENTS_READ),
            "create_agents": rbac.has_permission(user, Permission.AGENTS_WRITE),
            "delete_agents": rbac.has_permission(user, Permission.AGENTS_DELETE),
            "execute_agents": rbac.has_permission(user, Permission.AGENTS_EXECUTE),
            "manage_users": rbac.has_permission(user, Permission.USERS_WRITE),
            "delete_users": rbac.has_permission(user, Permission.USERS_DELETE),
            "manage_api_keys": rbac.has_permission(user, Permission.API_KEYS_WRITE),
            "view_audit_logs": rbac.has_permission(user, Permission.AUDIT_READ),
            "admin_access": rbac.has_permission(user, Permission.ADMIN_FULL),
        },
    }

    return capabilities


# ============================================================================
# Example 13: FastAPI App Setup with RBAC
# ============================================================================


"""
# In your main FastAPI application file (e.g., main.py):

from fastapi import FastAPI
from agent_service.auth.dependencies import set_auth_provider
from agent_service.auth.providers import create_auth_provider
from agent_service.auth.schemas import AuthConfig, AuthProvider
from agent_service.auth.rbac import set_rbac_service, RBACService
from agent_service.auth.rbac.examples import setup_custom_rbac_mapping

app = FastAPI()


@app.on_event("startup")
async def startup():
    # Configure authentication provider
    auth_config = AuthConfig(
        provider=AuthProvider.AZURE_AD,
        # ... your Azure AD or Cognito config
    )
    auth_provider = create_auth_provider(auth_config)
    set_auth_provider(auth_provider)

    # Configure RBAC service (optional, uses default if not set)
    rbac_service = RBACService(
        enable_hierarchy=True,
        enable_custom_permissions=True,
    )
    set_rbac_service(rbac_service)

    # Setup custom group-to-role mappings
    setup_custom_rbac_mapping()


# Include routers
app.include_router(router)
"""
