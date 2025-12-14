"""
Authentication configuration factory.

This module provides factory functions to create authentication configurations
and providers from application settings, with validation and caching.
"""

import logging
from functools import lru_cache
from typing import Optional

from pydantic import SecretStr, ValidationError

from ..auth.exceptions import ProviderConfigError
from ..auth.providers import IAuthProvider, create_auth_provider
from ..auth.schemas import AuthConfig, AuthProvider, AzureADConfig, CognitoConfig
from .settings import Settings, get_settings

logger = logging.getLogger(__name__)


def get_auth_config(settings: Optional[Settings] = None) -> Optional[AuthConfig]:
    """
    Create AuthConfig from application settings.

    This function converts the flat settings structure into a properly
    structured AuthConfig object with provider-specific configurations.

    Args:
        settings: Application settings (defaults to get_settings())

    Returns:
        AuthConfig instance if auth is enabled, None if auth_provider is "none"

    Raises:
        ProviderConfigError: If configuration is invalid or incomplete

    Example:
        >>> from agent_service.config.auth import get_auth_config
        >>> auth_config = get_auth_config()
        >>> if auth_config:
        ...     provider = create_auth_provider(auth_config)
    """
    if settings is None:
        settings = get_settings()

    # Check if authentication is disabled
    if settings.auth_provider == "none":
        logger.info("Authentication is disabled (auth_provider=none)")
        return None

    try:
        # Map provider string to enum
        provider_map = {
            "azure_ad": AuthProvider.AZURE_AD,
            "aws_cognito": AuthProvider.AWS_COGNITO,
        }

        if settings.auth_provider not in provider_map:
            raise ProviderConfigError(
                f"Unknown auth provider: {settings.auth_provider}",
                provider=settings.auth_provider,
            )

        provider = provider_map[settings.auth_provider]

        # Build provider-specific configuration
        azure_ad_config: Optional[AzureADConfig] = None
        cognito_config: Optional[CognitoConfig] = None

        if provider == AuthProvider.AZURE_AD:
            # Validate required Azure AD fields
            missing_fields = []
            if not settings.azure_tenant_id:
                missing_fields.append("azure_tenant_id")
            if not settings.azure_client_id:
                missing_fields.append("azure_client_id")

            if missing_fields:
                raise ProviderConfigError(
                    "Azure AD configuration is incomplete",
                    provider="azure_ad",
                    missing_fields=missing_fields,
                )

            # Build Azure AD config
            azure_ad_config = AzureADConfig(
                tenant_id=settings.azure_tenant_id,
                client_id=settings.azure_client_id,
                client_secret=(
                    settings.azure_client_secret.get_secret_value()
                    if isinstance(settings.azure_client_secret, SecretStr)
                    else settings.azure_client_secret
                ),
                authority=settings.azure_authority,
                cache_ttl=settings.auth_jwks_cache_ttl,
            )

            logger.info(
                f"Created Azure AD config for tenant: {settings.azure_tenant_id}"
            )

        elif provider == AuthProvider.AWS_COGNITO:
            # Validate required Cognito fields
            missing_fields = []
            if not settings.aws_region:
                missing_fields.append("aws_region")
            if not settings.aws_cognito_user_pool_id:
                missing_fields.append("aws_cognito_user_pool_id")
            if not settings.aws_cognito_client_id:
                missing_fields.append("aws_cognito_client_id")

            if missing_fields:
                raise ProviderConfigError(
                    "AWS Cognito configuration is incomplete",
                    provider="aws_cognito",
                    missing_fields=missing_fields,
                )

            # Build Cognito config
            cognito_config = CognitoConfig(
                region=settings.aws_region,
                user_pool_id=settings.aws_cognito_user_pool_id,
                client_id=settings.aws_cognito_client_id,
                client_secret=(
                    settings.aws_cognito_client_secret.get_secret_value()
                    if isinstance(settings.aws_cognito_client_secret, SecretStr)
                    else settings.aws_cognito_client_secret
                ),
                jwks_cache_ttl=settings.auth_jwks_cache_ttl,
            )

            logger.info(
                f"Created Cognito config for pool: {settings.aws_cognito_user_pool_id}"
            )

        # Create and return AuthConfig
        auth_config = AuthConfig(
            provider=provider,
            azure_ad=azure_ad_config,
            cognito=cognito_config,
            enable_logging=True,
            log_level="INFO" if settings.log_level == 20 else "DEBUG",
        )

        logger.info(f"Authentication configuration created for provider: {provider.value}")
        return auth_config

    except ValidationError as e:
        logger.error(f"Failed to create auth config: {e}")
        raise ProviderConfigError(
            "Authentication configuration validation failed",
            provider=settings.auth_provider,
            original_error=e,
        )
    except Exception as e:
        if isinstance(e, ProviderConfigError):
            raise
        logger.error(f"Unexpected error creating auth config: {e}")
        raise ProviderConfigError(
            "Failed to create authentication configuration",
            provider=settings.auth_provider,
            original_error=e,
        )


@lru_cache
def get_auth_provider() -> Optional[IAuthProvider]:
    """
    Get cached authentication provider instance.

    This function creates and caches an authentication provider based on
    the application settings. Returns None if authentication is disabled.

    The provider is cached using @lru_cache to avoid recreating it on
    every request. Clear the cache by calling get_auth_provider.cache_clear()
    if you need to reload the configuration.

    Returns:
        Initialized authentication provider instance, or None if auth is disabled

    Raises:
        ProviderConfigError: If provider configuration is invalid

    Example:
        >>> from agent_service.config.auth import get_auth_provider
        >>> provider = get_auth_provider()
        >>> if provider:
        ...     user_info = provider.get_user_info(token)
        ... else:
        ...     # Authentication is disabled
        ...     pass
    """
    # Get auth config
    auth_config = get_auth_config()

    # Return None if auth is disabled
    if auth_config is None:
        logger.info("Authentication provider not initialized (auth disabled)")
        return None

    try:
        # Create and return provider
        provider = create_auth_provider(auth_config)
        logger.info(
            f"Authentication provider initialized: {provider.get_provider_name()}"
        )
        return provider

    except Exception as e:
        if isinstance(e, ProviderConfigError):
            raise
        logger.error(f"Failed to create authentication provider: {e}")
        raise ProviderConfigError(
            "Failed to initialize authentication provider",
            provider=auth_config.provider.value,
            original_error=e,
        )


def is_auth_enabled() -> bool:
    """
    Check if authentication is enabled.

    Returns:
        True if authentication is enabled, False otherwise

    Example:
        >>> from agent_service.config.auth import is_auth_enabled
        >>> if is_auth_enabled():
        ...     # Require authentication
        ...     provider = get_auth_provider()
        ... else:
        ...     # Skip authentication
        ...     pass
    """
    settings = get_settings()
    return settings.auth_provider != "none"


__all__ = [
    "get_auth_config",
    "get_auth_provider",
    "is_auth_enabled",
]
