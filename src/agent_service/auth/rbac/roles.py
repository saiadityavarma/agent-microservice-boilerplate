"""
Role definitions and role-to-permission mappings for RBAC.

This module defines the role hierarchy and the default permissions assigned
to each role. Roles represent collections of permissions that can be assigned
to users through Azure AD groups, AWS Cognito groups, or directly.

Role Hierarchy (from least to most privileged):
    VIEWER -> USER -> DEVELOPER -> ADMIN -> SUPER_ADMIN
"""

from enum import Enum, unique
from typing import Optional

from .permissions import Permission, PermissionGroups


@unique
class Role(str, Enum):
    """
    System roles with hierarchical permissions.

    Roles define broad user categories with specific sets of permissions.
    Higher roles inherit permissions from lower roles in the hierarchy.

    Role Hierarchy:
        VIEWER: Read-only access to all resources
        USER: VIEWER + execute agents and tools
        DEVELOPER: USER + create/modify agents and tools
        ADMIN: DEVELOPER + manage users and API keys
        SUPER_ADMIN: All permissions including full admin access
    """

    VIEWER = "viewer"
    USER = "user"
    DEVELOPER = "developer"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


# Default permissions for each role
DEFAULT_ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    # VIEWER: Read-only access to all resources
    Role.VIEWER: {
        Permission.AGENTS_READ,
        Permission.TOOLS_READ,
        Permission.USERS_READ,
        Permission.API_KEYS_READ,
        Permission.AUDIT_READ,
    },
    # USER: VIEWER + execute agents and tools
    Role.USER: {
        Permission.AGENTS_READ,
        Permission.AGENTS_EXECUTE,
        Permission.TOOLS_READ,
        Permission.TOOLS_EXECUTE,
        Permission.USERS_READ,
        Permission.API_KEYS_READ,
        Permission.AUDIT_READ,
    },
    # DEVELOPER: USER + create/modify agents and tools (no delete users)
    Role.DEVELOPER: {
        Permission.AGENTS_READ,
        Permission.AGENTS_WRITE,
        Permission.AGENTS_DELETE,
        Permission.AGENTS_EXECUTE,
        Permission.TOOLS_READ,
        Permission.TOOLS_WRITE,
        Permission.TOOLS_DELETE,
        Permission.TOOLS_EXECUTE,
        Permission.USERS_READ,
        Permission.API_KEYS_READ,
        Permission.API_KEYS_WRITE,
        Permission.API_KEYS_DELETE,
        Permission.AUDIT_READ,
    },
    # ADMIN: DEVELOPER + manage users and API keys (all except SUPER_ADMIN)
    Role.ADMIN: {
        Permission.AGENTS_READ,
        Permission.AGENTS_WRITE,
        Permission.AGENTS_DELETE,
        Permission.AGENTS_EXECUTE,
        Permission.TOOLS_READ,
        Permission.TOOLS_WRITE,
        Permission.TOOLS_DELETE,
        Permission.TOOLS_EXECUTE,
        Permission.USERS_READ,
        Permission.USERS_WRITE,
        Permission.USERS_DELETE,
        Permission.API_KEYS_READ,
        Permission.API_KEYS_WRITE,
        Permission.API_KEYS_DELETE,
        Permission.AUDIT_READ,
    },
    # SUPER_ADMIN: Everything including full admin access
    Role.SUPER_ADMIN: {
        Permission.AGENTS_READ,
        Permission.AGENTS_WRITE,
        Permission.AGENTS_DELETE,
        Permission.AGENTS_EXECUTE,
        Permission.TOOLS_READ,
        Permission.TOOLS_WRITE,
        Permission.TOOLS_DELETE,
        Permission.TOOLS_EXECUTE,
        Permission.USERS_READ,
        Permission.USERS_WRITE,
        Permission.USERS_DELETE,
        Permission.API_KEYS_READ,
        Permission.API_KEYS_WRITE,
        Permission.API_KEYS_DELETE,
        Permission.ADMIN_FULL,
        Permission.AUDIT_READ,
    },
}


# Role hierarchy - higher roles inherit permissions from lower roles
ROLE_HIERARCHY: dict[Role, list[Role]] = {
    Role.VIEWER: [],
    Role.USER: [Role.VIEWER],
    Role.DEVELOPER: [Role.USER, Role.VIEWER],
    Role.ADMIN: [Role.DEVELOPER, Role.USER, Role.VIEWER],
    Role.SUPER_ADMIN: [Role.ADMIN, Role.DEVELOPER, Role.USER, Role.VIEWER],
}


# Mapping from Azure AD/Cognito group names to roles
# This can be customized based on your organization's group naming conventions
DEFAULT_GROUP_TO_ROLE: dict[str, Role] = {
    # Azure AD group names (examples)
    "AgentService.Viewers": Role.VIEWER,
    "AgentService.Users": Role.USER,
    "AgentService.Developers": Role.DEVELOPER,
    "AgentService.Admins": Role.ADMIN,
    "AgentService.SuperAdmins": Role.SUPER_ADMIN,
    # AWS Cognito group names (examples)
    "agent-service-viewers": Role.VIEWER,
    "agent-service-users": Role.USER,
    "agent-service-developers": Role.DEVELOPER,
    "agent-service-admins": Role.ADMIN,
    "agent-service-super-admins": Role.SUPER_ADMIN,
    # Generic role names (case-insensitive)
    "viewer": Role.VIEWER,
    "user": Role.USER,
    "developer": Role.DEVELOPER,
    "admin": Role.ADMIN,
    "super_admin": Role.SUPER_ADMIN,
    "superadmin": Role.SUPER_ADMIN,
}


