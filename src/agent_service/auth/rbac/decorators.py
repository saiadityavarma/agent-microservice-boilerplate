"""
FastAPI decorators for role and permission-based access control.

This module provides convenient decorators and dependencies for protecting
FastAPI routes with RBAC. It integrates with the existing authentication
system and RBAC service to provide declarative authorization.

Usage:
    Role-based protection:
        >>> @router.get("/admin/dashboard")
        >>> async def admin_dashboard(
        ...     user: UserInfo = Depends(get_current_user),
        ...     _: None = Depends(require_role(Role.ADMIN))
        ... ):
        ...     return {"message": "Admin dashboard"}

    Permission-based protection:
        >>> @router.post("/agents")
        >>> async def create_agent(
        ...     user: UserInfo = Depends(get_current_user),
        ...     _: None = Depends(require_permission(Permission.AGENTS_WRITE))
        ... ):
        ...     return {"message": "Agent created"}
"""

import logging
from typing import Callable, List, Union

from fastapi import Depends, HTTPException, status

from ..dependencies import get_current_user
from ..schemas import UserInfo
from .permissions import Permission
from .rbac import get_rbac_service, RBACService
from .roles import Role

logger = logging.getLogger(__name__)


class RoleRequired:
    """
    FastAPI dependency for requiring specific roles.

    This dependency checks if the authenticated user has at least one of the
    required roles (OR logic by default) or all roles (AND logic if require_all=True).

    Example:
        >>> role_dep = RoleRequired([Role.ADMIN, Role.DEVELOPER])
        >>>
        >>> @router.get("/protected")
        >>> async def protected_route(
        ...     user: UserInfo = Depends(get_current_user),
        ...     _: None = Depends(role_dep)
        ... ):
        ...     return {"message": "Authorized"}
    """

    def __init__(
        self,
        required_roles: List[Role],
        require_all: bool = False,
        rbac_service: RBACService = None,
    ):
        """
        Initialize role requirement dependency.

        Args:
            required_roles: List of roles, at least one must be present (or all if require_all=True)
            require_all: If True, user must have ALL roles; if False, ANY role (default)
            rbac_service: Optional RBAC service instance (uses global if not provided)
        """
        self.required_roles = required_roles
        self.require_all = require_all
        self.rbac_service = rbac_service or get_rbac_service()

    async def __call__(self, user: UserInfo = Depends(get_current_user)) -> None:
        """
        Check if user has required roles.

        Args:
            user: Authenticated user information

        Raises:
            HTTPException: 403 if user lacks required roles
        """
        if self.require_all:
            # User must have ALL required roles
            if not self.rbac_service.has_all_roles(user, self.required_roles):
                user_roles = self.rbac_service.get_user_roles(user)
                missing_roles = set(self.required_roles) - user_roles
                logger.warning(
                    f"User {user.id} denied access: missing roles "
                    f"{[r.value for r in missing_roles]}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required roles: {', '.join(r.value for r in missing_roles)}",
                )
        else:
            # User must have AT LEAST ONE required role
            if not self.rbac_service.has_any_role(user, self.required_roles):
                logger.warning(
                    f"User {user.id} denied access: requires one of roles "
                    f"{[r.value for r in self.required_roles]}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Required roles: {', '.join(r.value for r in self.required_roles)}",
                )

        logger.debug(f"User {user.id} authorized with required roles")


