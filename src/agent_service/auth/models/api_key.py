"""
SQLAlchemy model for API key storage and management.

This module defines the database schema for API keys with support for:
- Secure hashed key storage (never stores raw keys)
- User association and ownership
- Scopes and permissions
- Rate limiting tiers
- Expiration and soft deletion
- Usage tracking
"""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from sqlalchemy import Column, String, JSON, Index, ForeignKey
from sqlmodel import Field, Relationship

from agent_service.infrastructure.database.base_model import BaseModel, SoftDeleteMixin


class RateLimitTier(str):
    """
    Rate limit tiers for API key usage.

    Defines the allowed values for rate limiting tiers.
    """
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class APIKey(BaseModel, SoftDeleteMixin, table=True):
    """
    API Key model for secure authentication.

    Stores hashed API keys with associated metadata, permissions, and usage tracking.
    Raw keys are NEVER stored - only SHA256 hashes are persisted.

    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to the user who owns this key
        name: Human-friendly name for the key (e.g., "Production API", "Development")
        key_hash: SHA256 hash of the raw API key (NEVER store raw key)
        key_prefix: First 8 characters of the key for identification (e.g., "sk_live_")
        scopes: JSON array of permission scopes (e.g., ["read", "write", "admin"])
        rate_limit_tier: Tier for rate limiting (free, pro, enterprise)
        expires_at: Optional expiration timestamp
        last_used_at: Timestamp of last successful authentication
        created_at: Timestamp when key was created
        updated_at: Timestamp when key was last modified
        deleted_at: Timestamp when key was soft deleted (None if active)

    Indexes:
        - key_hash: Fast lookup during authentication
        - user_id: Fast retrieval of user's keys
        - key_prefix: Quick identification of key type

    Security:
        - Raw keys are NEVER stored or logged
        - Only hashed versions are persisted
        - Soft delete prevents accidental key exposure
        - Scopes provide fine-grained access control
    """

    __tablename__ = "api_keys"

    # User relationship
    user_id: UUID = Field(
        nullable=False,
        index=True,
        description="UUID of the user who owns this API key"
    )

    # Key identification
    name: str = Field(
        nullable=False,
        max_length=255,
        description="Human-friendly name for the key"
    )

    # Key storage (NEVER store raw key, only hash)
    key_hash: str = Field(
        nullable=False,
        unique=True,
        index=True,
        max_length=64,  # SHA256 produces 64 hex characters
        sa_column_kwargs={"comment": "SHA256 hash of the API key - NEVER store raw key"},
        description="SHA256 hash of the raw API key"
    )

    key_prefix: str = Field(
        nullable=False,
        max_length=12,
        index=True,
        description="First 8-12 characters of the key for identification (e.g., 'sk_live')"
    )

    # Permissions and access control
    scopes: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="JSON array of permission scopes"
    )

    # Rate limiting
    rate_limit_tier: str = Field(
        default=RateLimitTier.FREE,
        max_length=20,
        description="Rate limit tier (free, pro, enterprise)"
    )

    # Expiration
    expires_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        index=True,
        description="Optional expiration timestamp (None = never expires)"
    )

    # Usage tracking
    last_used_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        description="Timestamp of last successful authentication"
    )

    # Indexes for performance
    __table_args__ = (
        Index('ix_api_keys_user_id_deleted_at', 'user_id', 'deleted_at'),
        Index('ix_api_keys_key_hash_deleted_at', 'key_hash', 'deleted_at'),
        Index('ix_api_keys_expires_at', 'expires_at'),
    )

    @property
    def is_active(self) -> bool:
        """
        Check if the API key is currently active.

        A key is active if:
        1. It has not been soft deleted (deleted_at is None)
        2. It has not expired (expires_at is None or in the future)

        Returns:
            True if the key is active, False otherwise

        Example:
            >>> key = APIKey(deleted_at=None, expires_at=None)
            >>> key.is_active
            True
            >>> key.deleted_at = datetime.utcnow()
            >>> key.is_active
            False
        """
        # Check if soft deleted
        if self.is_deleted:
            return False

        # Check if expired
        if self.expires_at is not None and self.expires_at <= datetime.utcnow():
            return False

        return True

    @property
    def is_expired(self) -> bool:
        """
        Check if the API key has expired.

        Returns:
            True if the key has an expiration date and it has passed, False otherwise

        Example:
            >>> key = APIKey(expires_at=datetime.utcnow() - timedelta(days=1))
            >>> key.is_expired
            True
        """
        if self.expires_at is None:
            return False
        return self.expires_at <= datetime.utcnow()

    @property
    def expires_in_days(self) -> Optional[int]:
        """
        Get the number of days until the key expires.

        Returns:
            Number of days until expiration (negative if already expired),
            or None if the key never expires

        Example:
            >>> key = APIKey(expires_at=datetime.utcnow() + timedelta(days=7))
            >>> key.expires_in_days
            7
        """
        if self.expires_at is None:
            return None
        delta = self.expires_at - datetime.utcnow()
        return delta.days

    def has_scope(self, scope: str) -> bool:
        """
        Check if the API key has a specific scope.

        Args:
            scope: The scope to check for (e.g., "read", "write", "admin")

        Returns:
            True if the key has the scope, False otherwise

        Example:
            >>> key = APIKey(scopes=["read", "write"])
            >>> key.has_scope("read")
            True
            >>> key.has_scope("admin")
            False
        """
        return scope in (self.scopes or [])

    def has_any_scope(self, scopes: List[str]) -> bool:
        """
        Check if the API key has any of the specified scopes.

        Args:
            scopes: List of scopes to check

        Returns:
            True if the key has at least one of the scopes, False otherwise

        Example:
            >>> key = APIKey(scopes=["read"])
            >>> key.has_any_scope(["read", "write"])
            True
        """
        key_scopes = self.scopes or []
        return any(scope in key_scopes for scope in scopes)

    def has_all_scopes(self, scopes: List[str]) -> bool:
        """
        Check if the API key has all of the specified scopes.

        Args:
            scopes: List of scopes to check

        Returns:
            True if the key has all of the scopes, False otherwise

        Example:
            >>> key = APIKey(scopes=["read", "write"])
            >>> key.has_all_scopes(["read", "write"])
            True
            >>> key.has_all_scopes(["read", "write", "admin"])
            False
        """
        key_scopes = self.scopes or []
        return all(scope in key_scopes for scope in scopes)

    def update_last_used(self) -> None:
        """
        Update the last_used_at timestamp to the current time.

        This should be called after successful authentication.

        Example:
            >>> key = APIKey()
            >>> key.update_last_used()
            >>> assert key.last_used_at is not None
        """
        self.last_used_at = datetime.utcnow()

    def soft_delete(self) -> None:
        """
        Soft delete the API key by setting deleted_at timestamp.

        The key remains in the database but is marked as deleted.

        Example:
            >>> key = APIKey()
            >>> key.soft_delete()
            >>> assert key.is_deleted
            >>> assert not key.is_active
        """
        self.deleted_at = datetime.utcnow()

    def __repr__(self) -> str:
        """String representation of the API key (NEVER includes raw key)."""
        return (
            f"APIKey(id={self.id}, "
            f"user_id={self.user_id}, "
            f"name={self.name!r}, "
            f"prefix={self.key_prefix!r}, "
            f"active={self.is_active})"
        )
