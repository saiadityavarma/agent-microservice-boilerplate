"""
Authentication provider registry.

This module provides a registry for authentication providers and factory
functions to create provider instances based on configuration.
"""

import logging
from typing import Dict, Type

from ..exceptions import ProviderConfigError
from ..schemas import AuthConfig, AuthProvider
from .base import IAuthProvider
from .aws_cognito import CognitoAuthProvider
from .azure_ad import AzureADAuthProvider

logger = logging.getLogger(__name__)


# Provider registry mapping provider names to implementation classes
_PROVIDER_REGISTRY: Dict[AuthProvider, Type[IAuthProvider]] = {
    AuthProvider.AZURE_AD: AzureADAuthProvider,
    AuthProvider.AWS_COGNITO: CognitoAuthProvider,
}


def register_provider(
    provider_type: AuthProvider,
    provider_class: Type[IAuthProvider]
) -> None:
    """
    Register a custom authentication provider.

    This allows extending the authentication system with custom providers
    beyond the built-in Azure AD and Cognito implementations.

    Args:
        provider_type: Provider type identifier
        provider_class: Provider implementation class (must inherit from IAuthProvider)

    Raises:
        ValueError: If provider_class does not inherit from IAuthProvider
    """
    if not issubclass(provider_class, IAuthProvider):
        raise ValueError(
            f"Provider class must inherit from IAuthProvider. "
            f"Got: {provider_class.__name__}"
        )

    _PROVIDER_REGISTRY[provider_type] = provider_class
    logger.info(f"Registered provider: {provider_type.value} -> {provider_class.__name__}")


def get_provider_class(provider_type: AuthProvider) -> Type[IAuthProvider]:
    """
    Get provider implementation class by type.

    Args:
        provider_type: Provider type identifier

    Returns:
        Provider implementation class

    Raises:
        ProviderConfigError: If provider type is not registered
    """
    if provider_type not in _PROVIDER_REGISTRY:
        raise ProviderConfigError(
            f"Unknown provider type: {provider_type.value}",
            provider=provider_type.value
        )

    return _PROVIDER_REGISTRY[provider_type]


def create_auth_provider(config: AuthConfig) -> IAuthProvider:
    """
    Create authentication provider instance from configuration.

    This is the main factory function for creating authentication providers.
    It handles provider-specific configuration and initialization.

    Args:
        config: Authentication configuration

    Returns:
        Initialized authentication provider instance

    Raises:
        ProviderConfigError: If provider configuration is invalid

    Example:
        >>> from agent_service.auth.schemas import AuthConfig, AuthProvider, AzureADConfig
        >>>
        >>> config = AuthConfig(
        ...     provider=AuthProvider.AZURE_AD,
        ...     azure_ad=AzureADConfig(
        ...         tenant_id="your-tenant-id",
        ...         client_id="your-client-id"
        ...     )
        ... )
        >>> provider = create_auth_provider(config)
        >>> user_info = provider.get_user_info(token)
    """
    try:
        provider_class = get_provider_class(config.provider)

        # Create provider with appropriate configuration
        if config.provider == AuthProvider.AZURE_AD:
            if not config.azure_ad:
                raise ProviderConfigError(
                    "Azure AD configuration required",
                    provider="azure_ad",
                    missing_fields=["azure_ad"]
                )
            logger.info("Creating Azure AD authentication provider")
            return provider_class(config.azure_ad)

        elif config.provider == AuthProvider.AWS_COGNITO:
            if not config.cognito:
                raise ProviderConfigError(
                    "Cognito configuration required",
                    provider="aws_cognito",
                    missing_fields=["cognito"]
                )
            logger.info("Creating AWS Cognito authentication provider")
            return provider_class(config.cognito)

        else:
            # For custom providers, attempt to create with full config
            logger.info(f"Creating custom authentication provider: {config.provider.value}")
            return provider_class(config)

    except Exception as e:
        logger.error(f"Failed to create authentication provider: {str(e)}")
        if isinstance(e, ProviderConfigError):
            raise
        raise ProviderConfigError(
            f"Failed to create authentication provider: {str(e)}",
            provider=config.provider.value,
            original_error=e
        )


def list_providers() -> list[str]:
    """
    List all registered provider types.

    Returns:
        List of registered provider names
    """
    return [provider.value for provider in _PROVIDER_REGISTRY.keys()]


__all__ = [
    "IAuthProvider",
    "AzureADAuthProvider",
    "CognitoAuthProvider",
    "register_provider",
    "get_provider_class",
    "create_auth_provider",
    "list_providers",
]
