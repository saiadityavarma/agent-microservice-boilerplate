"""
Unit tests for RBAC (Role-Based Access Control) functionality.

Tests cover:
- Role-permission mappings
- Role hierarchy
- Permission checking logic
- Group-to-role mapping for Azure AD
- Group-to-role mapping for Cognito
"""

import pytest
from agent_service.auth.rbac.rbac import RBACService
from agent_service.auth.rbac.roles import (
    Role,
    get_permissions_for_role,
    get_roles_from_groups,
    get_roles_from_strings,
    get_highest_role,
    role_hierarchy_includes,
    DEFAULT_GROUP_TO_ROLE,
)
from agent_service.auth.rbac.permissions import Permission
from agent_service.auth.schemas import UserInfo, AuthProvider


@pytest.fixture
def rbac_service():
    """Create RBAC service for testing."""
    return RBACService(enable_hierarchy=True, enable_custom_permissions=True)


@pytest.fixture
def rbac_service_no_hierarchy():
    """Create RBAC service without hierarchy."""
    return RBACService(enable_hierarchy=False, enable_custom_permissions=True)


@pytest.fixture
def sample_viewer_user():
    """Create a sample viewer user."""
    return UserInfo(
        id="user-viewer-123",
        email="viewer@example.com",
        name="Viewer User",
        roles=["viewer"],
        groups=[],
        provider=AuthProvider.AZURE_AD,
    )


@pytest.fixture
def sample_user_user():
    """Create a sample regular user."""
    return UserInfo(
        id="user-regular-456",
        email="user@example.com",
        name="Regular User",
        roles=["user"],
        groups=[],
        provider=AuthProvider.AZURE_AD,
    )


@pytest.fixture
def sample_admin_user():
    """Create a sample admin user."""
    return UserInfo(
        id="user-admin-789",
        email="admin@example.com",
        name="Admin User",
        roles=["admin"],
        groups=[],
        provider=AuthProvider.AZURE_AD,
    )


@pytest.fixture
def sample_super_admin_user():
    """Create a sample super admin user."""
    return UserInfo(
        id="user-superadmin-999",
        email="superadmin@example.com",
        name="Super Admin",
        roles=["super_admin"],
        groups=[],
        provider=AuthProvider.AZURE_AD,
    )


class TestRolePermissionMappings:
    """Test role-to-permission mappings."""

    def test_viewer_has_read_only_permissions(self):
        """Test that viewer role has read-only permissions."""
        permissions = get_permissions_for_role(Role.VIEWER, include_hierarchy=False)

        # Should have read permissions
        assert Permission.AGENTS_READ in permissions
        assert Permission.TOOLS_READ in permissions
        assert Permission.USERS_READ in permissions

        # Should NOT have write/delete permissions
        assert Permission.AGENTS_WRITE not in permissions
        assert Permission.AGENTS_DELETE not in permissions
        assert Permission.TOOLS_WRITE not in permissions
        assert Permission.USERS_WRITE not in permissions

    def test_user_has_execute_permissions(self):
        """Test that user role has execute permissions."""
        permissions = get_permissions_for_role(Role.USER, include_hierarchy=False)

        # Should have execute permissions
        assert Permission.AGENTS_EXECUTE in permissions
        assert Permission.TOOLS_EXECUTE in permissions

        # Should have read permissions
        assert Permission.AGENTS_READ in permissions
        assert Permission.TOOLS_READ in permissions

    def test_developer_has_write_permissions(self):
        """Test that developer role has write permissions."""
        permissions = get_permissions_for_role(Role.DEVELOPER, include_hierarchy=False)

        # Should have write and delete permissions for agents/tools
        assert Permission.AGENTS_WRITE in permissions
        assert Permission.AGENTS_DELETE in permissions
        assert Permission.TOOLS_WRITE in permissions
        assert Permission.TOOLS_DELETE in permissions

        # Should have API key management
        assert Permission.API_KEYS_WRITE in permissions
        assert Permission.API_KEYS_DELETE in permissions

    def test_admin_has_user_management(self):
        """Test that admin role has user management permissions."""
        permissions = get_permissions_for_role(Role.ADMIN, include_hierarchy=False)

        # Should have user management permissions
        assert Permission.USERS_WRITE in permissions
        assert Permission.USERS_DELETE in permissions

        # Should NOT have ADMIN_FULL
        assert Permission.ADMIN_FULL not in permissions

    def test_super_admin_has_all_permissions(self):
        """Test that super admin has all permissions including ADMIN_FULL."""
        permissions = get_permissions_for_role(Role.SUPER_ADMIN, include_hierarchy=False)

        # Should have ADMIN_FULL
        assert Permission.ADMIN_FULL in permissions

        # Should have all other permissions
        assert Permission.USERS_WRITE in permissions
        assert Permission.USERS_DELETE in permissions
        assert Permission.AGENTS_WRITE in permissions


