"""
Pydantic schemas for API key requests and responses.

This module defines the data validation and serialization schemas for API key
operations. Raw keys are NEVER included in schemas except in the initial
creation response (APIKeyResponse).
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, ConfigDict


class APIKeyParts(BaseModel):
    """
    Parsed components of an API key.

    Used for key format validation and inspection.

    Attributes:
        prefix: The key prefix (e.g., 'sk', 'sk_live')
        random_part: The random cryptographic component
        full_key: The complete key string
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    prefix: str = Field(
        ...,
        description="Key prefix identifying the key type",
        min_length=1,
        max_length=12
    )
    random_part: str = Field(
        ...,
        description="Random cryptographic component",
        min_length=16
    )
    full_key: str = Field(
        ...,
        description="Complete API key string",
        min_length=18
    )


class APIKeyCreate(BaseModel):
    """
    Schema for creating a new API key.

    Attributes:
        name: Human-friendly name for the key
        scopes: List of permission scopes
        rate_limit_tier: Rate limiting tier
        expires_in_days: Optional number of days until expiration
        prefix: Optional custom prefix (default: "sk")
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(
        ...,
        description="Human-friendly name for the API key",
        min_length=1,
        max_length=255,
        examples=["Production API", "Development Key", "CI/CD Pipeline"]
    )
    scopes: List[str] = Field(
        default_factory=list,
        description="List of permission scopes",
        examples=[["read", "write"], ["admin"], ["read"]]
    )
    rate_limit_tier: str = Field(
        default="free",
        description="Rate limit tier (free, pro, enterprise)",
        pattern="^(free|pro|enterprise)$"
    )
    expires_in_days: Optional[int] = Field(
        default=None,
        description="Number of days until key expires (None = never expires)",
        gt=0,
        le=3650,  # Max 10 years
        examples=[30, 90, 365, None]
    )
    prefix: str = Field(
        default="sk",
        description="Key prefix (default: sk)",
        min_length=2,
        max_length=12,
        pattern="^[a-z_]+$",
        examples=["sk", "sk_live", "sk_test"]
    )

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, v: List[str]) -> List[str]:
        """Validate and normalize scopes."""
        if not v:
            return []

        # Remove duplicates and empty strings
        scopes = [s.strip().lower() for s in v if s.strip()]
        return list(set(scopes))

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name is not empty after stripping."""
        if not v.strip():
            raise ValueError("Name cannot be empty or only whitespace")
        return v.strip()


class APIKeyResponse(BaseModel):
    """
    Schema for API key creation response.

    CRITICAL: This is the ONLY schema that contains the raw API key.
    The raw key is shown ONCE and NEVER stored or returned again.

    Attributes:
        id: Unique identifier for the key
        user_id: User who owns the key
        name: Human-friendly name
        key: THE RAW API KEY - shown only once, never stored
        key_prefix: First part of the key for identification
        scopes: Permission scopes
        rate_limit_tier: Rate limiting tier
        expires_at: Optional expiration timestamp
        created_at: Creation timestamp

    Security Note:
        The 'key' field contains the raw API key and should be:
        - Displayed to the user ONCE
        - Never logged
        - Never stored
        - Never transmitted again after initial creation
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    id: UUID = Field(
        ...,
        description="Unique identifier for the API key"
    )
    user_id: UUID = Field(
        ...,
        description="User who owns this key"
    )
    name: str = Field(
        ...,
        description="Human-friendly name for the key"
    )
    key: str = Field(
        ...,
        description="RAW API KEY - shown only once, NEVER stored or returned again",
        min_length=18
    )
    key_prefix: str = Field(
        ...,
        description="Key prefix for identification (e.g., 'sk_live')"
    )
    scopes: List[str] = Field(
        default_factory=list,
        description="Permission scopes"
    )
    rate_limit_tier: str = Field(
        ...,
        description="Rate limit tier"
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Expiration timestamp (None = never expires)"
    )
    created_at: datetime = Field(
        ...,
        description="Creation timestamp"
    )


class APIKeyInfo(BaseModel):
    """
    Schema for API key information (without raw key).

    Used for listing and displaying existing keys.
    NEVER includes the raw key - only metadata.

    Attributes:
        id: Unique identifier
        user_id: User who owns the key
        name: Human-friendly name
        key_prefix: First part of the key for identification
        scopes: Permission scopes
        rate_limit_tier: Rate limiting tier
        expires_at: Optional expiration timestamp
        last_used_at: Timestamp of last use
        created_at: Creation timestamp
        updated_at: Last update timestamp
        is_active: Whether the key is currently active
        is_expired: Whether the key has expired
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    id: UUID = Field(
        ...,
        description="Unique identifier for the API key"
    )
    user_id: UUID = Field(
        ...,
        description="User who owns this key"
    )
    name: str = Field(
        ...,
        description="Human-friendly name for the key"
    )
    key_prefix: str = Field(
        ...,
        description="Key prefix for identification (e.g., 'sk_live_abc1...')"
    )
    scopes: List[str] = Field(
        default_factory=list,
        description="Permission scopes"
    )
    rate_limit_tier: str = Field(
        ...,
        description="Rate limit tier"
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Expiration timestamp (None = never expires)"
    )
    last_used_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp of last successful authentication"
    )
    created_at: datetime = Field(
        ...,
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp"
    )
    is_active: bool = Field(
        ...,
        description="Whether the key is currently active"
    )
    is_expired: bool = Field(
        ...,
        description="Whether the key has expired"
    )

    @property
    def status(self) -> str:
        """
        Get human-readable status of the key.

        Returns:
            Status string: "active", "expired", "revoked"
        """
        if not self.is_active:
            return "revoked"
        if self.is_expired:
            return "expired"
        return "active"


class APIKeyUpdate(BaseModel):
    """
    Schema for updating an existing API key.

    Allows updating metadata without changing the key itself.

    Attributes:
        name: New name for the key
        scopes: New permission scopes
        rate_limit_tier: New rate limit tier
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    name: Optional[str] = Field(
        default=None,
        description="New name for the key",
        min_length=1,
        max_length=255
    )
    scopes: Optional[List[str]] = Field(
        default=None,
        description="New permission scopes"
    )
    rate_limit_tier: Optional[str] = Field(
        default=None,
        description="New rate limit tier",
        pattern="^(free|pro|enterprise)$"
    )

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate and normalize scopes."""
        if v is None:
            return None

        # Remove duplicates and empty strings
        scopes = [s.strip().lower() for s in v if s.strip()]
        return list(set(scopes))

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate name is not empty after stripping."""
        if v is not None and not v.strip():
            raise ValueError("Name cannot be empty or only whitespace")
        return v.strip() if v else None


class APIKeyValidation(BaseModel):
    """
    Schema for API key validation response.

    Returned after successful key validation during authentication.

    Attributes:
        id: Key identifier
        user_id: User who owns the key
        scopes: Permission scopes
        rate_limit_tier: Rate limiting tier
        is_active: Whether the key is active
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    id: UUID = Field(
        ...,
        description="Unique identifier for the API key"
    )
    user_id: UUID = Field(
        ...,
        description="User who owns this key"
    )
    scopes: List[str] = Field(
        default_factory=list,
        description="Permission scopes"
    )
    rate_limit_tier: str = Field(
        ...,
        description="Rate limit tier for rate limiting middleware"
    )
    is_active: bool = Field(
        ...,
        description="Whether the key is currently active"
    )
