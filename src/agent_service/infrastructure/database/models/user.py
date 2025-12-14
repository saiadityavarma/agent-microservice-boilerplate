"""
SQLAlchemy model for user management.

This module defines the database schema for users with support for:
- Multiple authentication providers (Azure AD, AWS Cognito, local)
- Role-based access control (RBAC)
- Group membership
- Soft deletion
- OAuth user mapping
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from sqlalchemy import Column, String, JSON, Index, Boolean
from sqlmodel import Field

from agent_service.infrastructure.database.base_model import BaseModel, SoftDeleteMixin


class AuthProvider(str):
    """
    Authentication provider types.

    Defines the supported authentication providers for user accounts.
    """
    AZURE_AD = "azure_ad"
    AWS_COGNITO = "aws_cognito"
    LOCAL = "local"


class User(BaseModel, SoftDeleteMixin, table=True):
    """
    User model for authentication and authorization.

    Supports multiple authentication providers and includes role-based
    access control (RBAC) and group membership.

    Attributes:
        id: Unique identifier (UUID)
        email: User email address (unique, required)
        name: Full name of the user
        hashed_password: Hashed password (optional for OAuth users)
        provider: Authentication provider (azure_ad, aws_cognito, local)
        provider_user_id: User ID from the authentication provider
        roles: JSON array of user roles (e.g., ["admin", "user"])
        groups: JSON array of user groups (e.g., ["engineering", "management"])
        is_active: Whether the user account is active
        created_at: Timestamp when user was created
        updated_at: Timestamp when user was last modified
        deleted_at: Timestamp when user was soft deleted (None if active)

    Indexes:
        - email: Fast lookup by email (unique)
        - provider + provider_user_id: Fast lookup by provider credentials
        - is_active: Fast filtering of active users

    Security:
        - Passwords are always hashed (never store plaintext)
        - OAuth users may not have passwords
        - Soft delete prevents accidental data loss
        - Email is unique across all providers

    Example:
        >>> # Azure AD user
        >>> user = User(
        ...     email="john@example.com",
        ...     name="John Doe",
        ...     provider=AuthProvider.AZURE_AD,
        ...     provider_user_id="azure-123",
        ...     roles=["user"],
        ...     groups=["engineering"],
        ...     is_active=True
        ... )
        >>>
        >>> # Local user with password
        >>> user = User(
        ...     email="jane@example.com",
        ...     name="Jane Smith",
        ...     hashed_password="$2b$12$...",
        ...     provider=AuthProvider.LOCAL,
        ...     provider_user_id="jane@example.com",
        ...     roles=["admin"],
        ...     is_active=True
        ... )
    """

    __tablename__ = "users"

    # User identification
    email: str = Field(
        nullable=False,
        unique=True,
        index=True,
        max_length=255,
        description="User email address (unique)",
        sa_column_kwargs={"comment": "User email address - unique across all providers"}
    )

    name: str = Field(
        nullable=False,
        max_length=255,
        description="Full name of the user",
        sa_column_kwargs={"comment": "User's full name"}
    )

    # Authentication
    hashed_password: Optional[str] = Field(
        default=None,
        nullable=True,
        max_length=255,
        description="Hashed password (optional for OAuth users)",
        sa_column_kwargs={"comment": "Hashed password - null for OAuth users"}
    )

    provider: str = Field(
        nullable=False,
        max_length=50,
        index=True,
        description="Authentication provider (azure_ad, aws_cognito, local)",
        sa_column_kwargs={"comment": "Authentication provider: azure_ad, aws_cognito, local"}
    )

    provider_user_id: str = Field(
        nullable=False,
        max_length=255,
        index=True,
        description="User ID from the authentication provider",
        sa_column_kwargs={"comment": "User ID from the authentication provider"}
    )

    # Authorization
    roles: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="JSON array of user roles (e.g., ['admin', 'user'])",
        sa_column_kwargs={"comment": "User roles for RBAC"}
    )

    groups: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="JSON array of user groups (e.g., ['engineering', 'management'])",
        sa_column_kwargs={"comment": "User groups for organization"}
    )

    # Status
    is_active: bool = Field(
        default=True,
        nullable=False,
        index=True,
        sa_column=Column(Boolean, default=True),
        description="Whether the user account is active",
        sa_column_kwargs={"comment": "User account active status"}
    )

    # Indexes for performance
    __table_args__ = (
        Index('ix_users_provider_provider_user_id', 'provider', 'provider_user_id'),
        Index('ix_users_email_deleted_at', 'email', 'deleted_at'),
        Index('ix_users_is_active_deleted_at', 'is_active', 'deleted_at'),
    )

    @property
    def is_oauth_user(self) -> bool:
        """
        Check if the user is an OAuth user (no password).

        Returns:
            True if user authenticates via OAuth, False if local user

        Example:
            >>> user = User(provider=AuthProvider.AZURE_AD)
            >>> user.is_oauth_user
            True
            >>> local_user = User(provider=AuthProvider.LOCAL)
            >>> local_user.is_oauth_user
            False
        """
        return self.provider in [AuthProvider.AZURE_AD, AuthProvider.AWS_COGNITO]

    def has_role(self, role: str) -> bool:
        """
        Check if the user has a specific role.

        Args:
            role: The role to check for (e.g., "admin", "user")

        Returns:
            True if the user has the role, False otherwise

        Example:
            >>> user = User(roles=["admin", "user"])
            >>> user.has_role("admin")
            True
            >>> user.has_role("guest")
            False
        """
        return role in (self.roles or [])

    def has_any_role(self, roles: List[str]) -> bool:
        """
        Check if the user has any of the specified roles.

        Args:
            roles: List of roles to check

        Returns:
            True if the user has at least one of the roles, False otherwise

        Example:
            >>> user = User(roles=["user"])
            >>> user.has_any_role(["admin", "user"])
            True
        """
        user_roles = self.roles or []
        return any(role in user_roles for role in roles)

    def has_all_roles(self, roles: List[str]) -> bool:
        """
        Check if the user has all of the specified roles.

        Args:
            roles: List of roles to check

        Returns:
            True if the user has all of the roles, False otherwise

        Example:
            >>> user = User(roles=["admin", "user"])
            >>> user.has_all_roles(["admin", "user"])
            True
            >>> user.has_all_roles(["admin", "user", "guest"])
            False
        """
        user_roles = self.roles or []
        return all(role in user_roles for role in roles)

    def is_in_group(self, group: str) -> bool:
        """
        Check if the user is in a specific group.

        Args:
            group: The group to check for

        Returns:
            True if the user is in the group, False otherwise

        Example:
            >>> user = User(groups=["engineering", "management"])
            >>> user.is_in_group("engineering")
            True
        """
        return group in (self.groups or [])

    def is_in_any_group(self, groups: List[str]) -> bool:
        """
        Check if the user is in any of the specified groups.

        Args:
            groups: List of groups to check

        Returns:
            True if the user is in at least one of the groups, False otherwise

        Example:
            >>> user = User(groups=["engineering"])
            >>> user.is_in_any_group(["engineering", "sales"])
            True
        """
        user_groups = self.groups or []
        return any(group in user_groups for group in groups)

    def activate(self) -> None:
        """
        Activate the user account.

        Example:
            >>> user = User(is_active=False)
            >>> user.activate()
            >>> assert user.is_active
        """
        self.is_active = True

    def deactivate(self) -> None:
        """
        Deactivate the user account.

        Example:
            >>> user = User(is_active=True)
            >>> user.deactivate()
            >>> assert not user.is_active
        """
        self.is_active = False

    def add_role(self, role: str) -> None:
        """
        Add a role to the user.

        Args:
            role: The role to add

        Example:
            >>> user = User(roles=["user"])
            >>> user.add_role("admin")
            >>> assert "admin" in user.roles
        """
        if self.roles is None:
            self.roles = []
        if role not in self.roles:
            self.roles.append(role)

    def remove_role(self, role: str) -> None:
        """
        Remove a role from the user.

        Args:
            role: The role to remove

        Example:
            >>> user = User(roles=["admin", "user"])
            >>> user.remove_role("admin")
            >>> assert "admin" not in user.roles
        """
        if self.roles and role in self.roles:
            self.roles.remove(role)

    def add_group(self, group: str) -> None:
        """
        Add a group to the user.

        Args:
            group: The group to add

        Example:
            >>> user = User(groups=["engineering"])
            >>> user.add_group("management")
            >>> assert "management" in user.groups
        """
        if self.groups is None:
            self.groups = []
        if group not in self.groups:
            self.groups.append(group)

    def remove_group(self, group: str) -> None:
        """
        Remove a group from the user.

        Args:
            group: The group to remove

        Example:
            >>> user = User(groups=["engineering", "management"])
            >>> user.remove_group("management")
            >>> assert "management" not in user.groups
        """
        if self.groups and group in self.groups:
            self.groups.remove(group)

    def __repr__(self) -> str:
        """String representation of the user (never includes password)."""
        return (
            f"User(id={self.id}, "
            f"email={self.email!r}, "
            f"name={self.name!r}, "
            f"provider={self.provider!r}, "
            f"is_active={self.is_active})"
        )