class TestRoleHierarchy:
    """Test role hierarchy functionality."""

    def test_user_inherits_from_viewer(self):
        """Test that USER role inherits VIEWER permissions."""
        viewer_perms = get_permissions_for_role(Role.VIEWER, include_hierarchy=False)
        user_perms = get_permissions_for_role(Role.USER, include_hierarchy=True)

        # USER should have all VIEWER permissions
        assert viewer_perms.issubset(user_perms)

    def test_developer_inherits_from_user(self):
        """Test that DEVELOPER role inherits USER permissions."""
        user_perms = get_permissions_for_role(Role.USER, include_hierarchy=True)
        dev_perms = get_permissions_for_role(Role.DEVELOPER, include_hierarchy=True)

        # DEVELOPER should have all USER permissions
        assert user_perms.issubset(dev_perms)

    def test_admin_inherits_from_developer(self):
        """Test that ADMIN role inherits DEVELOPER permissions."""
        dev_perms = get_permissions_for_role(Role.DEVELOPER, include_hierarchy=True)
        admin_perms = get_permissions_for_role(Role.ADMIN, include_hierarchy=True)

        # ADMIN should have all DEVELOPER permissions
        assert dev_perms.issubset(admin_perms)

    def test_super_admin_inherits_from_admin(self):
        """Test that SUPER_ADMIN inherits ADMIN permissions."""
        admin_perms = get_permissions_for_role(Role.ADMIN, include_hierarchy=True)
        super_admin_perms = get_permissions_for_role(Role.SUPER_ADMIN, include_hierarchy=True)

        # SUPER_ADMIN should have all ADMIN permissions
        assert admin_perms.issubset(super_admin_perms)

    def test_hierarchy_includes_check(self):
        """Test role hierarchy inclusion checks."""
        # ADMIN includes USER
        assert role_hierarchy_includes(Role.ADMIN, Role.USER) is True

        # USER does not include ADMIN
        assert role_hierarchy_includes(Role.USER, Role.ADMIN) is False

        # Same role includes itself
        assert role_hierarchy_includes(Role.DEVELOPER, Role.DEVELOPER) is True

    def test_get_highest_role(self):
        """Test getting the highest role from a set."""
        roles = {Role.USER, Role.ADMIN, Role.VIEWER}
        assert get_highest_role(roles) == Role.ADMIN

        roles = {Role.VIEWER, Role.USER}
        assert get_highest_role(roles) == Role.USER

        assert get_highest_role(set()) is None