class PermissionRequired:
    """
    FastAPI dependency for requiring specific permissions.

    This dependency checks if the authenticated user has the required permissions
    based on their roles and custom permissions.

    Example:
        >>> perm_dep = PermissionRequired([Permission.AGENTS_WRITE])
        >>>
        >>> @router.post("/agents")
        >>> async def create_agent(
        ...     user: UserInfo = Depends(get_current_user),
        ...     _: None = Depends(perm_dep)
        ... ):
        ...     return {"message": "Agent created"}
    """

    def __init__(
        self,
        required_permissions: List[Permission],
        require_all: bool = True,
        rbac_service: RBACService = None,
    ):
        """
        Initialize permission requirement dependency.

        Args:
            required_permissions: List of permissions to check
            require_all: If True, user needs ALL permissions; if False, ANY permission
            rbac_service: Optional RBAC service instance (uses global if not provided)
        """
        self.required_permissions = required_permissions
        self.require_all = require_all
        self.rbac_service = rbac_service or get_rbac_service()

    async def __call__(self, user: UserInfo = Depends(get_current_user)) -> None:
        """
        Check if user has required permissions.

        Args:
            user: Authenticated user information

        Raises:
            HTTPException: 403 if user lacks required permissions
        """
        if self.require_all:
            # User must have ALL required permissions
            if not self.rbac_service.has_all_permissions(user, self.required_permissions):
                user_permissions = self.rbac_service.get_user_permissions(user)
                missing_perms = set(self.required_permissions) - user_permissions
                logger.warning(
                    f"User {user.id} denied access: missing permissions "
                    f"{[p.value for p in missing_perms]}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permissions: {', '.join(p.value for p in missing_perms)}",
                )
        else:
            # User must have AT LEAST ONE required permission
            if not self.rbac_service.has_any_permission(user, self.required_permissions):
                logger.warning(
                    f"User {user.id} denied access: requires one of permissions "
                    f"{[p.value for p in self.required_permissions]}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Required permissions: {', '.join(p.value for p in self.required_permissions)}",
                )

        logger.debug(f"User {user.id} authorized with required permissions")


# Convenience factory functions for creating dependencies


def require_role(
    *roles: Role,
    require_all: bool = False,
) -> RoleRequired:
    """
    Create a dependency that requires specific roles.

    This is a convenience function for creating RoleRequired dependencies
    with a cleaner syntax.

    Args:
        *roles: Variable number of roles required
        require_all: If True, user must have ALL roles; if False, ANY role (default)

    Returns:
        RoleRequired dependency instance

    Example:
        >>> @router.delete("/users/{user_id}")
        >>> async def delete_user(
        ...     user_id: str,
        ...     user: UserInfo = Depends(get_current_user),
        ...     _: None = Depends(require_role(Role.ADMIN))
        ... ):
        ...     return {"deleted": user_id}
        >>>
        >>> @router.get("/dashboard")
        >>> async def dashboard(
        ...     user: UserInfo = Depends(get_current_user),
        ...     _: None = Depends(require_role(Role.ADMIN, Role.DEVELOPER))
        ... ):
        ...     # Accessible by ADMIN OR DEVELOPER
        ...     return {"dashboard": "data"}
    """
    return RoleRequired(list(roles), require_all=require_all)


def require_permission(
    *permissions: Permission,
    require_all: bool = True,
) -> PermissionRequired:
    """
    Create a dependency that requires specific permissions.

    This is a convenience function for creating PermissionRequired dependencies
    with a cleaner syntax.

    Args:
        *permissions: Variable number of permissions required
        require_all: If True, user needs ALL permissions; if False, ANY permission

    Returns:
        PermissionRequired dependency instance

    Example:
        >>> @router.post("/agents")
        >>> async def create_agent(
        ...     user: UserInfo = Depends(get_current_user),
        ...     _: None = Depends(require_permission(Permission.AGENTS_WRITE))
        ... ):
        ...     return {"message": "Agent created"}
        >>>
        >>> @router.delete("/agents/{agent_id}")
        >>> async def delete_agent(
        ...     agent_id: str,
        ...     user: UserInfo = Depends(get_current_user),
        ...     _: None = Depends(require_permission(
        ...         Permission.AGENTS_DELETE,
        ...         Permission.ADMIN_FULL,
        ...         require_all=False
        ...     ))
        ... ):
        ...     # Requires AGENTS_DELETE OR ADMIN_FULL
        ...     return {"deleted": agent_id}
    """
    return PermissionRequired(list(permissions), require_all=require_all)


# Combined role and permission checker


