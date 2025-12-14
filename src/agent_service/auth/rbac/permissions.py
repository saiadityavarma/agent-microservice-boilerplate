"""
Permission definitions for Role-Based Access Control (RBAC).

This module defines all available permissions in the system using an enum.
Permissions are organized by resource type (agents, tools, users, etc.) and
operation type (read, write, delete, execute).

Permissions are the building blocks of the RBAC system and are assigned to roles.
Each role receives a set of permissions that determine what actions users with
that role can perform.
"""

from enum import Enum, unique


@unique
class Permission(str, Enum):
    """
    System-wide permissions for access control.

    Permissions follow a naming convention: RESOURCE_OPERATION
    where RESOURCE is the entity type and OPERATION is the action.

    Permission Groups:
        - AGENTS_*: Agent management and execution
        - TOOLS_*: Tool management and execution
        - USERS_*: User management
        - API_KEYS_*: API key management
        - ADMIN_*: Administrative operations
        - AUDIT_*: Audit log access
    """

    # Agent permissions
    AGENTS_READ = "agents:read"
    AGENTS_WRITE = "agents:write"
    AGENTS_DELETE = "agents:delete"
    AGENTS_EXECUTE = "agents:execute"

    # Tool permissions
    TOOLS_READ = "tools:read"
    TOOLS_WRITE = "tools:write"
    TOOLS_DELETE = "tools:delete"
    TOOLS_EXECUTE = "tools:execute"

    # User permissions
    USERS_READ = "users:read"
    USERS_WRITE = "users:write"
    USERS_DELETE = "users:delete"

    # API key permissions
    API_KEYS_READ = "api_keys:read"
    API_KEYS_WRITE = "api_keys:write"
    API_KEYS_DELETE = "api_keys:delete"

    # Administrative permissions
    ADMIN_FULL = "admin:full"
    AUDIT_READ = "audit:read"


# Permission groups for easier management
class PermissionGroups:
    """
    Logical groupings of permissions by resource type.

    These groups make it easier to assign related permissions to roles
    and to check if a user has access to a particular resource category.
    """

    # All agent-related permissions
    AGENTS_ALL: set[Permission] = {
        Permission.AGENTS_READ,
        Permission.AGENTS_WRITE,
        Permission.AGENTS_DELETE,
        Permission.AGENTS_EXECUTE,
    }

    # Read-only agent permissions
    AGENTS_READ_ONLY: set[Permission] = {
        Permission.AGENTS_READ,
    }

    # Agent execution (read + execute)
    AGENTS_EXECUTE_ONLY: set[Permission] = {
        Permission.AGENTS_READ,
        Permission.AGENTS_EXECUTE,
    }

    # Agent management (read + write, no delete)
    AGENTS_MANAGE: set[Permission] = {
        Permission.AGENTS_READ,
        Permission.AGENTS_WRITE,
        Permission.AGENTS_EXECUTE,
    }

    # All tool-related permissions
    TOOLS_ALL: set[Permission] = {
        Permission.TOOLS_READ,
        Permission.TOOLS_WRITE,
        Permission.TOOLS_DELETE,
        Permission.TOOLS_EXECUTE,
    }

    # Read-only tool permissions
    TOOLS_READ_ONLY: set[Permission] = {
        Permission.TOOLS_READ,
    }

    # Tool execution (read + execute)
    TOOLS_EXECUTE_ONLY: set[Permission] = {
        Permission.TOOLS_READ,
        Permission.TOOLS_EXECUTE,
    }

    # Tool management (read + write, no delete)
    TOOLS_MANAGE: set[Permission] = {
        Permission.TOOLS_READ,
        Permission.TOOLS_WRITE,
        Permission.TOOLS_EXECUTE,
    }

    # All user-related permissions
    USERS_ALL: set[Permission] = {
        Permission.USERS_READ,
        Permission.USERS_WRITE,
        Permission.USERS_DELETE,
    }

    # Read-only user permissions
    USERS_READ_ONLY: set[Permission] = {
        Permission.USERS_READ,
    }

    # User management (read + write, no delete)
    USERS_MANAGE: set[Permission] = {
        Permission.USERS_READ,
        Permission.USERS_WRITE,
    }

    # All API key-related permissions
    API_KEYS_ALL: set[Permission] = {
        Permission.API_KEYS_READ,
        Permission.API_KEYS_WRITE,
        Permission.API_KEYS_DELETE,
    }

    # Read-only API key permissions
    API_KEYS_READ_ONLY: set[Permission] = {
        Permission.API_KEYS_READ,
    }

    # API key management (read + write, no delete)
    API_KEYS_MANAGE: set[Permission] = {
        Permission.API_KEYS_READ,
        Permission.API_KEYS_WRITE,
    }

    # All read permissions across all resources
    ALL_READ: set[Permission] = {
        Permission.AGENTS_READ,
        Permission.TOOLS_READ,
        Permission.USERS_READ,
        Permission.API_KEYS_READ,
        Permission.AUDIT_READ,
    }

    # All write permissions across all resources
    ALL_WRITE: set[Permission] = {
        Permission.AGENTS_WRITE,
        Permission.TOOLS_WRITE,
        Permission.USERS_WRITE,
        Permission.API_KEYS_WRITE,
    }

    # All delete permissions across all resources
    ALL_DELETE: set[Permission] = {
        Permission.AGENTS_DELETE,
        Permission.TOOLS_DELETE,
        Permission.USERS_DELETE,
        Permission.API_KEYS_DELETE,
    }

    # All execute permissions
    ALL_EXECUTE: set[Permission] = {
        Permission.AGENTS_EXECUTE,
        Permission.TOOLS_EXECUTE,
    }