class TestPermissionChecking:
    """Test permission checking logic."""

    def test_has_permission_direct(self, rbac_service, sample_admin_user):
        """Test direct permission checking."""
        # Admin has user write permission
        assert rbac_service.has_permission(sample_admin_user, Permission.USERS_WRITE) is True

        # Admin does not have ADMIN_FULL (only super admin does)
        assert rbac_service.has_permission(sample_admin_user, Permission.ADMIN_FULL) is False

    def test_has_permission_through_hierarchy(self, rbac_service, sample_admin_user):
        """Test permission checking through role hierarchy."""
        # Admin should have AGENTS_READ through hierarchy (from VIEWER)
        assert rbac_service.has_permission(sample_admin_user, Permission.AGENTS_READ) is True

        # Admin should have AGENTS_EXECUTE through hierarchy (from USER)
        assert rbac_service.has_permission(sample_admin_user, Permission.AGENTS_EXECUTE) is True

    def test_has_permission_without_hierarchy(self, rbac_service_no_hierarchy, sample_user_user):
        """Test permission checking without hierarchy enabled."""
        # Without hierarchy, USER should have their direct permissions
        assert rbac_service_no_hierarchy.has_permission(
            sample_user_user, Permission.AGENTS_EXECUTE
        ) is True

        # But may not have VIEWER permissions if not explicitly granted
        permissions = rbac_service_no_hierarchy.get_user_permissions(sample_user_user)
        viewer_only_perms = get_permissions_for_role(Role.VIEWER, include_hierarchy=False)

        # If USER role doesn't directly grant AGENTS_READ, it won't have it without hierarchy
        # (depends on role definition)

    def test_has_any_permission(self, rbac_service, sample_user_user):
        """Test checking if user has any of multiple permissions."""
        # User should have at least one of these
        assert rbac_service.has_any_permission(
            sample_user_user,
            [Permission.AGENTS_READ, Permission.AGENTS_WRITE, Permission.ADMIN_FULL]
        ) is True

        # User should not have any of these admin permissions
        assert rbac_service.has_any_permission(
            sample_user_user,
            [Permission.ADMIN_FULL, Permission.USERS_DELETE]
        ) is False

    def test_has_all_permissions(self, rbac_service, sample_admin_user):
        """Test checking if user has all of multiple permissions."""
        # Admin should have all of these
        assert rbac_service.has_all_permissions(
            sample_admin_user,
            [Permission.AGENTS_READ, Permission.USERS_WRITE]
        ) is True

        # Admin should not have all of these (missing ADMIN_FULL)
        assert rbac_service.has_all_permissions(
            sample_admin_user,
            [Permission.AGENTS_READ, Permission.ADMIN_FULL]
        ) is False

    def test_viewer_cannot_write(self, rbac_service, sample_viewer_user):
        """Test that viewer cannot perform write operations."""
        write_permissions = [
            Permission.AGENTS_WRITE,
            Permission.TOOLS_WRITE,
            Permission.USERS_WRITE,
        ]

        for perm in write_permissions:
            assert rbac_service.has_permission(sample_viewer_user, perm) is False

    def test_super_admin_has_all_permissions(self, rbac_service, sample_super_admin_user):
        """Test that super admin has all permissions."""
        all_permissions = [
            Permission.AGENTS_READ,
            Permission.AGENTS_WRITE,
            Permission.AGENTS_DELETE,
            Permission.AGENTS_EXECUTE,
            Permission.TOOLS_READ,
            Permission.TOOLS_WRITE,
            Permission.USERS_WRITE,
            Permission.USERS_DELETE,
            Permission.ADMIN_FULL,
        ]

        for perm in all_permissions:
            assert rbac_service.has_permission(sample_super_admin_user, perm) is True


class TestAzureADGroupMapping:
    """Test Azure AD group-to-role mapping."""

    def test_azure_ad_group_naming_convention(self):
        """Test Azure AD group name mapping."""
        azure_groups = [
            "AgentService.Viewers",
            "AgentService.Users",
            "AgentService.Developers",
            "AgentService.Admins",
            "AgentService.SuperAdmins",
        ]

        roles = get_roles_from_groups(azure_groups)

        assert Role.VIEWER in roles
        assert Role.USER in roles
        assert Role.DEVELOPER in roles
        assert Role.ADMIN in roles
        assert Role.SUPER_ADMIN in roles

    def test_azure_ad_single_group(self):
        """Test mapping a single Azure AD group."""
        roles = get_roles_from_groups(["AgentService.Admins"])

        assert len(roles) == 1
        assert Role.ADMIN in roles

    def test_azure_ad_unknown_groups_ignored(self):
        """Test that unknown Azure AD groups are ignored."""
        roles = get_roles_from_groups([
            "AgentService.Admins",
            "SomeOtherService.Users",
            "RandomGroup",
        ])

        # Should only get the known group
        assert Role.ADMIN in roles
        assert len(roles) == 1

    def test_azure_ad_case_insensitive_matching(self):
        """Test case-insensitive group matching."""
        # Test with different cases
        roles1 = get_roles_from_groups(["agentservice.admins"])
        roles2 = get_roles_from_groups(["AGENTSERVICE.ADMINS"])

        assert Role.ADMIN in roles1
        assert Role.ADMIN in roles2