class RoleOrPermissionRequired:
    """
    FastAPI dependency for requiring either a role OR a permission.

    This is useful when you want to allow access either by role (e.g., ADMIN)
    or by specific permission (e.g., AGENTS_DELETE).

    Example:
        >>> dep = RoleOrPermissionRequired(
        ...     roles=[Role.ADMIN],
        ...     permissions=[Permission.AGENTS_DELETE]
        ... )
        >>>
        >>> @router.delete("/agents/{agent_id}")
        >>> async def delete_agent(
        ...     agent_id: str,
        ...     user: UserInfo = Depends(get_current_user),
        ...     _: None = Depends(dep)
        ... ):
        ...     return {"deleted": agent_id}
    """

    def __init__(
        self,
        roles: List[Role] = None,
        permissions: List[Permission] = None,
        rbac_service: RBACService = None,
    ):
        """
        Initialize combined role/permission requirement dependency.

        Args:
            roles: List of roles (user needs at least one)
            permissions: List of permissions (user needs at least one)
            rbac_service: Optional RBAC service instance (uses global if not provided)
        """
        self.roles = roles or []
        self.permissions = permissions or []
        self.rbac_service = rbac_service or get_rbac_service()

        if not self.roles and not self.permissions:
            raise ValueError("Must specify at least one role or permission")

    async def __call__(self, user: UserInfo = Depends(get_current_user)) -> None:
        """
        Check if user has required roles or permissions.

        Args:
            user: Authenticated user information

        Raises:
            HTTPException: 403 if user lacks both required roles and permissions
        """
        # Check if user has any required role
        if self.roles and self.rbac_service.has_any_role(user, self.roles):
            logger.debug(f"User {user.id} authorized via role")
            return

        # Check if user has any required permission
        if self.permissions and self.rbac_service.has_any_permission(
            user, self.permissions
        ):
            logger.debug(f"User {user.id} authorized via permission")
            return

        # User has neither required roles nor permissions
        logger.warning(
            f"User {user.id} denied access: requires role "
            f"{[r.value for r in self.roles]} or permission "
            f"{[p.value for p in self.permissions]}"
        )

        role_names = ", ".join(r.value for r in self.roles) if self.roles else "none"
        perm_names = (
            ", ".join(p.value for p in self.permissions) if self.permissions else "none"
        )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Required roles: {role_names} OR permissions: {perm_names}",
        )


def require_role_or_permission(
    roles: List[Role] = None,
    permissions: List[Permission] = None,
) -> RoleOrPermissionRequired:
    """
    Create a dependency that requires either a role OR a permission.

    This is useful for flexible access control where you want to allow
    access by either role or specific permission.

    Args:
        roles: List of roles (user needs at least one)
        permissions: List of permissions (user needs at least one)

    Returns:
        RoleOrPermissionRequired dependency instance

    Example:
        >>> @router.delete("/agents/{agent_id}")
        >>> async def delete_agent(
        ...     agent_id: str,
        ...     user: UserInfo = Depends(get_current_user),
        ...     _: None = Depends(require_role_or_permission(
        ...         roles=[Role.ADMIN],
        ...         permissions=[Permission.AGENTS_DELETE]
        ...     ))
        ... ):
        ...     return {"deleted": agent_id}
    """
    return RoleOrPermissionRequired(roles=roles, permissions=permissions)


# Utility function to get user with RBAC info


async def get_current_user_with_rbac(
    user: UserInfo = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> tuple[UserInfo, RBACService]:
    """
    Get current user along with RBAC service instance.

    This is a convenience dependency that provides both the authenticated
    user and the RBAC service, useful for routes that need to perform
    multiple permission checks.

    Args:
        user: Authenticated user from get_current_user
        rbac_service: RBAC service instance

    Returns:
        Tuple of (user, rbac_service)

    Example:
        >>> @router.get("/complex-route")
        >>> async def complex_route(
        ...     user_rbac: tuple[UserInfo, RBACService] = Depends(get_current_user_with_rbac)
        ... ):
        ...     user, rbac = user_rbac
        ...     if rbac.has_permission(user, Permission.AGENTS_READ):
        ...         # Do something
        ...     return {"message": "Success"}
    """
    return user, rbac_service
