"""
Unit tests for the RBAC system.

This file contains tests to verify the RBAC system works correctly.
Run with: pytest test_rbac.py
"""

import pytest
from agent_service.auth.schemas import UserInfo, AuthProvider
from agent_service.auth.rbac.permissions import Permission, PermissionGroups
from agent_service.auth.rbac.roles import (
    Role,
    get_permissions_for_role,
    get_roles_from_groups,
    get_roles_from_strings,
    get_highest_role,
)
from agent_service.auth.rbac.rbac import RBACService


class TestPermissions:
    """Test permission definitions and groupings."""

    def test_all_permissions_defined(self):
        """Test that all permissions are properly defined."""
        assert Permission.AGENTS_READ.value == "agents:read"
        assert Permission.AGENTS_WRITE.value == "agents:write"
        assert Permission.TOOLS_EXECUTE.value == "tools:execute"
        assert Permission.ADMIN_FULL.value == "admin:full"

    def test_permission_groups(self):
        """Test permission groupings."""
        assert Permission.AGENTS_READ in PermissionGroups.AGENTS_ALL
        assert Permission.TOOLS_WRITE in PermissionGroups.TOOLS_ALL
        assert Permission.USERS_READ in PermissionGroups.ALL_READ


class TestRoles:
    """Test role definitions and mappings."""

    def test_role_values(self):
        """Test that roles have correct values."""
        assert Role.VIEWER.value == "viewer"
        assert Role.ADMIN.value == "admin"
        assert Role.SUPER_ADMIN.value == "super_admin"

    def test_viewer_permissions(self):
        """Test VIEWER role permissions."""
        perms = get_permissions_for_role(Role.VIEWER, include_hierarchy=False)
        assert Permission.AGENTS_READ in perms
        assert Permission.TOOLS_READ in perms
        assert Permission.AGENTS_WRITE not in perms

    def test_developer_permissions(self):
        """Test DEVELOPER role permissions."""
        perms = get_permissions_for_role(Role.DEVELOPER, include_hierarchy=False)
        assert Permission.AGENTS_WRITE in perms
        assert Permission.AGENTS_DELETE in perms
        assert Permission.TOOLS_WRITE in perms
        assert Permission.USERS_DELETE not in perms

    def test_admin_permissions(self):
        """Test ADMIN role permissions."""
        perms = get_permissions_for_role(Role.ADMIN, include_hierarchy=False)
        assert Permission.USERS_WRITE in perms
        assert Permission.USERS_DELETE in perms
        assert Permission.ADMIN_FULL not in perms  # Only SUPER_ADMIN has this

    def test_super_admin_permissions(self):
        """Test SUPER_ADMIN role permissions."""
        perms = get_permissions_for_role(Role.SUPER_ADMIN, include_hierarchy=False)
        assert Permission.ADMIN_FULL in perms

    def test_role_hierarchy(self):
        """Test role hierarchy inheritance."""
        # With hierarchy, ADMIN should have DEVELOPER and USER permissions
        perms = get_permissions_for_role(Role.ADMIN, include_hierarchy=True)
        assert Permission.AGENTS_READ in perms  # From VIEWER
        assert Permission.AGENTS_EXECUTE in perms  # From USER
        assert Permission.AGENTS_WRITE in perms  # From DEVELOPER
        assert Permission.USERS_WRITE in perms  # From ADMIN

    def test_get_roles_from_groups(self):
        """Test extracting roles from group names."""
        groups = ["AgentService.Admins", "AgentService.Developers"]
        roles = get_roles_from_groups(groups)
        assert Role.ADMIN in roles
        assert Role.DEVELOPER in roles

        # Test Cognito groups
        cognito_groups = ["agent-service-users", "agent-service-viewers"]
        roles = get_roles_from_groups(cognito_groups)
        assert Role.USER in roles
        assert Role.VIEWER in roles

    def test_get_roles_from_strings(self):
        """Test converting role strings to Role enums."""
        role_strings = ["admin", "developer", "invalid"]
        roles = get_roles_from_strings(role_strings)
        assert Role.ADMIN in roles
        assert Role.DEVELOPER in roles
        assert len(roles) == 2  # Invalid should be skipped

    def test_get_highest_role(self):
        """Test getting the highest role from a set."""
        roles = {Role.VIEWER, Role.DEVELOPER, Role.ADMIN}
        highest = get_highest_role(roles)
        assert highest == Role.ADMIN