class TestCognitoGroupMapping:
    """Test AWS Cognito group-to-role mapping."""

    def test_cognito_group_naming_convention(self):
        """Test Cognito group name mapping."""
        cognito_groups = [
            "agent-service-viewers",
            "agent-service-users",
            "agent-service-developers",
            "agent-service-admins",
            "agent-service-super-admins",
        ]

        roles = get_roles_from_groups(cognito_groups)

        assert Role.VIEWER in roles
        assert Role.USER in roles
        assert Role.DEVELOPER in roles
        assert Role.ADMIN in roles
        assert Role.SUPER_ADMIN in roles

    def test_cognito_single_group(self):
        """Test mapping a single Cognito group."""
        roles = get_roles_from_groups(["agent-service-developers"])

        assert len(roles) == 1
        assert Role.DEVELOPER in roles

    def test_cognito_unknown_groups_ignored(self):
        """Test that unknown Cognito groups are ignored."""
        roles = get_roles_from_groups([
            "agent-service-users",
            "other-service-admins",
            "random-group",
        ])

        assert Role.USER in roles
        assert len(roles) == 1


class TestGenericRoleMapping:
    """Test generic role string mapping."""

    def test_generic_role_names(self):
        """Test mapping of generic role names."""
        generic_groups = ["viewer", "user", "developer", "admin", "super_admin"]

        roles = get_roles_from_groups(generic_groups)

        assert len(roles) == 5
        assert Role.VIEWER in roles
        assert Role.USER in roles
        assert Role.DEVELOPER in roles
        assert Role.ADMIN in roles
        assert Role.SUPER_ADMIN in roles

    def test_role_string_conversion(self):
        """Test converting role strings to Role enums."""
        role_strings = ["admin", "user", "viewer"]
        roles = get_roles_from_strings(role_strings)

        assert Role.ADMIN in roles
        assert Role.USER in roles
        assert Role.VIEWER in roles

    def test_role_string_case_insensitive(self):
        """Test case-insensitive role string conversion."""
        roles = get_roles_from_strings(["ADMIN", "User", "vIeWeR"])

        assert Role.ADMIN in roles
        assert Role.USER in roles
        assert Role.VIEWER in roles

    def test_invalid_role_strings_ignored(self):
        """Test that invalid role strings are ignored."""
        roles = get_roles_from_strings(["admin", "invalid_role", "user", "bad_role"])

        assert Role.ADMIN in roles
        assert Role.USER in roles
        assert len(roles) == 2


class TestRBACServiceWithGroups:
    """Test RBAC service with group-based roles."""

    def test_user_with_azure_ad_groups(self, rbac_service):
        """Test user permissions derived from Azure AD groups."""
        user = UserInfo(
            id="user-123",
            email="dev@company.com",
            name="Developer",
            roles=[],
            groups=["AgentService.Developers", "AgentService.Users"],
            provider=AuthProvider.AZURE_AD,
        )

        # Should get DEVELOPER and USER roles from groups
        user_roles = rbac_service.get_user_roles(user)
        assert Role.DEVELOPER in user_roles
        assert Role.USER in user_roles

        # Should have developer permissions
        assert rbac_service.has_permission(user, Permission.AGENTS_WRITE) is True

    def test_user_with_cognito_groups(self, rbac_service):
        """Test user permissions derived from Cognito groups."""
        user = UserInfo(
            id="user-456",
            email="admin@company.com",
            name="Admin",
            roles=[],
            groups=["agent-service-admins"],
            provider=AuthProvider.AWS_COGNITO,
        )

        user_roles = rbac_service.get_user_roles(user)
        assert Role.ADMIN in user_roles

        # Should have admin permissions
        assert rbac_service.has_permission(user, Permission.USERS_WRITE) is True

    def test_user_with_both_roles_and_groups(self, rbac_service):
        """Test user with both direct roles and group-derived roles."""
        user = UserInfo(
            id="user-789",
            email="mixed@company.com",
            name="Mixed User",
            roles=["user"],
            groups=["AgentService.Developers"],
            provider=AuthProvider.AZURE_AD,
        )

        user_roles = rbac_service.get_user_roles(user)

        # Should have both USER (from roles) and DEVELOPER (from groups)
        assert Role.USER in user_roles
        assert Role.DEVELOPER in user_roles

        # Should have permissions from both roles
        assert rbac_service.has_permission(user, Permission.AGENTS_EXECUTE) is True
        assert rbac_service.has_permission(user, Permission.AGENTS_WRITE) is True


