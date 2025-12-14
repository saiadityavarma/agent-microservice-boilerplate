"""
Pydantic models for authentication and authorization.

This module defines data models for tokens, user information, and provider
configurations using Pydantic for validation and serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


class AuthProvider(str, Enum):
    """Supported authentication providers."""

    AZURE_AD = "azure_ad"
    AWS_COGNITO = "aws_cognito"
    CUSTOM = "custom"


class TokenPayload(BaseModel):
    """
    JWT token payload with standard and custom claims.

    Contains the decoded and validated token claims including
    subject, expiration, issuer, and authorization data.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="allow")

    sub: str = Field(
        ...,
        description="Subject identifier (user ID)",
        min_length=1
    )
    exp: int = Field(
        ...,
        description="Expiration time as Unix timestamp",
        gt=0
    )
    iat: int = Field(
        ...,
        description="Issued at time as Unix timestamp",
        gt=0
    )
    iss: str = Field(
        ...,
        description="Issuer identifier (who issued the token)",
        min_length=1
    )
    aud: str | list[str] = Field(
        ...,
        description="Audience (intended recipient of the token)"
    )
    roles: list[str] = Field(
        default_factory=list,
        description="User roles for authorization"
    )
    groups: list[str] = Field(
        default_factory=list,
        description="User groups for authorization"
    )
    email: Optional[str] = Field(
        default=None,
        description="User email address"
    )
    name: Optional[str] = Field(
        default=None,
        description="User display name"
    )
    tenant_id: Optional[str] = Field(
        default=None,
        description="Tenant identifier (for multi-tenant scenarios)"
    )

    @field_validator("aud")
    @classmethod
    def normalize_audience(cls, v: str | list[str]) -> str | list[str]:
        """Normalize audience to ensure consistent handling."""
        if isinstance(v, str):
            return v
        return v

    @property
    def is_expired(self) -> bool:
        """Check if the token is expired."""
        return datetime.utcnow().timestamp() >= self.exp

    @property
    def expires_in(self) -> int:
        """Get seconds until token expires (negative if already expired)."""
        return int(self.exp - datetime.utcnow().timestamp())


class UserInfo(BaseModel):
    """
    User information extracted from authentication token.

    Contains user identity, contact information, and authorization data.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    id: str = Field(
        ...,
        description="Unique user identifier",
        min_length=1
    )
    email: Optional[str] = Field(
        default=None,
        description="User email address"
    )
    name: Optional[str] = Field(
        default=None,
        description="User display name"
    )
    roles: list[str] = Field(
        default_factory=list,
        description="User roles for authorization"
    )
    groups: list[str] = Field(
        default_factory=list,
        description="User groups for authorization"
    )
    provider: AuthProvider = Field(
        ...,
        description="Authentication provider that verified this user"
    )
    tenant_id: Optional[str] = Field(
        default=None,
        description="Tenant identifier (for multi-tenant scenarios)"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional provider-specific user metadata"
    )

    def has_role(self, role: str) -> bool:
        """
        Check if user has a specific role.

        Args:
            role: Role name to check

        Returns:
            True if user has the role, False otherwise
        """
        return role in self.roles

    def has_any_role(self, roles: list[str]) -> bool:
        """
        Check if user has any of the specified roles.

        Args:
            roles: List of role names to check

        Returns:
            True if user has at least one role, False otherwise
        """
        return any(role in self.roles for role in roles)

    def has_all_roles(self, roles: list[str]) -> bool:
        """
        Check if user has all of the specified roles.

        Args:
            roles: List of role names to check

        Returns:
            True if user has all roles, False otherwise
        """
        return all(role in self.roles for role in roles)

    def in_group(self, group: str) -> bool:
        """
        Check if user is in a specific group.

        Args:
            group: Group name to check

        Returns:
            True if user is in the group, False otherwise
        """
        return group in self.groups


class TokenResponse(BaseModel):
    """
    Response from token refresh operations.

    Contains new access token and optionally a new refresh token.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    access_token: str = Field(
        ...,
        description="New access token",
        min_length=1
    )
    token_type: str = Field(
        default="Bearer",
        description="Token type (typically 'Bearer')"
    )
    expires_in: int = Field(
        ...,
        description="Seconds until token expires",
        gt=0
    )
    refresh_token: Optional[str] = Field(
        default=None,
        description="New refresh token (if rotated)"
    )
    scope: Optional[str] = Field(
        default=None,
        description="Granted scopes"
    )


