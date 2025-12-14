"""
Role-Based Access Control (RBAC) module.

This module provides a comprehensive RBAC system for the agent service,
including permission definitions, role management, and FastAPI decorators
for protecting routes.

The RBAC system integrates seamlessly with Azure AD and AWS Cognito,
mapping groups to roles and providing fine-grained permission control.

Quick Start:
    Basic usage in FastAPI routes:
        >>> from agent_service.auth.rbac import (
        ...     Permission,
        ...     Role,
        ...     require_role,
        ...     require_permission,
        ... )
        >>> from agent_service.auth.dependencies import get_current_user
        >>> from agent_service.auth.schemas import UserInfo
        >>> from fastapi import Depends, APIRouter
        >>>
        >>> router = APIRouter()
        >>>
        >>> # Require specific role
        >>> @router.get("/admin")
        >>> async def admin_only(
        ...     user: UserInfo = Depends(get_current_user),
        ...     _: None = Depends(require_role(Role.ADMIN))
        ... ):
        ...     return {"message": "Admin access"}
        >>>
        >>> # Require specific permission
        >>> @router.post("/agents")
        >>> async def create_agent(
        ...     user: UserInfo = Depends(get_current_user),
        ...     _: None = Depends(require_permission(Permission.AGENTS_WRITE))
        ... ):
        ...     return {"message": "Agent created"}

    Using RBAC service directly:
        >>> from agent_service.auth.rbac import get_rbac_service, Permission
        >>>
        >>> rbac = get_rbac_service()
        >>> if rbac.has_permission(user, Permission.AGENTS_READ):
        ...     # Allow access
        ...     pass

Key Components:
    - Permission: Enum defining all system permissions
    - Role: Enum defining user roles (VIEWER, USER, DEVELOPER, ADMIN, SUPER_ADMIN)
    - RBACService: Core service for permission checking
    - require_role: FastAPI dependency for role-based access control
    - require_permission: FastAPI dependency for permission-based access control

Integration with Azure AD and Cognito:
    The RBAC system automatically extracts roles from:
    - Azure AD groups (e.g., "AgentService.Admins" -> Role.ADMIN)
    - AWS Cognito groups (e.g., "agent-service-admins" -> Role.ADMIN)
    - Direct role claims in JWT tokens

    You can customize the group-to-role mapping:
        >>> from agent_service.auth.rbac import update_group_to_role_mapping, Role
        >>>
        >>> update_group_to_role_mapping({
        ...     "MyCompany-Admins": Role.ADMIN,
        ...     "MyCompany-Developers": Role.DEVELOPER,
        ... })
"""

from .decorators import (
    PermissionRequired,
    RoleOrPermissionRequired,
    RoleRequired,
    get_current_user_with_rbac,
    require_permission,
    require_role,
    require_role_or_permission,
)
from .permissions import (
    Permission,
    PermissionGroups,
    get_permissions_by_operation,
    get_permissions_by_resource,
    permission_implies,
)
from .rbac import (
    RBACService,
    get_rbac_service,
    set_rbac_service,
)
from .roles import (
    DEFAULT_GROUP_TO_ROLE,
    DEFAULT_ROLE_PERMISSIONS,
    ROLE_HIERARCHY,
    Role,
    get_highest_role,
    get_permissions_for_role,
    get_role_from_string,
    get_roles_from_groups,
    get_roles_from_strings,
    role_hierarchy_includes,
    update_group_to_role_mapping,
)

__all__ = [
    # Permissions
    "Permission",
    "PermissionGroups",
    "get_permissions_by_resource",
    "get_permissions_by_operation",
    "permission_implies",
    # Roles
    "Role",
    "DEFAULT_ROLE_PERMISSIONS",
    "ROLE_HIERARCHY",
    "DEFAULT_GROUP_TO_ROLE",
    "get_permissions_for_role",
    "get_role_from_string",
    "get_roles_from_groups",
    "get_roles_from_strings",
    "role_hierarchy_includes",
    "get_highest_role",
    "update_group_to_role_mapping",
    # RBAC Service
    "RBACService",
    "get_rbac_service",
    "set_rbac_service",
    # Decorators/Dependencies
    "RoleRequired",
    "PermissionRequired",
    "RoleOrPermissionRequired",
    "require_role",
    "require_permission",
    "require_role_or_permission",
    "get_current_user_with_rbac",
]

# Version info
__version__ = "1.0.0"
__author__ = "Agent Service Team"
__description__ = "Role-Based Access Control system for Agent Service"
