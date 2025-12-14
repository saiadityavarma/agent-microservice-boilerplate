"""
AWS Cognito authentication provider.

This module implements AWS Cognito User Pool authentication using boto3
and python-jose for JWT validation, with JWKS caching and group-based
authorization support.
"""

import logging
import time
from typing import Any, Optional

import boto3
import requests
from cachetools import TTLCache
from jose import jwt, JWTError

from ..exceptions import (
    AuthenticationError,
    InvalidTokenError,
    ProviderConfigError,
    TokenExpiredError,
)
from ..schemas import (
    AuthProvider,
    CognitoConfig,
    TokenPayload,
    TokenResponse,
    UserInfo,
)
from .base import IAuthProvider

logger = logging.getLogger(__name__)


class CognitoAuthProvider(IAuthProvider):
    """
    AWS Cognito authentication provider.

    Implements token verification using Cognito's JWKS endpoint and JWT validation.
    Supports Cognito groups for authorization and caches JWKS for performance.
    """

    def __init__(self, config: CognitoConfig) -> None:
        """
        Initialize AWS Cognito authentication provider.

        Args:
            config: Cognito configuration settings

        Raises:
            ProviderConfigError: If configuration is invalid
        """
        self.config = config
        self._jwks_cache: TTLCache = TTLCache(
            maxsize=1,
            ttl=config.jwks_cache_ttl
        )
        self._token_validation_cache: TTLCache = TTLCache(
            maxsize=1000,
            ttl=300  # 5 minutes for token validation cache
        )
        self._cognito_client: Optional[Any] = None

        # Validate configuration
        self.validate_configuration()

        # Initialize boto3 client
        self._initialize_cognito_client()

        logger.info(
            f"Initialized Cognito provider for user pool: {config.user_pool_id}"
        )

    def validate_configuration(self) -> None:
        """
        Validate Cognito configuration.

        Raises:
            ProviderConfigError: If configuration is invalid or incomplete
        """
        missing_fields: list[str] = []

        if not self.config.region:
            missing_fields.append("region")
        if not self.config.user_pool_id:
            missing_fields.append("user_pool_id")
        if not self.config.client_id:
            missing_fields.append("client_id")

        if missing_fields:
            raise ProviderConfigError(
                "Cognito configuration is incomplete",
                provider="aws_cognito",
                missing_fields=missing_fields
            )

    def _initialize_cognito_client(self) -> None:
        """
        Initialize boto3 Cognito Identity Provider client.

        Raises:
            ProviderConfigError: If client initialization fails
        """
        try:
            self._cognito_client = boto3.client(
                "cognito-idp",
                region_name=self.config.region
            )
            logger.debug(f"Initialized Cognito client for region: {self.config.region}")

        except Exception as e:
            logger.error(f"Failed to initialize Cognito client: {str(e)}")
            raise ProviderConfigError(
                "Failed to initialize AWS Cognito client",
                provider="aws_cognito",
                original_error=e
            )

    def _get_jwks(self) -> dict[str, Any]:
        """
        Get JWKS from Cognito with caching.

        Returns:
            JWKS dictionary containing public keys

        Raises:
            InvalidTokenError: If JWKS cannot be retrieved
        """
        # Check cache first
        cache_key = "jwks"
        if cache_key in self._jwks_cache:
            logger.debug("Using cached JWKS")
            return self._jwks_cache[cache_key]

        try:
            logger.debug(f"Fetching JWKS from: {self.config.jwks_uri}")
            response = requests.get(self.config.jwks_uri, timeout=10)
            response.raise_for_status()

            jwks = response.json()
            self._jwks_cache[cache_key] = jwks
            logger.debug("Cached JWKS successfully")

            return jwks

        except requests.RequestException as e:
            logger.error(f"Failed to fetch JWKS: {str(e)}")
            raise InvalidTokenError(
                "Failed to retrieve JWKS from Cognito",
                provider="aws_cognito",
                original_error=e
            )

    def _get_signing_key(self, kid: str) -> dict[str, Any]:
        """
        Get signing key from JWKS by key ID.

        Args:
            kid: Key ID from JWT header

        Returns:
            Signing key dictionary

        Raises:
            InvalidTokenError: If signing key cannot be found
        """
        jwks = self._get_jwks()

        # Find the key with matching kid
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                logger.debug(f"Found signing key for kid: {kid}")
                return key

        raise InvalidTokenError(
            "Signing key not found in JWKS",
            provider="aws_cognito",
            reason=f"No key found with kid: {kid}"
        )

    def verify_token(self, token: str) -> TokenPayload:
        """
        Verify and decode Cognito JWT token.

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
                    provider="aws_cognito"
                )

            # Get signing key
            signing_key = self._get_signing_key(kid)

            # Prepare validation options
            decode_options: dict[str, Any] = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_aud": self.config.validate_audience,
                "verify_iss": True,
            }

            # Decode and validate token
            logger.debug("Validating JWT token")
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.config.client_id if self.config.validate_audience else None,
                issuer=self.config.issuer,
                options=decode_options
            )

            # Validate token_use claim
            token_use = claims.get("token_use")
            if token_use != self.config.token_use:
                raise InvalidTokenError(
                    f"Invalid token_use claim. Expected: {self.config.token_use}, Got: {token_use}",
                    provider="aws_cognito"
                )

            # Extract groups from claims (Cognito uses 'cognito:groups')
            groups: list[str] = []
            if "cognito:groups" in claims:
                cognito_groups = claims["cognito:groups"]
                groups = cognito_groups if isinstance(cognito_groups, list) else [cognito_groups]

            # Cognito doesn't have built-in roles, but we can use custom attributes
            roles: list[str] = []
            if "custom:roles" in claims:
                custom_roles = claims["custom:roles"]
                # Handle comma-separated roles or JSON array
                if isinstance(custom_roles, str):
                    roles = [r.strip() for r in custom_roles.split(",")]
                elif isinstance(custom_roles, list):
                    roles = custom_roles

            # Create token payload
            token_payload = TokenPayload(
                sub=claims["sub"],
                exp=claims["exp"],
                iat=claims["iat"],
                iss=claims["iss"],
                aud=claims.get("aud") or claims.get("client_id", self.config.client_id),
                roles=roles,
                groups=groups,
                email=claims.get("email"),
                name=claims.get("name") or claims.get("cognito:username"),
                tenant_id=None  # Cognito doesn't have multi-tenancy
            )

            # Cache the result
            self._token_validation_cache[cache_key] = token_payload
            logger.info(f"Token verified successfully for user: {token_payload.sub}")

            return token_payload

        except jwt.ExpiredSignatureError as e:
            logger.warning("Token has expired")
            raise TokenExpiredError(
                "Cognito token has expired",
                provider="aws_cognito",
                original_error=e
            )
        except JWTError as e:
            logger.warning(f"Invalid token: {str(e)}")
            raise InvalidTokenError(
                "Invalid Cognito token",
                provider="aws_cognito",
                reason=str(e),
                original_error=e
            )
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            raise AuthenticationError(
                "Token verification failed",
                provider="aws_cognito",
                original_error=e
            )

    def get_user_info(self, token: str) -> UserInfo:
        """
        Extract user information from Cognito token.

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

            # Extract additional metadata from Cognito if needed
            metadata: dict[str, Any] = {
                "user_pool_id": self.config.user_pool_id
            }

            # Create user info
            user_info = UserInfo(
                id=token_payload.sub,
                email=token_payload.email,
                name=token_payload.name,
                roles=token_payload.roles,
                groups=token_payload.groups,
                provider=AuthProvider.AWS_COGNITO,
                tenant_id=None,
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
                provider="aws_cognito",
                original_error=e
            )

    def refresh_token(self, refresh_token: str) -> TokenResponse:
        """
        Refresh access token using Cognito.

        Args:
            refresh_token: Refresh token string

        Returns:
            TokenResponse containing new access token

        Raises:
            AuthenticationError: If token refresh fails
            ProviderConfigError: If client secret is required but not configured
        """
        if not self._cognito_client:
            raise ProviderConfigError(
                "Cognito client not initialized",
                provider="aws_cognito"
            )

        try:
            # Prepare auth parameters
            auth_params = {
                "REFRESH_TOKEN": refresh_token
            }

            # Add client secret if configured
            if self.config.client_secret:
                import hmac
                import hashlib
                import base64

                # Calculate SECRET_HASH for Cognito
                message = bytes(self.config.client_id + refresh_token, "utf-8")
                secret = bytes(self.config.client_secret, "utf-8")
                secret_hash = base64.b64encode(
                    hmac.new(secret, message, digestmod=hashlib.sha256).digest()
                ).decode()

                auth_params["SECRET_HASH"] = secret_hash

            # Initiate auth with refresh token
            logger.debug("Attempting to refresh token using Cognito")
            response = self._cognito_client.initiate_auth(
                ClientId=self.config.client_id,
                AuthFlow="REFRESH_TOKEN_AUTH",
                AuthParameters=auth_params
            )

            auth_result = response.get("AuthenticationResult")
            if not auth_result:
                raise AuthenticationError(
                    "Token refresh failed: No authentication result returned",
                    provider="aws_cognito"
                )

            logger.info("Token refreshed successfully")

            return TokenResponse(
                access_token=auth_result["AccessToken"],
                token_type=auth_result.get("TokenType", "Bearer"),
                expires_in=auth_result.get("ExpiresIn", 3600),
                refresh_token=auth_result.get("RefreshToken"),  # May be rotated
                scope=None
            )

        except self._cognito_client.exceptions.NotAuthorizedException as e:
            logger.error(f"Refresh token not authorized: {str(e)}")
            raise InvalidTokenError(
                "Refresh token is invalid or expired",
                provider="aws_cognito",
                original_error=e
            )
        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            raise AuthenticationError(
                "Token refresh failed",
                provider="aws_cognito",
                original_error=e
            )

    def get_user_groups(self, username: str) -> list[str]:
        """
        Get user's Cognito groups using boto3 (admin operation).

        This is an additional method specific to Cognito for fetching
        groups when they're not included in the token.

        Args:
            username: Cognito username

        Returns:
            List of group names the user belongs to

        Raises:
            AuthenticationError: If group retrieval fails
        """
        if not self._cognito_client:
            raise ProviderConfigError(
                "Cognito client not initialized",
                provider="aws_cognito"
            )

        try:
            logger.debug(f"Fetching groups for user: {username}")
            response = self._cognito_client.admin_list_groups_for_user(
                Username=username,
                UserPoolId=self.config.user_pool_id
            )

            groups = [group["GroupName"] for group in response.get("Groups", [])]
            logger.info(f"Retrieved {len(groups)} groups for user: {username}")

            return groups

        except Exception as e:
            logger.error(f"Failed to fetch user groups: {str(e)}")
            raise AuthenticationError(
                "Failed to retrieve user groups",
                provider="aws_cognito",
                original_error=e
            )

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "aws_cognito"