def get_permissions_for_role(role: Role, include_hierarchy: bool = True) -> set[Permission]:
    """
    Get all permissions for a specific role.

    Args:
        role: The role to get permissions for
        include_hierarchy: If True, include permissions from parent roles in the hierarchy

    Returns:
        Set of permissions for the role

    Example:
        >>> get_permissions_for_role(Role.USER)
        {Permission.AGENTS_READ, Permission.AGENTS_EXECUTE, ...}
    """
    permissions = set(DEFAULT_ROLE_PERMISSIONS.get(role, set()))

    # If hierarchy is enabled, add permissions from parent roles
    if include_hierarchy:
        parent_roles = ROLE_HIERARCHY.get(role, [])
        for parent_role in parent_roles:
            permissions.update(DEFAULT_ROLE_PERMISSIONS.get(parent_role, set()))

    return permissions


def get_role_from_string(role_str: str) -> Optional[Role]:
    """
    Convert a string to a Role enum, case-insensitive.

    Args:
        role_str: String representation of the role

    Returns:
        Role enum or None if not found

    Example:
        >>> get_role_from_string("ADMIN")
        Role.ADMIN
        >>> get_role_from_string("invalid")
        None
    """
    try:
        return Role(role_str.lower())
    except (ValueError, AttributeError):
        return None


def get_roles_from_groups(groups: list[str]) -> set[Role]:
    """
    Extract roles from Azure AD or Cognito group names.

    This function maps group names to roles based on the DEFAULT_GROUP_TO_ROLE
    mapping. It's case-insensitive and handles both Azure AD and Cognito group
    naming conventions.

    Args:
        groups: List of group names from Azure AD or Cognito

    Returns:
        Set of roles derived from the groups

    Example:
        >>> get_roles_from_groups(["AgentService.Admins", "AgentService.Users"])
        {Role.ADMIN, Role.USER}
    """
    roles: set[Role] = set()

    for group in groups:
        # Try exact match first
        if group in DEFAULT_GROUP_TO_ROLE:
            roles.add(DEFAULT_GROUP_TO_ROLE[group])
            continue

        # Try case-insensitive match
        group_lower = group.lower()
        for group_name, role in DEFAULT_GROUP_TO_ROLE.items():
            if group_name.lower() == group_lower:
                roles.add(role)
                break

    return roles


def get_roles_from_strings(role_strings: list[str]) -> set[Role]:
    """
    Convert a list of role strings to Role enums.

    This is useful when roles are provided as strings in JWT claims
    or configuration files.

    Args:
        role_strings: List of role names as strings

    Returns:
        Set of valid roles (invalid strings are skipped)

    Example:
        >>> get_roles_from_strings(["admin", "user", "invalid"])
        {Role.ADMIN, Role.USER}
    """
    roles: set[Role] = set()

    for role_str in role_strings:
        role = get_role_from_string(role_str)
        if role:
            roles.add(role)

    return roles


def role_hierarchy_includes(higher_role: Role, lower_role: Role) -> bool:
    """
    Check if a higher role includes a lower role in the hierarchy.

    Args:
        higher_role: The role to check
        lower_role: The role that might be included

    Returns:
        True if higher_role includes lower_role in the hierarchy

    Example:
        >>> role_hierarchy_includes(Role.ADMIN, Role.USER)
        True
        >>> role_hierarchy_includes(Role.USER, Role.ADMIN)
        False
    """
    if higher_role == lower_role:
        return True

    parent_roles = ROLE_HIERARCHY.get(higher_role, [])
    return lower_role in parent_roles


def get_highest_role(roles: set[Role]) -> Optional[Role]:
    """
    Get the highest role from a set of roles based on the hierarchy.

    Args:
        roles: Set of roles to evaluate

    Returns:
        The highest role in the hierarchy, or None if no roles provided

    Example:
        >>> get_highest_role({Role.USER, Role.ADMIN, Role.VIEWER})
        Role.ADMIN
    """
    if not roles:
        return None

    # Define role priority (higher number = higher privilege)
    role_priority = {
        Role.VIEWER: 1,
        Role.USER: 2,
        Role.DEVELOPER: 3,
        Role.ADMIN: 4,
        Role.SUPER_ADMIN: 5,
    }

    return max(roles, key=lambda r: role_priority.get(r, 0))


def update_group_to_role_mapping(custom_mapping: dict[str, Role]) -> None:
    """
    Update the default group-to-role mapping with custom mappings.

    This allows organizations to customize the group names that map to roles
    based on their Azure AD or Cognito group naming conventions.

    Args:
        custom_mapping: Dictionary mapping group names to roles

    Example:
        >>> update_group_to_role_mapping({
        ...     "MyCompany-Admins": Role.ADMIN,
        ...     "MyCompany-Devs": Role.DEVELOPER,
        ... })
    """
    DEFAULT_GROUP_TO_ROLE.update(custom_mapping)