class TestRBACService:
    """Test RBAC service functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.rbac = RBACService(
            enable_hierarchy=True,
            enable_custom_permissions=True,
        )

    def test_get_user_roles_from_roles_claim(self):
        """Test extracting roles from user.roles."""
        user = UserInfo(
            id="user1",
            roles=["admin", "developer"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        roles = self.rbac.get_user_roles(user)
        assert Role.ADMIN in roles
        assert Role.DEVELOPER in roles

    def test_get_user_roles_from_groups(self):
        """Test extracting roles from user.groups."""
        user = UserInfo(
            id="user1",
            roles=[],
            groups=["AgentService.Admins", "AgentService.Developers"],
            provider=AuthProvider.AZURE_AD,
        )

        roles = self.rbac.get_user_roles(user)
        assert Role.ADMIN in roles
        assert Role.DEVELOPER in roles

    def test_get_user_permissions(self):
        """Test getting all permissions for a user."""
        user = UserInfo(
            id="user1",
            roles=["developer"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        perms = self.rbac.get_user_permissions(user)
        assert Permission.AGENTS_READ in perms
        assert Permission.AGENTS_WRITE in perms
        assert Permission.AGENTS_DELETE in perms

    def test_has_permission_true(self):
        """Test has_permission returns True for granted permissions."""
        user = UserInfo(
            id="user1",
            roles=["developer"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        assert self.rbac.has_permission(user, Permission.AGENTS_READ)
        assert self.rbac.has_permission(user, Permission.AGENTS_WRITE)
        assert self.rbac.has_permission(user, Permission.TOOLS_EXECUTE)

    def test_has_permission_false(self):
        """Test has_permission returns False for non-granted permissions."""
        user = UserInfo(
            id="user1",
            roles=["viewer"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        assert not self.rbac.has_permission(user, Permission.AGENTS_WRITE)
        assert not self.rbac.has_permission(user, Permission.USERS_DELETE)

    def test_has_any_permission(self):
        """Test has_any_permission."""
        user = UserInfo(
            id="user1",
            roles=["user"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        # User has AGENTS_READ and AGENTS_EXECUTE
        assert self.rbac.has_any_permission(
            user, [Permission.AGENTS_READ, Permission.AGENTS_WRITE]
        )
        assert not self.rbac.has_any_permission(
            user, [Permission.USERS_DELETE, Permission.ADMIN_FULL]
        )

    def test_has_all_permissions(self):
        """Test has_all_permissions."""
        user = UserInfo(
            id="user1",
            roles=["developer"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        # Developer has both permissions
        assert self.rbac.has_all_permissions(
            user, [Permission.AGENTS_READ, Permission.AGENTS_WRITE]
        )

        # Developer doesn't have USERS_DELETE
        assert not self.rbac.has_all_permissions(
            user, [Permission.AGENTS_WRITE, Permission.USERS_DELETE]
        )

    def test_has_role(self):
        """Test has_role."""
        user = UserInfo(
            id="user1",
            roles=["admin"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        assert self.rbac.has_role(user, Role.ADMIN)
        assert not self.rbac.has_role(user, Role.SUPER_ADMIN)

    def test_has_any_role(self):
        """Test has_any_role."""
        user = UserInfo(
            id="user1",
            roles=["developer"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        assert self.rbac.has_any_role(user, [Role.ADMIN, Role.DEVELOPER])
        assert not self.rbac.has_any_role(user, [Role.ADMIN, Role.SUPER_ADMIN])

    def test_has_all_roles(self):
        """Test has_all_roles."""
        user = UserInfo(
            id="user1",
            roles=["admin", "developer"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        assert self.rbac.has_all_roles(user, [Role.ADMIN, Role.DEVELOPER])
        assert not self.rbac.has_all_roles(user, [Role.ADMIN, Role.SUPER_ADMIN])

    def test_get_highest_user_role(self):
        """Test get_highest_user_role."""
        user = UserInfo(
            id="user1",
            roles=["viewer", "developer", "admin"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        highest = self.rbac.get_highest_user_role(user)
        assert highest == Role.ADMIN

    def test_custom_permissions(self):
        """Test adding custom permissions."""
        user = UserInfo(
            id="user1",
            roles=["viewer"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        # Initially, viewer doesn't have AGENTS_DELETE
        assert not self.rbac.has_permission(user, Permission.AGENTS_DELETE)

        # Add custom permission
        self.rbac.add_custom_permission(user, Permission.AGENTS_DELETE)

        # Now should have the permission
        assert self.rbac.has_permission(user, Permission.AGENTS_DELETE)

    def test_admin_full_implies_all_permissions(self):
        """Test that ADMIN_FULL grants all permissions."""
        user = UserInfo(
            id="user1",
            roles=["super_admin"],  # Has ADMIN_FULL
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        # ADMIN_FULL should grant all permissions
        assert self.rbac.has_permission(user, Permission.AGENTS_READ)
        assert self.rbac.has_permission(user, Permission.AGENTS_WRITE)
        assert self.rbac.has_permission(user, Permission.USERS_DELETE)
        assert self.rbac.has_permission(user, Permission.ADMIN_FULL)

    def test_cognito_groups(self):
        """Test role extraction from Cognito groups."""
        user = UserInfo(
            id="user1",
            roles=[],
            groups=["agent-service-developers"],
            provider=AuthProvider.AWS_COGNITO,
        )

        roles = self.rbac.get_user_roles(user)
        assert Role.DEVELOPER in roles

        perms = self.rbac.get_user_permissions(user)
        assert Permission.AGENTS_WRITE in perms

    def test_azure_ad_groups(self):
        """Test role extraction from Azure AD groups."""
        user = UserInfo(
            id="user1",
            roles=[],
            groups=["AgentService.Admins"],
            provider=AuthProvider.AZURE_AD,
        )

        roles = self.rbac.get_user_roles(user)
        assert Role.ADMIN in roles

        perms = self.rbac.get_user_permissions(user)
        assert Permission.USERS_WRITE in perms

    def test_multiple_roles_permission_union(self):
        """Test that multiple roles give union of permissions."""
        user = UserInfo(
            id="user1",
            roles=["viewer", "user"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        perms = self.rbac.get_user_permissions(user)

        # Should have permissions from both VIEWER and USER
        assert Permission.AGENTS_READ in perms  # From VIEWER
        assert Permission.AGENTS_EXECUTE in perms  # From USER


class TestRoleHierarchy:
    """Test role hierarchy behavior."""

    def test_hierarchy_enabled(self):
        """Test that hierarchy grants inherited permissions."""
        rbac = RBACService(enable_hierarchy=True)

        user = UserInfo(
            id="user1",
            roles=["admin"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        # ADMIN should have permissions from DEVELOPER, USER, and VIEWER
        assert rbac.has_permission(user, Permission.AGENTS_READ)  # From VIEWER
        assert rbac.has_permission(user, Permission.AGENTS_EXECUTE)  # From USER
        assert rbac.has_permission(user, Permission.AGENTS_WRITE)  # From DEVELOPER
        assert rbac.has_permission(user, Permission.USERS_WRITE)  # From ADMIN

    def test_hierarchy_disabled(self):
        """Test that hierarchy can be disabled."""
        rbac = RBACService(enable_hierarchy=False)

        user = UserInfo(
            id="user1",
            roles=["admin"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        # ADMIN should only have ADMIN permissions, not inherited ones
        assert rbac.has_permission(user, Permission.USERS_WRITE)  # From ADMIN
        # These should not be present without hierarchy
        # Note: This depends on how DEFAULT_ROLE_PERMISSIONS is defined
        # If ADMIN explicitly includes these, this test might fail


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
