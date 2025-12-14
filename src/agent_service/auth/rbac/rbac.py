"""
RBAC service for permission checking and authorization.

This module provides the core RBAC service that handles permission checking,
role evaluation, and authorization logic. It supports:
- Permission checking based on roles
- Custom permission overrides per user
- Role hierarchy with inheritance
- Integration with Azure AD and AWS Cognito groups
"""

import logging
from typing import Optional

from ..schemas import UserInfo
from .permissions import Permission, permission_implies
from .roles import (
    Role,
    get_permissions_for_role,
    get_roles_from_groups,
    get_roles_from_strings,
    get_highest_role,
)

logger = logging.getLogger(__name__)


class RBACService:
    """
    Role-Based Access Control service.

    This service provides methods for checking permissions based on user roles,
    custom permissions, and role hierarchy. It's the central component for
    authorization decisions in the application.

    Features:
        - Role-based permission checking
        - Custom per-user permission overrides
        - Role hierarchy with inheritance
        - Azure AD and Cognito group integration
        - Permission implication (e.g., ADMIN_FULL grants everything)
    """

    def __init__(
        self,
        enable_hierarchy: bool = True,
        enable_custom_permissions: bool = True,
    ):
        """
        Initialize the RBAC service.

        Args:
            enable_hierarchy: If True, higher roles inherit permissions from lower roles
            enable_custom_permissions: If True, allow user-specific permission overrides
        """
        self.enable_hierarchy = enable_hierarchy
        self.enable_custom_permissions = enable_custom_permissions

        logger.info(
            f"Initialized RBAC service (hierarchy={enable_hierarchy}, "
            f"custom_permissions={enable_custom_permissions})"
        )

    def get_permissions_for_role(self, role: Role) -> set[Permission]:
        """
        Get all permissions for a specific role.

        Args:
            role: The role to get permissions for

        Returns:
            Set of permissions granted by the role

        Example:
            >>> rbac = RBACService()
            >>> rbac.get_permissions_for_role(Role.ADMIN)
            {Permission.AGENTS_READ, Permission.AGENTS_WRITE, ...}
        """
        return get_permissions_for_role(role, include_hierarchy=self.enable_hierarchy)

    def get_permissions_for_roles(self, roles: list[Role]) -> set[Permission]:
        """
        Get combined permissions for multiple roles.

        When a user has multiple roles, they receive the union of all
        permissions from those roles.

        Args:
            roles: List of roles to get permissions for

        Returns:
            Set of all permissions granted by any of the roles

        Example:
            >>> rbac = RBACService()
            >>> rbac.get_permissions_for_roles([Role.USER, Role.DEVELOPER])
            {Permission.AGENTS_READ, Permission.AGENTS_WRITE, ...}
        """
        permissions: set[Permission] = set()

        for role in roles:
            permissions.update(self.get_permissions_for_role(role))

        return permissions

    def get_user_roles(self, user: UserInfo) -> set[Role]:
        """
        Extract roles from user information.

        This method extracts roles from:
        1. User's direct roles (from JWT claims)
        2. User's groups (Azure AD or Cognito groups)

        Args:
            user: User information from authentication

        Returns:
            Set of roles for the user

        Example:
            >>> rbac = RBACService()
            >>> roles = rbac.get_user_roles(user)
            >>> Role.ADMIN in roles
            True
        """
        roles: set[Role] = set()

        # Extract roles from user.roles (direct role assignments)
        if user.roles:
            roles.update(get_roles_from_strings(user.roles))

        # Extract roles from user.groups (Azure AD or Cognito groups)
        if user.groups:
            roles.update(get_roles_from_groups(user.groups))

        logger.debug(
            f"Extracted roles for user {user.id}: {[r.value for r in roles]}"
        )

        return roles

    def get_user_permissions(self, user: UserInfo) -> set[Permission]:
        """
        Get all permissions for a user based on their roles and custom permissions.

        This method combines:
        1. Permissions from user's roles
        2. Custom permissions from user metadata (if enabled)

        Args:
            user: User information from authentication

        Returns:
            Set of all permissions the user has

        Example:
            >>> rbac = RBACService()
            >>> permissions = rbac.get_user_permissions(user)
            >>> Permission.AGENTS_READ in permissions
            True
        """
        permissions: set[Permission] = set()

        # Get permissions from roles
        roles = self.get_user_roles(user)
        permissions.update(self.get_permissions_for_roles(list(roles)))

        # Add custom permissions from user metadata (if enabled)
        if self.enable_custom_permissions and user.metadata:
            custom_perms = user.metadata.get("permissions", [])
            if isinstance(custom_perms, list):
                for perm_str in custom_perms:
                    try:
                        permission = Permission(perm_str)
                        permissions.add(permission)
                        logger.debug(
                            f"Added custom permission {permission.value} for user {user.id}"
                        )
                    except ValueError:
                        logger.warning(
                            f"Invalid custom permission '{perm_str}' for user {user.id}"
                        )

        logger.debug(
            f"Total permissions for user {user.id}: {len(permissions)}"
        )

        return permissions

    def has_permission(self, user: UserInfo, permission: Permission) -> bool:
        """
        Check if a user has a specific permission.

        This method checks:
        1. Direct permission grants from roles
        2. Custom permissions from user metadata
        3. Permission implications (e.g., ADMIN_FULL grants everything)

        Args:
            user: User information from authentication
            permission: The permission to check

        Returns:
            True if user has the permission, False otherwise

        Example:
            >>> rbac = RBACService()
            >>> rbac.has_permission(user, Permission.AGENTS_READ)
            True
        """
        user_permissions = self.get_user_permissions(user)

        # Check direct permission match
        if permission in user_permissions:
            return True

        # Check permission implications
        # For example, ADMIN_FULL grants all permissions
        for granted_perm in user_permissions:
            if permission_implies(granted_perm, permission):
                logger.debug(
                    f"Permission {granted_perm.value} implies {permission.value} "
                    f"for user {user.id}"
                )
                return True

        logger.debug(
            f"User {user.id} does not have permission {permission.value}"
        )
        return False

    def has_any_permission(
        self, user: UserInfo, permissions: list[Permission]
    ) -> bool:
        """
        Check if a user has at least one of the specified permissions.

        Args:
            user: User information from authentication
            permissions: List of permissions to check

        Returns:
            True if user has at least one permission, False otherwise

        Example:
            >>> rbac = RBACService()
            >>> rbac.has_any_permission(user, [
            ...     Permission.AGENTS_READ,
            ...     Permission.AGENTS_WRITE
            ... ])
            True
        """
        for permission in permissions:
            if self.has_permission(user, permission):
                return True

        logger.debug(
            f"User {user.id} does not have any of the required permissions"
        )
        return False

    def has_all_permissions(
        self, user: UserInfo, permissions: list[Permission]
    ) -> bool:
        """
        Check if a user has all of the specified permissions.

        Args:
            user: User information from authentication
            permissions: List of permissions to check

        Returns:
            True if user has all permissions, False otherwise

        Example:
            >>> rbac = RBACService()
            >>> rbac.has_all_permissions(user, [
            ...     Permission.AGENTS_READ,
            ...     Permission.AGENTS_WRITE
            ... ])
            True
        """
        for permission in permissions:
            if not self.has_permission(user, permission):
                logger.debug(
                    f"User {user.id} missing required permission {permission.value}"
                )
                return False

        return True

    def has_role(self, user: UserInfo, role: Role) -> bool:
        """
        Check if a user has a specific role.

        Args:
            user: User information from authentication
            role: The role to check

        Returns:
            True if user has the role, False otherwise

        Example:
            >>> rbac = RBACService()
            >>> rbac.has_role(user, Role.ADMIN)
            True
        """
        user_roles = self.get_user_roles(user)
        result = role in user_roles

        logger.debug(
            f"User {user.id} {'has' if result else 'does not have'} role {role.value}"
        )

        return result

    def has_any_role(self, user: UserInfo, roles: list[Role]) -> bool:
        """
        Check if a user has at least one of the specified roles.

        Args:
            user: User information from authentication
            roles: List of roles to check

        Returns:
            True if user has at least one role, False otherwise

        Example:
            >>> rbac = RBACService()
            >>> rbac.has_any_role(user, [Role.ADMIN, Role.DEVELOPER])
            True
        """
        user_roles = self.get_user_roles(user)

        for role in roles:
            if role in user_roles:
                logger.debug(f"User {user.id} has role {role.value}")
                return True

        logger.debug(
            f"User {user.id} does not have any of the required roles"
        )
        return False

    def has_all_roles(self, user: UserInfo, roles: list[Role]) -> bool:
        """
        Check if a user has all of the specified roles.

        Args:
            user: User information from authentication
            roles: List of roles to check

        Returns:
            True if user has all roles, False otherwise

        Example:
            >>> rbac = RBACService()
            >>> rbac.has_all_roles(user, [Role.ADMIN, Role.DEVELOPER])
            False
        """
        user_roles = self.get_user_roles(user)

        for role in roles:
            if role not in user_roles:
                logger.debug(f"User {user.id} missing required role {role.value}")
                return False

        return True

    def get_highest_user_role(self, user: UserInfo) -> Optional[Role]:
        """
        Get the highest role a user has based on the role hierarchy.

        Args:
            user: User information from authentication

        Returns:
            The highest role the user has, or None if user has no roles

        Example:
            >>> rbac = RBACService()
            >>> rbac.get_highest_user_role(user)
            Role.ADMIN
        """
        user_roles = self.get_user_roles(user)
        highest_role = get_highest_role(user_roles)

        if highest_role:
            logger.debug(
                f"Highest role for user {user.id}: {highest_role.value}"
            )
        else:
            logger.debug(f"User {user.id} has no roles")

        return highest_role

    def add_custom_permission(
        self, user: UserInfo, permission: Permission
    ) -> UserInfo:
        """
        Add a custom permission to a user's metadata.

        Note: This modifies the UserInfo object but does not persist to any
        database. It's meant for runtime permission grants.

        Args:
            user: User information to modify
            permission: Permission to add

        Returns:
            Updated UserInfo object

        Example:
            >>> rbac = RBACService()
            >>> user = rbac.add_custom_permission(user, Permission.AGENTS_DELETE)
        """
        if not self.enable_custom_permissions:
            logger.warning(
                "Custom permissions are disabled, cannot add permission"
            )
            return user

        if "permissions" not in user.metadata:
            user.metadata["permissions"] = []

        if permission.value not in user.metadata["permissions"]:
            user.metadata["permissions"].append(permission.value)
            logger.info(
                f"Added custom permission {permission.value} to user {user.id}"
            )

        return user

    def remove_custom_permission(
        self, user: UserInfo, permission: Permission
    ) -> UserInfo:
        """
        Remove a custom permission from a user's metadata.

        Note: This modifies the UserInfo object but does not persist to any
        database. It's meant for runtime permission revocation.

        Args:
            user: User information to modify
            permission: Permission to remove

        Returns:
            Updated UserInfo object

        Example:
            >>> rbac = RBACService()
            >>> user = rbac.remove_custom_permission(user, Permission.AGENTS_DELETE)
        """
        if not self.enable_custom_permissions:
            logger.warning(
                "Custom permissions are disabled, cannot remove permission"
            )
            return user

        if "permissions" in user.metadata:
            if permission.value in user.metadata["permissions"]:
                user.metadata["permissions"].remove(permission.value)
                logger.info(
                    f"Removed custom permission {permission.value} from user {user.id}"
                )

        return user


# Global RBAC service instance
_rbac_service: Optional[RBACService] = None


def get_rbac_service() -> RBACService:
    """
    Get the global RBAC service instance.

    This creates a singleton instance of the RBAC service that can be
    used throughout the application.

    Returns:
        The global RBACService instance

    Example:
        >>> rbac = get_rbac_service()
        >>> rbac.has_permission(user, Permission.AGENTS_READ)
        True
    """
    global _rbac_service

    if _rbac_service is None:
        _rbac_service = RBACService()
        logger.info("Created global RBAC service instance")

    return _rbac_service


def set_rbac_service(rbac_service: RBACService) -> None:
    """
    Set a custom RBAC service instance.

    This allows applications to configure the RBAC service with specific
    settings (e.g., disable hierarchy, disable custom permissions).

    Args:
        rbac_service: The RBAC service instance to use globally

    Example:
        >>> custom_rbac = RBACService(enable_hierarchy=False)
        >>> set_rbac_service(custom_rbac)
    """
    global _rbac_service
    _rbac_service = rbac_service
    logger.info("Set custom RBAC service instance")
