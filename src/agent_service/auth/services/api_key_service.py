"""
Business logic service for API key management.

This module provides high-level operations for API key lifecycle management:
- Creating new API keys with secure generation
- Validating API keys during authentication
- Revoking and rotating keys
- Managing key metadata and permissions

SECURITY CRITICAL:
- Raw keys are NEVER logged or stored
- Only hashed versions are persisted to the database
- All database operations use async/await for performance
"""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from agent_service.auth.api_key import (
    generate_api_key,
    hash_api_key,
    verify_api_key,
    parse_api_key,
    validate_api_key_format,
)
from agent_service.auth.models.api_key import APIKey
from agent_service.auth.schemas.api_key import (
    APIKeyCreate,
    APIKeyResponse,
    APIKeyInfo,
    APIKeyValidation,
)
from agent_service.auth.exceptions import (
    AuthenticationError,
    AuthorizationError,
)


class APIKeyService:
    """
    Service for managing API key lifecycle and operations.

    Provides high-level business logic for:
    - Creating new API keys with secure generation
    - Validating keys during authentication
    - Revoking and rotating keys
    - Listing and managing user keys

    Security:
        - Raw keys are NEVER stored or logged
        - Only hashed versions are persisted
        - Soft delete prevents accidental key exposure
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the API key service.

        Args:
            session: Async SQLAlchemy session for database operations
        """
        self.session = session

    async def create_api_key(
        self,
        user_id: UUID,
        name: str,
        scopes: Optional[List[str]] = None,
        expires_in_days: Optional[int] = None,
        rate_limit_tier: str = "free",
        prefix: str = "sk",
    ) -> APIKeyResponse:
        """
        Create a new API key for a user.

        Generates a cryptographically secure API key, stores only the hash,
        and returns the raw key ONCE to be shown to the user.

        Args:
            user_id: UUID of the user who will own the key
            name: Human-friendly name for the key
            scopes: List of permission scopes (default: empty list)
            expires_in_days: Number of days until expiration (None = never expires)
            rate_limit_tier: Rate limit tier (free, pro, enterprise)
            prefix: Key prefix (default: "sk")

        Returns:
            APIKeyResponse containing the raw key (shown ONCE) and metadata

        Raises:
            ValueError: If parameters are invalid

        Example:
            >>> service = APIKeyService(session)
            >>> response = await service.create_api_key(
            ...     user_id=user_uuid,
            ...     name="Production API",
            ...     scopes=["read", "write"],
            ...     expires_in_days=365
            ... )
            >>> print(response.key)  # Show to user ONCE
            'sk_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6'

        Security:
            - Raw key is returned ONLY in this response
            - Only the hash is stored in the database
            - The raw key should be shown to the user immediately
        """
        # Generate the raw key and hash
        raw_key, key_hash = generate_api_key(prefix)

        # Parse the key to get the prefix for identification
        key_parts = parse_api_key(raw_key)

        # Calculate expiration if specified
        expires_at = None
        if expires_in_days is not None:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Create the database record (with hash only, NEVER raw key)
        api_key = APIKey(
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_parts.prefix[:12],  # Store first 8-12 chars for identification
            scopes=scopes or [],
            rate_limit_tier=rate_limit_tier,
            expires_at=expires_at,
        )

        self.session.add(api_key)
        await self.session.flush()
        await self.session.refresh(api_key)

        # Return response with raw key (shown ONCE)
        return APIKeyResponse(
            id=api_key.id,
            user_id=api_key.user_id,
            name=api_key.name,
            key=raw_key,  # RAW KEY - shown only once
            key_prefix=api_key.key_prefix,
            scopes=api_key.scopes,
            rate_limit_tier=api_key.rate_limit_tier,
            expires_at=api_key.expires_at,
            created_at=api_key.created_at,
        )

    async def validate_api_key(self, raw_key: str) -> Optional[APIKeyValidation]:
        """
        Validate an API key and return key information if valid.

        Checks:
        1. Key format is valid
        2. Key exists in database (by hash)
        3. Key is not soft deleted
        4. Key is not expired
        5. Key hash matches

        Args:
            raw_key: The raw API key to validate

        Returns:
            APIKeyValidation with key info if valid, None if invalid

        Example:
            >>> service = APIKeyService(session)
            >>> validation = await service.validate_api_key("sk_abc123...")
            >>> if validation:
            ...     print(f"Valid key for user {validation.user_id}")
            ... else:
            ...     print("Invalid key")

        Security:
            - Raw key is NEVER logged
            - Uses constant-time comparison for hash verification
            - Updates last_used_at on successful validation
        """
        # Validate format first (fast fail)
        if not validate_api_key_format(raw_key):
            return None

        # Hash the provided key
        key_hash = hash_api_key(raw_key)

        # Query for the key (not deleted, not expired)
        query = select(APIKey).where(
            and_(
                APIKey.key_hash == key_hash,
                APIKey.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(query)
        api_key = result.scalar_one_or_none()

        if not api_key:
            return None

        # Check if key is active (handles expiration check)
        if not api_key.is_active:
            return None

        # Verify the hash (constant-time comparison)
        if not verify_api_key(raw_key, api_key.key_hash):
            return None

        # Update last used timestamp
        api_key.update_last_used()
        await self.session.flush()

        # Return validation info (NO raw key)
        return APIKeyValidation(
            id=api_key.id,
            user_id=api_key.user_id,
            scopes=api_key.scopes,
            rate_limit_tier=api_key.rate_limit_tier,
            is_active=api_key.is_active,
        )

    async def revoke_api_key(self, key_id: UUID, user_id: UUID) -> bool:
        """
        Revoke (soft delete) an API key.

        The key remains in the database but is marked as deleted and
        can no longer be used for authentication.

        Args:
            key_id: UUID of the key to revoke
            user_id: UUID of the user (for ownership verification)

        Returns:
            True if key was revoked, False if not found or not owned by user

        Raises:
            AuthorizationError: If user doesn't own the key

        Example:
            >>> service = APIKeyService(session)
            >>> success = await service.revoke_api_key(key_uuid, user_uuid)
            >>> if success:
            ...     print("Key revoked successfully")
        """
        # Get the key
        query = select(APIKey).where(
            and_(
                APIKey.id == key_id,
                APIKey.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(query)
        api_key = result.scalar_one_or_none()

        if not api_key:
            return False

        # Verify ownership
        if api_key.user_id != user_id:
            raise AuthorizationError("You do not have permission to revoke this key")

        # Soft delete
        api_key.soft_delete()
        await self.session.flush()

        return True

    async def rotate_api_key(
        self,
        key_id: UUID,
        user_id: UUID,
    ) -> APIKeyResponse:
        """
        Rotate an API key by creating a new one and revoking the old one.

        The new key inherits all properties from the old key (name, scopes, etc.)
        but has a new cryptographic value.

        Args:
            key_id: UUID of the key to rotate
            user_id: UUID of the user (for ownership verification)

        Returns:
            APIKeyResponse with the new raw key (shown ONCE)

        Raises:
            AuthorizationError: If user doesn't own the key
            ValueError: If key not found

        Example:
            >>> service = APIKeyService(session)
            >>> new_key = await service.rotate_api_key(old_key_uuid, user_uuid)
            >>> print(f"New key: {new_key.key}")  # Show to user ONCE
        """
        # Get the existing key
        query = select(APIKey).where(
            and_(
                APIKey.id == key_id,
                APIKey.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(query)
        old_key = result.scalar_one_or_none()

        if not old_key:
            raise ValueError(f"API key {key_id} not found")

        # Verify ownership
        if old_key.user_id != user_id:
            raise AuthorizationError("You do not have permission to rotate this key")

        # Calculate new expiration (preserve relative expiration)
        expires_in_days = None
        if old_key.expires_at is not None:
            remaining_days = old_key.expires_in_days
            expires_in_days = max(1, remaining_days) if remaining_days else None

        # Create new key with same properties
        new_key_response = await self.create_api_key(
            user_id=user_id,
            name=old_key.name,
            scopes=old_key.scopes,
            expires_in_days=expires_in_days,
            rate_limit_tier=old_key.rate_limit_tier,
            prefix=old_key.key_prefix.split('_')[0],  # Extract original prefix
        )

        # Revoke the old key
        old_key.soft_delete()
        await self.session.flush()

        return new_key_response

    async def list_api_keys(self, user_id: UUID) -> List[APIKeyInfo]:
        """
        List all API keys for a user (excluding raw keys).

        Returns metadata for all non-deleted keys owned by the user.

        Args:
            user_id: UUID of the user

        Returns:
            List of APIKeyInfo (NO raw keys, only metadata)

        Example:
            >>> service = APIKeyService(session)
            >>> keys = await service.list_api_keys(user_uuid)
            >>> for key in keys:
            ...     print(f"{key.name}: {key.key_prefix}... (active: {key.is_active})")
        """
        query = select(APIKey).where(
            and_(
                APIKey.user_id == user_id,
                APIKey.deleted_at.is_(None),
            )
        ).order_by(APIKey.created_at.desc())

        result = await self.session.execute(query)
        api_keys = result.scalars().all()

        return [
            APIKeyInfo(
                id=key.id,
                user_id=key.user_id,
                name=key.name,
                key_prefix=key.key_prefix,
                scopes=key.scopes,
                rate_limit_tier=key.rate_limit_tier,
                expires_at=key.expires_at,
                last_used_at=key.last_used_at,
                created_at=key.created_at,
                updated_at=key.updated_at,
                is_active=key.is_active,
                is_expired=key.is_expired,
            )
            for key in api_keys
        ]

    async def get_api_key(self, key_id: UUID, user_id: UUID) -> Optional[APIKeyInfo]:
        """
        Get information about a specific API key.

        Args:
            key_id: UUID of the key
            user_id: UUID of the user (for ownership verification)

        Returns:
            APIKeyInfo if found and owned by user, None otherwise

        Raises:
            AuthorizationError: If user doesn't own the key

        Example:
            >>> service = APIKeyService(session)
            >>> key_info = await service.get_api_key(key_uuid, user_uuid)
            >>> if key_info:
            ...     print(f"Key: {key_info.name} - Status: {key_info.status}")
        """
        query = select(APIKey).where(
            and_(
                APIKey.id == key_id,
                APIKey.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(query)
        api_key = result.scalar_one_or_none()

        if not api_key:
            return None

        # Verify ownership
        if api_key.user_id != user_id:
            raise AuthorizationError("You do not have permission to view this key")

        return APIKeyInfo(
            id=api_key.id,
            user_id=api_key.user_id,
            name=api_key.name,
            key_prefix=api_key.key_prefix,
            scopes=api_key.scopes,
            rate_limit_tier=api_key.rate_limit_tier,
            expires_at=api_key.expires_at,
            last_used_at=api_key.last_used_at,
            created_at=api_key.created_at,
            updated_at=api_key.updated_at,
            is_active=api_key.is_active,
            is_expired=api_key.is_expired,
        )

    async def update_last_used(self, key_id: UUID) -> bool:
        """
        Update the last_used_at timestamp for a key.

        This is called automatically during validation but can also
        be called explicitly if needed.

        Args:
            key_id: UUID of the key to update

        Returns:
            True if updated, False if key not found

        Example:
            >>> service = APIKeyService(session)
            >>> await service.update_last_used(key_uuid)
        """
        query = select(APIKey).where(
            and_(
                APIKey.id == key_id,
                APIKey.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(query)
        api_key = result.scalar_one_or_none()

        if not api_key:
            return False

        api_key.update_last_used()
        await self.session.flush()

        return True