class AzureADConfig(BaseModel):
    """Configuration for Azure AD authentication provider."""

    model_config = ConfigDict(str_strip_whitespace=True)

    tenant_id: str = Field(
        ...,
        description="Azure AD tenant ID (or 'common' for multi-tenant)",
        min_length=1
    )
    client_id: str = Field(
        ...,
        description="Application (client) ID",
        min_length=1
    )
    client_secret: Optional[str] = Field(
        default=None,
        description="Client secret (if using client credentials flow)"
    )
    authority: Optional[str] = Field(
        default=None,
        description="Custom authority URL (if not using default)"
    )
    validate_issuer: bool = Field(
        default=True,
        description="Whether to validate token issuer"
    )
    validate_audience: bool = Field(
        default=True,
        description="Whether to validate token audience"
    )
    allowed_audiences: list[str] = Field(
        default_factory=list,
        description="List of allowed audience values"
    )
    cache_ttl: int = Field(
        default=3600,
        description="Token validation cache TTL in seconds",
        gt=0
    )

    @property
    def authority_url(self) -> str:
        """Get the authority URL for token validation."""
        if self.authority:
            return self.authority
        return f"https://login.microsoftonline.com/{self.tenant_id}"


class CognitoConfig(BaseModel):
    """Configuration for AWS Cognito authentication provider."""

    model_config = ConfigDict(str_strip_whitespace=True)

    region: str = Field(
        ...,
        description="AWS region (e.g., 'us-east-1')",
        min_length=1
    )
    user_pool_id: str = Field(
        ...,
        description="Cognito User Pool ID",
        min_length=1
    )
    client_id: str = Field(
        ...,
        description="App client ID",
        min_length=1
    )
    client_secret: Optional[str] = Field(
        default=None,
        description="App client secret (if configured)"
    )
    validate_audience: bool = Field(
        default=True,
        description="Whether to validate token audience (client_id)"
    )
    jwks_cache_ttl: int = Field(
        default=3600,
        description="JWKS cache TTL in seconds",
        gt=0
    )
    token_use: str = Field(
        default="access",
        description="Expected token use claim ('access' or 'id')"
    )

    @property
    def issuer(self) -> str:
        """Get the expected token issuer."""
        return f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"

    @property
    def jwks_uri(self) -> str:
        """Get the JWKS URI for public key retrieval."""
        return f"{self.issuer}/.well-known/jwks.json"


class AuthConfig(BaseModel):
    """
    Authentication configuration supporting multiple providers.

    Contains provider-specific configuration and general settings.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    provider: AuthProvider = Field(
        ...,
        description="Authentication provider to use"
    )
    azure_ad: Optional[AzureADConfig] = Field(
        default=None,
        description="Azure AD configuration (if provider is azure_ad)"
    )
    cognito: Optional[CognitoConfig] = Field(
        default=None,
        description="AWS Cognito configuration (if provider is aws_cognito)"
    )
    enable_logging: bool = Field(
        default=True,
        description="Whether to enable authentication logging"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )

    @field_validator("azure_ad")
    @classmethod
    def validate_azure_ad_config(
        cls,
        v: Optional[AzureADConfig],
        info: Any
    ) -> Optional[AzureADConfig]:
        """Validate that Azure AD config is provided when using Azure AD."""
        if info.data.get("provider") == AuthProvider.AZURE_AD and v is None:
            raise ValueError("azure_ad configuration required when provider is azure_ad")
        return v

    @field_validator("cognito")
    @classmethod
    def validate_cognito_config(
        cls,
        v: Optional[CognitoConfig],
        info: Any
    ) -> Optional[CognitoConfig]:
        """Validate that Cognito config is provided when using Cognito."""
        if info.data.get("provider") == AuthProvider.AWS_COGNITO and v is None:
            raise ValueError("cognito configuration required when provider is aws_cognito")
        return v
