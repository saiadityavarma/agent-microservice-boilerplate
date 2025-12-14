"""
Unit tests for authentication providers.

Tests cover:
- Azure AD token parsing (with MSAL mocking)
- Cognito token parsing (with boto3 mocking)
- Token validation caching
- Error handling for invalid tokens
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timedelta

from agent_service.auth.providers.azure_ad import AzureADAuthProvider
from agent_service.auth.providers.aws_cognito import CognitoAuthProvider
from agent_service.auth.schemas import (
    AzureADConfig,
    CognitoConfig,
    TokenPayload,
    UserInfo,
    AuthProvider,
)
from agent_service.auth.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
    AuthenticationError,
    ProviderConfigError,
)


# ============================================================================
# Azure AD Provider Tests
# ============================================================================


@pytest.fixture
def azure_config():
    """Create Azure AD configuration for testing."""
    return AzureADConfig(
        tenant_id="test-tenant-id",
        client_id="test-client-id",
        client_secret="test-client-secret",
        cache_ttl=300,
    )


@pytest.fixture
def mock_oidc_config():
    """Mock OIDC configuration response."""
    return {
        "issuer": "https://login.microsoftonline.com/test-tenant-id/v2.0",
        "jwks_uri": "https://login.microsoftonline.com/test-tenant-id/discovery/v2.0/keys",
        "authorization_endpoint": "https://login.microsoftonline.com/test-tenant-id/oauth2/v2.0/authorize",
        "token_endpoint": "https://login.microsoftonline.com/test-tenant-id/oauth2/v2.0/token",
    }


@pytest.fixture
def mock_jwks():
    """Mock JWKS (JSON Web Key Set) response."""
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "kid": "test-key-id",
                "n": "test-modulus",
                "e": "AQAB",
            }
        ]
    }


@pytest.fixture
def valid_token_claims():
    """Valid token claims for testing."""
    exp_time = int((datetime.utcnow() + timedelta(hours=1)).timestamp())
    iat_time = int(datetime.utcnow().timestamp())

    return {
        "sub": "user-123",
        "exp": exp_time,
        "iat": iat_time,
        "iss": "https://login.microsoftonline.com/test-tenant-id/v2.0",
        "aud": "test-client-id",
        "roles": ["admin", "user"],
        "groups": ["group-1", "group-2"],
        "email": "user@example.com",
        "name": "Test User",
        "tid": "test-tenant-id",
    }


class TestAzureADProviderConfiguration:
    """Test Azure AD provider configuration and initialization."""

    def test_azure_provider_initialization(self, azure_config):
        """Test successful Azure AD provider initialization."""
        with patch("requests.get") as mock_get:
            mock_get.return_value.json.return_value = {
                "jwks_uri": "https://example.com/keys"
            }

            provider = AzureADAuthProvider(azure_config)

            assert provider.config == azure_config
            assert provider.get_provider_name() == "azure_ad"

    def test_azure_provider_missing_tenant_id(self):
        """Test that missing tenant_id raises error."""
        config = AzureADConfig(
            tenant_id="",
            client_id="test-client-id",
        )

        with pytest.raises(ProviderConfigError, match="incomplete"):
            with patch("requests.get"):
                AzureADAuthProvider(config)

    def test_azure_provider_missing_client_id(self):
        """Test that missing client_id raises error."""
        config = AzureADConfig(
            tenant_id="test-tenant-id",
            client_id="",
        )

        with pytest.raises(ProviderConfigError, match="incomplete"):
            with patch("requests.get"):
                AzureADAuthProvider(config)

    def test_azure_provider_oidc_discovery_failure(self, azure_config):
        """Test OIDC discovery failure handling."""
        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("Network error")

            with pytest.raises(ProviderConfigError, match="OIDC discovery"):
                AzureADAuthProvider(azure_config)


class TestAzureADTokenParsing:
    """Test Azure AD token parsing and validation."""

    @patch("agent_service.auth.providers.azure_ad.jwt")
    @patch("requests.get")
    def test_azure_verify_token_success(
        self, mock_get, mock_jwt, azure_config, valid_token_claims
    ):
        """Test successful token verification."""
        # Mock OIDC discovery
        mock_get.return_value.json.return_value = {
            "jwks_uri": "https://example.com/keys"
        }
        mock_get.return_value.status_code = 200

        provider = AzureADAuthProvider(azure_config)

        # Mock JWT operations
        mock_jwt.get_unverified_header.return_value = {"kid": "test-key-id"}
        mock_jwt.PyJWK.return_value.key = "test-signing-key"
        mock_jwt.decode.return_value = valid_token_claims

        # Mock JWKS fetch
        with patch.object(provider, "_get_signing_key") as mock_signing_key:
            mock_signing_key.return_value = Mock(key="test-key")

            token_payload = provider.verify_token("test.jwt.token")

            assert isinstance(token_payload, TokenPayload)
            assert token_payload.sub == "user-123"
            assert token_payload.email == "user@example.com"
            assert "admin" in token_payload.roles
            assert "group-1" in token_payload.groups

    @patch("agent_service.auth.providers.azure_ad.jwt")
    @patch("requests.get")
    def test_azure_verify_expired_token(self, mock_get, mock_jwt, azure_config):
        """Test that expired token raises TokenExpiredError."""
        # Mock OIDC discovery
        mock_get.return_value.json.return_value = {
            "jwks_uri": "https://example.com/keys"
        }

        provider = AzureADAuthProvider(azure_config)

        # Mock JWT to raise ExpiredSignatureError
        mock_jwt.get_unverified_header.return_value = {"kid": "test-key-id"}
        mock_jwt.decode.side_effect = mock_jwt.ExpiredSignatureError("Token expired")

        with patch.object(provider, "_get_signing_key"):
            with pytest.raises(TokenExpiredError, match="expired"):
                provider.verify_token("expired.jwt.token")

    @patch("agent_service.auth.providers.azure_ad.jwt")
    @patch("requests.get")
    def test_azure_verify_invalid_token(self, mock_get, mock_jwt, azure_config):
        """Test that invalid token raises InvalidTokenError."""
        mock_get.return_value.json.return_value = {
            "jwks_uri": "https://example.com/keys"
        }

        provider = AzureADAuthProvider(azure_config)

        mock_jwt.get_unverified_header.return_value = {"kid": "test-key-id"}
        mock_jwt.decode.side_effect = mock_jwt.InvalidTokenError("Invalid token")

        with patch.object(provider, "_get_signing_key"):
            with pytest.raises(InvalidTokenError, match="Invalid"):
                provider.verify_token("invalid.jwt.token")

    @patch("agent_service.auth.providers.azure_ad.jwt")
    @patch("requests.get")
    def test_azure_get_user_info(
        self, mock_get, mock_jwt, azure_config, valid_token_claims
    ):
        """Test extracting user info from Azure AD token."""
        mock_get.return_value.json.return_value = {
            "jwks_uri": "https://example.com/keys"
        }

        provider = AzureADAuthProvider(azure_config)

        mock_jwt.get_unverified_header.return_value = {"kid": "test-key-id"}
        mock_jwt.decode.return_value = valid_token_claims

        with patch.object(provider, "_get_signing_key"):
            user_info = provider.get_user_info("test.jwt.token")

            assert isinstance(user_info, UserInfo)
            assert user_info.id == "user-123"
            assert user_info.email == "user@example.com"
            assert user_info.name == "Test User"
            assert user_info.provider == AuthProvider.AZURE_AD
            assert user_info.tenant_id == "test-tenant-id"
            assert "admin" in user_info.roles
            assert "group-1" in user_info.groups


class TestAzureADTokenCaching:
    """Test Azure AD token validation caching."""

    @patch("agent_service.auth.providers.azure_ad.jwt")
    @patch("requests.get")
    def test_azure_token_cache_hit(
        self, mock_get, mock_jwt, azure_config, valid_token_claims
    ):
        """Test that token validation is cached."""
        mock_get.return_value.json.return_value = {
            "jwks_uri": "https://example.com/keys"
        }

        provider = AzureADAuthProvider(azure_config)

        mock_jwt.get_unverified_header.return_value = {"kid": "test-key-id"}
        mock_jwt.decode.return_value = valid_token_claims

        with patch.object(provider, "_get_signing_key") as mock_signing_key:
            mock_signing_key.return_value = Mock(key="test-key")

            # First call - should hit the real validation
            provider.verify_token("test.jwt.token")
            first_call_count = mock_jwt.decode.call_count

            # Second call with same token - should use cache
            provider.verify_token("test.jwt.token")
            second_call_count = mock_jwt.decode.call_count

            # Cache should prevent second decode call
            assert second_call_count == first_call_count

    @patch("requests.get")
    def test_azure_signing_key_cache(self, mock_get, azure_config):
        """Test that signing keys are cached."""
        mock_get.return_value.json.return_value = {
            "jwks_uri": "https://example.com/keys"
        }

        provider = AzureADAuthProvider(azure_config)

        # Mock JWKS response
        jwks_response = {
            "keys": [{"kid": "test-key-id", "kty": "RSA", "use": "sig"}]
        }

        with patch("requests.get") as mock_jwks_get:
            mock_jwks_get.return_value.json.return_value = jwks_response
            mock_jwks_get.return_value.status_code = 200

            with patch("agent_service.auth.providers.azure_ad.jwt.PyJWK") as mock_pyjwk:
                mock_pyjwk.return_value = Mock(key="cached-key")

                # First call
                provider._get_signing_key("test-key-id")
                first_calls = mock_jwks_get.call_count

                # Second call - should use cache
                provider._get_signing_key("test-key-id")
                second_calls = mock_jwks_get.call_count

                # Should not make additional JWKS request
                assert second_calls == first_calls


# ============================================================================
# AWS Cognito Provider Tests
# ============================================================================


@pytest.fixture
def cognito_config():
    """Create Cognito configuration for testing."""
    return CognitoConfig(
        region="us-east-1",
        user_pool_id="us-east-1_TestPool",
        client_id="test-cognito-client-id",
        client_secret="test-cognito-secret",
        jwks_cache_ttl=300,
    )


@pytest.fixture
def cognito_token_claims():
    """Valid Cognito token claims."""
    exp_time = int((datetime.utcnow() + timedelta(hours=1)).timestamp())
    iat_time = int(datetime.utcnow().timestamp())

    return {
        "sub": "cognito-user-456",
        "exp": exp_time,
        "iat": iat_time,
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_TestPool",
        "aud": "test-cognito-client-id",
        "token_use": "id",
        "cognito:groups": ["developers", "users"],
        "custom:roles": "admin,developer",
        "email": "cognito@example.com",
        "cognito:username": "cognitouser",
    }


class TestCognitoProviderConfiguration:
    """Test Cognito provider configuration and initialization."""

    @patch("boto3.client")
    def test_cognito_provider_initialization(self, mock_boto_client, cognito_config):
        """Test successful Cognito provider initialization."""
        provider = CognitoAuthProvider(cognito_config)

        assert provider.config == cognito_config
        assert provider.get_provider_name() == "aws_cognito"
        mock_boto_client.assert_called_once_with(
            "cognito-idp", region_name="us-east-1"
        )

    def test_cognito_provider_missing_region(self):
        """Test that missing region raises error."""
        config = CognitoConfig(
            region="",
            user_pool_id="test-pool",
            client_id="test-client",
        )

        with pytest.raises(ProviderConfigError, match="incomplete"):
            with patch("boto3.client"):
                CognitoAuthProvider(config)

    def test_cognito_provider_missing_pool_id(self):
        """Test that missing user_pool_id raises error."""
        config = CognitoConfig(
            region="us-east-1",
            user_pool_id="",
            client_id="test-client",
        )

        with pytest.raises(ProviderConfigError, match="incomplete"):
            with patch("boto3.client"):
                CognitoAuthProvider(config)


class TestCognitoTokenParsing:
    """Test Cognito token parsing and validation."""

    @patch("agent_service.auth.providers.aws_cognito.jwt")
    @patch("requests.get")
    @patch("boto3.client")
    def test_cognito_verify_token_success(
        self, mock_boto, mock_get, mock_jwt, cognito_config, cognito_token_claims
    ):
        """Test successful Cognito token verification."""
        provider = CognitoAuthProvider(cognito_config)

        # Mock JWKS
        mock_get.return_value.json.return_value = {
            "keys": [{"kid": "cognito-key-id"}]
        }
        mock_get.return_value.status_code = 200

        # Mock JWT operations
        mock_jwt.get_unverified_header.return_value = {"kid": "cognito-key-id"}
        mock_jwt.decode.return_value = cognito_token_claims

        with patch.object(provider, "_get_signing_key") as mock_key:
            mock_key.return_value = {"kid": "cognito-key-id"}

            token_payload = provider.verify_token("cognito.jwt.token")

            assert isinstance(token_payload, TokenPayload)
            assert token_payload.sub == "cognito-user-456"
            assert token_payload.email == "cognito@example.com"
            assert "developers" in token_payload.groups
            assert "admin" in token_payload.roles

    @patch("agent_service.auth.providers.aws_cognito.jwt")
    @patch("boto3.client")
    def test_cognito_verify_expired_token(self, mock_boto, mock_jwt, cognito_config):
        """Test that expired Cognito token raises TokenExpiredError."""
        provider = CognitoAuthProvider(cognito_config)

        mock_jwt.get_unverified_header.return_value = {"kid": "cognito-key-id"}
        mock_jwt.decode.side_effect = mock_jwt.ExpiredSignatureError("Token expired")

        with patch.object(provider, "_get_jwks"), patch.object(
            provider, "_get_signing_key"
        ):
            with pytest.raises(TokenExpiredError, match="expired"):
                provider.verify_token("expired.cognito.token")

    @patch("agent_service.auth.providers.aws_cognito.jwt")
    @patch("boto3.client")
    def test_cognito_verify_invalid_token_use(
        self, mock_boto, mock_jwt, cognito_config, cognito_token_claims
    ):
        """Test that token with wrong token_use is rejected."""
        provider = CognitoAuthProvider(cognito_config)

        # Set wrong token_use
        claims = cognito_token_claims.copy()
        claims["token_use"] = "access"  # Should be "id"

        mock_jwt.get_unverified_header.return_value = {"kid": "cognito-key-id"}
        mock_jwt.decode.return_value = claims

        with patch.object(provider, "_get_signing_key"):
            with pytest.raises(InvalidTokenError, match="token_use"):
                provider.verify_token("wrong.token.use")

    @patch("agent_service.auth.providers.aws_cognito.jwt")
    @patch("requests.get")
    @patch("boto3.client")
    def test_cognito_get_user_info(
        self, mock_boto, mock_get, mock_jwt, cognito_config, cognito_token_claims
    ):
        """Test extracting user info from Cognito token."""
        provider = CognitoAuthProvider(cognito_config)

        mock_get.return_value.json.return_value = {
            "keys": [{"kid": "cognito-key-id"}]
        }
        mock_jwt.get_unverified_header.return_value = {"kid": "cognito-key-id"}
        mock_jwt.decode.return_value = cognito_token_claims

        with patch.object(provider, "_get_signing_key"):
            user_info = provider.get_user_info("cognito.jwt.token")

            assert isinstance(user_info, UserInfo)
            assert user_info.id == "cognito-user-456"
            assert user_info.email == "cognito@example.com"
            assert user_info.provider == AuthProvider.AWS_COGNITO
            assert "developers" in user_info.groups
            assert "admin" in user_info.roles


class TestCognitoTokenCaching:
    """Test Cognito token validation caching."""

    @patch("agent_service.auth.providers.aws_cognito.jwt")
    @patch("requests.get")
    @patch("boto3.client")
    def test_cognito_token_cache(
        self, mock_boto, mock_get, mock_jwt, cognito_config, cognito_token_claims
    ):
        """Test that Cognito token validation is cached."""
        provider = CognitoAuthProvider(cognito_config)

        mock_get.return_value.json.return_value = {
            "keys": [{"kid": "cognito-key-id"}]
        }
        mock_jwt.get_unverified_header.return_value = {"kid": "cognito-key-id"}
        mock_jwt.decode.return_value = cognito_token_claims

        with patch.object(provider, "_get_signing_key"):
            # First call
            provider.verify_token("cognito.jwt.token")
            first_calls = mock_jwt.decode.call_count

            # Second call - should use cache
            provider.verify_token("cognito.jwt.token")
            second_calls = mock_jwt.decode.call_count

            # Cache should prevent second decode
            assert second_calls == first_calls

    @patch("requests.get")
    @patch("boto3.client")
    def test_cognito_jwks_cache(self, mock_boto, mock_get, cognito_config):
        """Test that JWKS is cached for Cognito."""
        provider = CognitoAuthProvider(cognito_config)

        mock_get.return_value.json.return_value = {
            "keys": [{"kid": "test-key"}]
        }
        mock_get.return_value.status_code = 200

        # First call
        provider._get_jwks()
        first_calls = mock_get.call_count

        # Second call - should use cache
        provider._get_jwks()
        second_calls = mock_get.call_count

        # Should not make additional request
        assert second_calls == first_calls


class TestCognitoGroupOperations:
    """Test Cognito-specific group operations."""

    @patch("boto3.client")
    def test_cognito_get_user_groups(self, mock_boto_client, cognito_config):
        """Test fetching user groups from Cognito."""
        mock_cognito = MagicMock()
        mock_boto_client.return_value = mock_cognito

        provider = CognitoAuthProvider(cognito_config)

        # Mock admin_list_groups_for_user response
        mock_cognito.admin_list_groups_for_user.return_value = {
            "Groups": [
                {"GroupName": "developers"},
                {"GroupName": "admins"},
            ]
        }

        groups = provider.get_user_groups("testuser")

        assert "developers" in groups
        assert "admins" in groups
        assert len(groups) == 2

        mock_cognito.admin_list_groups_for_user.assert_called_once_with(
            Username="testuser", UserPoolId="us-east-1_TestPool"
        )

    @patch("boto3.client")
    def test_cognito_get_user_groups_error(self, mock_boto_client, cognito_config):
        """Test error handling when fetching user groups fails."""
        mock_cognito = MagicMock()
        mock_boto_client.return_value = mock_cognito

        provider = CognitoAuthProvider(cognito_config)

        mock_cognito.admin_list_groups_for_user.side_effect = Exception("API Error")

        with pytest.raises(AuthenticationError, match="retrieve user groups"):
            provider.get_user_groups("testuser")


class TestProviderErrorHandling:
    """Test error handling across providers."""

    @patch("requests.get")
    def test_azure_network_error_on_jwks(self, mock_get, azure_config):
        """Test handling of network errors when fetching JWKS."""
        mock_get.return_value.json.return_value = {
            "jwks_uri": "https://example.com/keys"
        }

        provider = AzureADAuthProvider(azure_config)

        # Mock network error on JWKS fetch
        with patch.object(provider, "_jwks_uri", "https://example.com/keys"):
            with patch("requests.get") as mock_jwks_get:
                mock_jwks_get.side_effect = Exception("Network error")

                with pytest.raises(InvalidTokenError, match="retrieve signing keys"):
                    provider._get_signing_key("test-key-id")

    @patch("requests.get")
    @patch("boto3.client")
    def test_cognito_network_error_on_jwks(self, mock_boto, mock_get, cognito_config):
        """Test handling of network errors when fetching Cognito JWKS."""
        provider = CognitoAuthProvider(cognito_config)

        mock_get.side_effect = Exception("Network error")

        with pytest.raises(InvalidTokenError, match="retrieve JWKS"):
            provider._get_jwks()

    @patch("agent_service.auth.providers.azure_ad.jwt")
    @patch("requests.get")
    def test_azure_missing_kid_in_token(self, mock_get, mock_jwt, azure_config):
        """Test handling of tokens without kid in header."""
        mock_get.return_value.json.return_value = {
            "jwks_uri": "https://example.com/keys"
        }

        provider = AzureADAuthProvider(azure_config)

        # Mock token without kid
        mock_jwt.get_unverified_header.return_value = {}

        with pytest.raises(InvalidTokenError, match="missing 'kid'"):
            provider.verify_token("token.without.kid")

    @patch("agent_service.auth.providers.aws_cognito.jwt")
    @patch("boto3.client")
    def test_cognito_missing_kid_in_token(self, mock_boto, mock_jwt, cognito_config):
        """Test handling of Cognito tokens without kid."""
        provider = CognitoAuthProvider(cognito_config)

        mock_jwt.get_unverified_header.return_value = {}

        with pytest.raises(InvalidTokenError, match="missing 'kid'"):
            provider.verify_token("token.without.kid")