class TestCustomPermissions:
    """Test custom per-user permissions."""

    def test_add_custom_permission(self, rbac_service, sample_viewer_user):
        """Test adding custom permissions to a user."""
        # Viewer normally can't write
        assert rbac_service.has_permission(sample_viewer_user, Permission.AGENTS_WRITE) is False

        # Add custom permission
        rbac_service.add_custom_permission(sample_viewer_user, Permission.AGENTS_WRITE)

        # Now should have the permission
        assert rbac_service.has_permission(sample_viewer_user, Permission.AGENTS_WRITE) is True

    def test_remove_custom_permission(self, rbac_service, sample_viewer_user):
        """Test removing custom permissions."""
        # Add custom permission
        rbac_service.add_custom_permission(sample_viewer_user, Permission.AGENTS_WRITE)
        assert rbac_service.has_permission(sample_viewer_user, Permission.AGENTS_WRITE) is True

        # Remove it
        rbac_service.remove_custom_permission(sample_viewer_user, Permission.AGENTS_WRITE)
        assert rbac_service.has_permission(sample_viewer_user, Permission.AGENTS_WRITE) is False

    def test_custom_permissions_in_user_metadata(self, rbac_service):
        """Test that custom permissions are stored in user metadata."""
        user = UserInfo(
            id="user-custom-123",
            email="custom@example.com",
            name="Custom User",
            roles=["viewer"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
            metadata={"permissions": ["agents:write", "tools:delete"]},
        )

        # Should have custom permissions
        assert rbac_service.has_permission(user, Permission.AGENTS_WRITE) is True
        assert rbac_service.has_permission(user, Permission.TOOLS_DELETE) is True

    def test_custom_permissions_disabled(self):
        """Test RBAC service with custom permissions disabled."""
        rbac = RBACService(enable_custom_permissions=False)

        user = UserInfo(
            id="user-no-custom-123",
            email="nocustom@example.com",
            name="No Custom User",
            roles=["viewer"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        # Try to add custom permission (should be ignored)
        rbac.add_custom_permission(user, Permission.AGENTS_WRITE)

        # Should not have the permission
        assert rbac.has_permission(user, Permission.AGENTS_WRITE) is False


class TestRoleChecking:
    """Test role checking functionality."""

    def test_has_role(self, rbac_service, sample_admin_user):
        """Test checking if user has a specific role."""
        assert rbac_service.has_role(sample_admin_user, Role.ADMIN) is True
        assert rbac_service.has_role(sample_admin_user, Role.VIEWER) is False

    def test_has_any_role(self, rbac_service, sample_user_user):
        """Test checking if user has any of multiple roles."""
        assert rbac_service.has_any_role(
            sample_user_user,
            [Role.ADMIN, Role.USER]
        ) is True

        assert rbac_service.has_any_role(
            sample_user_user,
            [Role.ADMIN, Role.SUPER_ADMIN]
        ) is False

    def test_has_all_roles(self, rbac_service):
        """Test checking if user has all of multiple roles."""
        user = UserInfo(
            id="multi-role-123",
            email="multi@example.com",
            name="Multi Role User",
            roles=["admin", "developer"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        assert rbac_service.has_all_roles(user, [Role.ADMIN, Role.DEVELOPER]) is True
        assert rbac_service.has_all_roles(user, [Role.ADMIN, Role.SUPER_ADMIN]) is False

    def test_get_highest_user_role(self, rbac_service):
        """Test getting the highest role a user has."""
        user = UserInfo(
            id="multi-role-456",
            email="highest@example.com",
            name="Highest Role User",
            roles=["user", "developer", "admin"],
            groups=[],
            provider=AuthProvider.AZURE_AD,
        )

        highest = rbac_service.get_highest_user_role(user)
        assert highest == Role.ADMIN
