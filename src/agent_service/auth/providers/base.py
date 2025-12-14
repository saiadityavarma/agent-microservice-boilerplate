"""
Abstract base class for authentication providers.

This module defines the interface that all authentication providers must implement,
ensuring consistent behavior across different identity providers.
"""

from abc import ABC, abstractmethod
from typing import Optional

from ..schemas import TokenPayload, TokenResponse, UserInfo


class IAuthProvider(ABC):
    """
    Abstract base class for authentication providers.

    All authentication providers must implement this interface to ensure
    consistent token verification and user information retrieval.
    """

    @abstractmethod
    def verify_token(self, token: str) -> TokenPayload:
        """
        Verify and decode a JWT token.

        This method validates the token signature, expiration, issuer, and audience,
        then returns the decoded token payload.

        Args:
            token: JWT token string to verify

        Returns:
            TokenPayload containing the decoded and validated token claims

        Raises:
            InvalidTokenError: If token is malformed or signature is invalid
            TokenExpiredError: If token has expired
            AuthenticationError: If token validation fails for any other reason
        """
        pass

    @abstractmethod
    def get_user_info(self, token: str) -> UserInfo:
        """
        Extract user information from a JWT token.

        This method verifies the token and extracts user identity, roles, groups,
        and other relevant information for authorization.

        Args:
            token: JWT token string to extract user information from

        Returns:
            UserInfo containing user identity and authorization data

        Raises:
            InvalidTokenError: If token is malformed or signature is invalid
            TokenExpiredError: If token has expired
            AuthenticationError: If token validation fails for any other reason
        """
        pass

    def refresh_token(self, refresh_token: str) -> TokenResponse:
        """
        Refresh an access token using a refresh token.

        This is an optional method that providers can implement if they support
        token refresh. The default implementation raises NotImplementedError.

        Args:
            refresh_token: Refresh token string to exchange for new access token

        Returns:
            TokenResponse containing new access token and metadata

        Raises:
            NotImplementedError: If the provider does not support token refresh
            InvalidTokenError: If refresh token is invalid
            AuthenticationError: If token refresh fails for any other reason
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support token refresh"
        )

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of this authentication provider.

        Returns:
            Provider name (e.g., 'azure_ad', 'aws_cognito')
        """
        pass

    def validate_configuration(self) -> None:
        """
        Validate the provider configuration.

        This method can be overridden by providers to perform configuration
        validation at initialization time. The default implementation does nothing.

        Raises:
            ProviderConfigError: If configuration is invalid or incomplete
        """
        pass

    def __str__(self) -> str:
        """Return string representation of the provider."""
        return f"{self.__class__.__name__}(provider={self.get_provider_name()})"

    def __repr__(self) -> str:
        """Return detailed string representation of the provider."""
        return self.__str__()
