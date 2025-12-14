"""
Azure Active Directory authentication provider.

This module implements Azure AD authentication using MSAL and JWT validation,
supporting both single-tenant and multi-tenant scenarios with role-based
access control through App Roles.
"""

import logging
import time
from typing import Any, Optional

import jwt
import msal
import requests
from cachetools import TTLCache

from ..exceptions import (
    AuthenticationError,
    InvalidTokenError,
    ProviderConfigError,
    TokenExpiredError,
)
from ..schemas import (
    AuthProvider,
    AzureADConfig,
    TokenPayload,
    TokenResponse,
    UserInfo,
)
from .base import IAuthProvider

logger = logging.getLogger(__name__)


class AzureADAuthProvider(IAuthProvider):
    """
    Azure Active Directory authentication provider.

    Implements token verification using Azure AD's OIDC discovery and JWT validation.
    Supports App Roles, security groups, and both single-tenant and multi-tenant apps.
    """

    def __init__(self, config: AzureADConfig) -> None:
        """
        Initialize Azure AD authentication provider.

        Args:
            config: Azure AD configuration settings

        Raises:
            ProviderConfigError: If configuration is invalid
        """
        self.config = config
        self._signing_keys_cache: TTLCache = TTLCache(
            maxsize=100,
            ttl=config.cache_ttl
        )
        self._token_validation_cache: TTLCache = TTLCache(
            maxsize=1000,
            ttl=config.cache_ttl
        )
        self._oidc_config: Optional[dict[str, Any]] = None
        self._jwks_uri: Optional[str] = None

        # Validate configuration
        self.validate_configuration()

        # Initialize OIDC discovery
        self._initialize_oidc_discovery()

        logger.info(
            f"Initialized Azure AD provider for tenant: {config.tenant_id}"
        )

    def validate_configuration(self) -> None:
        """
        Validate Azure AD configuration.

        Raises:
            ProviderConfigError: If configuration is invalid or incomplete
        """
        missing_fields: list[str] = []

        if not self.config.tenant_id:
            missing_fields.append("tenant_id")
        if not self.config.client_id:
            missing_fields.append("client_id")

        if missing_fields:
            raise ProviderConfigError(
                "Azure AD configuration is incomplete",
                provider="azure_ad",
                missing_fields=missing_fields
            )

    def _initialize_oidc_discovery(self) -> None:
        """
        Initialize OIDC discovery to get JWKS URI and issuer.

        Raises:
            ProviderConfigError: If OIDC discovery fails
        """
        try:
            discovery_url = (
                f"{self.config.authority_url}/v2.0/.well-known/openid-configuration"
            )
            logger.debug(f"Fetching OIDC configuration from: {discovery_url}")

            response = requests.get(discovery_url, timeout=10)
            response.raise_for_status()

            self._oidc_config = response.json()
            self._jwks_uri = self._oidc_config["jwks_uri"]

            logger.info(f"OIDC discovery successful. JWKS URI: {self._jwks_uri}")

        except Exception as e:
            logger.error(f"OIDC discovery failed: {str(e)}")
            raise ProviderConfigError(
                "Failed to initialize Azure AD OIDC discovery",
                provider="azure_ad",
                original_error=e
            )

    def _get_signing_key(self, kid: str) -> Any:
        """
        Get signing key from Azure AD JWKS endpoint with caching.

        Args:
            kid: Key ID from JWT header

        Returns:
            Signing key for JWT verification

        Raises:
            InvalidTokenError: If signing key cannot be retrieved
        """
        # Check cache first
        if kid in self._signing_keys_cache:
            logger.debug(f"Using cached signing key for kid: {kid}")
            return self._signing_keys_cache[kid]

        try:
            logger.debug(f"Fetching signing keys from: {self._jwks_uri}")
            response = requests.get(self._jwks_uri, timeout=10)
            response.raise_for_status()

            jwks = response.json()

            # Find the key with matching kid
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    # Convert JWK to PEM format for PyJWT
                    signing_key = jwt.PyJWK(key)
                    self._signing_keys_cache[kid] = signing_key
                    logger.debug(f"Cached signing key for kid: {kid}")
                    return signing_key

            raise InvalidTokenError(
                "Signing key not found in JWKS",
                provider="azure_ad",
                reason=f"No key found with kid: {kid}"
            )

        except requests.RequestException as e:
            logger.error(f"Failed to fetch signing keys: {str(e)}")
            raise InvalidTokenError(
                "Failed to retrieve signing keys",
                provider="azure_ad",
                original_error=e
            )

    def verify_token(self, token: str) -> TokenPayload:
        """
        Verify and decode Azure AD JWT token.

        Args:
            token: JWT token string to verify

        Returns:
            TokenPayload containing decoded and validated token claims

        Raises:
            InvalidTokenError: If token is malformed or signature is invalid
            TokenExpiredError: If token has expired
            AuthenticationError: If token validation fails
        """
        # Check cache first
        cache_key = f"token:{token[:50]}"  # Use partial token as key
        if cache_key in self._token_validation_cache:
            logger.debug("Returning cached token validation result")
            return self._token_validation_cache[cache_key]

        try:
            # Decode header to get kid
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            if not kid:
                raise InvalidTokenError(
                    "Token missing 'kid' in header",
                    provider="azure_ad"
                )

            # Get signing key
            signing_key = self._get_signing_key(kid)

            # Prepare validation options
            decode_options: dict[str, Any] = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_aud": self.config.validate_audience,
                "verify_iss": self.config.validate_issuer,
            }

            # Prepare validation parameters
            decode_params: dict[str, Any] = {
                "algorithms": ["RS256"],
                "options": decode_options,
            }

            # Add audience validation
            if self.config.validate_audience:
                if self.config.allowed_audiences:
                    decode_params["audience"] = self.config.allowed_audiences
                else:
                    decode_params["audience"] = self.config.client_id

            # Add issuer validation
            if self.config.validate_issuer:
                # Azure AD issuer format
                expected_issuer = (
                    f"https://login.microsoftonline.com/{self.config.tenant_id}/v2.0"
                )
                decode_params["issuer"] = expected_issuer

            # Decode and validate token
            logger.debug("Validating JWT token")
            claims = jwt.decode(
                token,
                signing_key.key,
                **decode_params
            )

            # Extract roles from claims
            roles: list[str] = []
            if "roles" in claims:
                roles = claims["roles"] if isinstance(claims["roles"], list) else [claims["roles"]]

            # Extract groups from claims
            groups: list[str] = []
            if "groups" in claims:
                groups = claims["groups"] if isinstance(claims["groups"], list) else [claims["groups"]]

            # Create token payload
            token_payload = TokenPayload(
                sub=claims["sub"],
                exp=claims["exp"],
                iat=claims["iat"],
                iss=claims["iss"],
                aud=claims["aud"],
                roles=roles,
                groups=groups,
                email=claims.get("email") or claims.get("preferred_username"),
                name=claims.get("name"),
                tenant_id=claims.get("tid")
            )

            # Cache the result
            self._token_validation_cache[cache_key] = token_payload
            logger.info(f"Token verified successfully for user: {token_payload.sub}")

            return token_payload

        except jwt.ExpiredSignatureError as e:
            logger.warning("Token has expired")
            raise TokenExpiredError(
                "Azure AD token has expired",
                provider="azure_ad",
                original_error=e
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            raise InvalidTokenError(
                "Invalid Azure AD token",
                provider="azure_ad",
                reason=str(e),
                original_error=e
            )
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            raise AuthenticationError(
                "Token verification failed",
                provider="azure_ad",
                original_error=e
            )

    def get_user_info(self, token: str) -> UserInfo:
        """
        Extract user information from Azure AD token.

        Args:
            token: JWT token string to extract user information from

        Returns:
            UserInfo containing user identity and authorization data

        Raises:
            InvalidTokenError: If token is invalid
            TokenExpiredError: If token has expired
            AuthenticationError: If extraction fails
        """
        try:
            # Verify token and get payload
            token_payload = self.verify_token(token)

            # Extract additional metadata
            metadata: dict[str, Any] = {}
            if token_payload.tenant_id:
                metadata["tenant_id"] = token_payload.tenant_id

            # Create user info
            user_info = UserInfo(
                id=token_payload.sub,
                email=token_payload.email,
                name=token_payload.name,
                roles=token_payload.roles,
                groups=token_payload.groups,
                provider=AuthProvider.AZURE_AD,
                tenant_id=token_payload.tenant_id,
                metadata=metadata
            )

            logger.info(
                f"Extracted user info for: {user_info.email or user_info.id}"
            )

            return user_info

        except (InvalidTokenError, TokenExpiredError, AuthenticationError):
            raise
        except Exception as e:
            logger.error(f"Failed to extract user info: {str(e)}")
            raise AuthenticationError(
                "Failed to extract user information from token",
                provider="azure_ad",
                original_error=e
            )

    def refresh_token(self, refresh_token: str) -> TokenResponse:
        """
        Refresh access token using MSAL.

        Args:
            refresh_token: Refresh token string

        Returns:
            TokenResponse containing new access token

        Raises:
            AuthenticationError: If token refresh fails
            ProviderConfigError: If client secret is not configured
        """
        if not self.config.client_secret:
            raise ProviderConfigError(
                "Client secret required for token refresh",
                provider="azure_ad",
                missing_fields=["client_secret"]
            )

        try:
            # Create MSAL confidential client app
            app = msal.ConfidentialClientApplication(
                client_id=self.config.client_id,
                client_credential=self.config.client_secret,
                authority=self.config.authority_url
            )

            # Acquire token by refresh token
            logger.debug("Attempting to refresh token using MSAL")
            result = app.acquire_token_by_refresh_token(
                refresh_token=refresh_token,
                scopes=["openid", "profile", "email"]
            )

            if "access_token" not in result:
                error_description = result.get(
                    "error_description",
                    result.get("error", "Unknown error")
                )
                raise AuthenticationError(
                    f"Token refresh failed: {error_description}",
                    provider="azure_ad"
                )

            logger.info("Token refreshed successfully")

            return TokenResponse(
                access_token=result["access_token"],
                token_type=result.get("token_type", "Bearer"),
                expires_in=result.get("expires_in", 3600),
                refresh_token=result.get("refresh_token"),
                scope=result.get("scope")
            )

        except msal.MsalError as e:
            logger.error(f"MSAL token refresh failed: {str(e)}")
            raise AuthenticationError(
                "Failed to refresh token",
                provider="azure_ad",
                original_error=e
            )
        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            raise AuthenticationError(
                "Token refresh failed",
                provider="azure_ad",
                original_error=e
            )

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "azure_ad"