def get_permissions_by_resource(resource: str) -> set[Permission]:
    """
    Get all permissions for a specific resource type.

    Args:
        resource: Resource type (agents, tools, users, api_keys)

    Returns:
        Set of all permissions for the resource

    Example:
        >>> get_permissions_by_resource("agents")
        {Permission.AGENTS_READ, Permission.AGENTS_WRITE, ...}
    """
    resource_map = {
        "agents": PermissionGroups.AGENTS_ALL,
        "tools": PermissionGroups.TOOLS_ALL,
        "users": PermissionGroups.USERS_ALL,
        "api_keys": PermissionGroups.API_KEYS_ALL,
    }
    return resource_map.get(resource.lower(), set())


def get_permissions_by_operation(operation: str) -> set[Permission]:
    """
    Get all permissions for a specific operation type.

    Args:
        operation: Operation type (read, write, delete, execute)

    Returns:
        Set of all permissions for the operation

    Example:
        >>> get_permissions_by_operation("read")
        {Permission.AGENTS_READ, Permission.TOOLS_READ, ...}
    """
    operation_map = {
        "read": PermissionGroups.ALL_READ,
        "write": PermissionGroups.ALL_WRITE,
        "delete": PermissionGroups.ALL_DELETE,
        "execute": PermissionGroups.ALL_EXECUTE,
    }
    return operation_map.get(operation.lower(), set())


def permission_implies(granted: Permission, required: Permission) -> bool:
    """
    Check if a granted permission implies another required permission.

    Some permissions grant broader access that includes other permissions.
    For example, ADMIN_FULL grants all permissions.

    Args:
        granted: Permission that has been granted
        required: Permission that is required

    Returns:
        True if granted permission implies the required permission

    Example:
        >>> permission_implies(Permission.ADMIN_FULL, Permission.AGENTS_READ)
        True
        >>> permission_implies(Permission.AGENTS_READ, Permission.AGENTS_WRITE)
        False
    """
    # ADMIN_FULL grants all permissions
    if granted == Permission.ADMIN_FULL:
        return True

    # Same permission
    if granted == required:
        return True

    return False
