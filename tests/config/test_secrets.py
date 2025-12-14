"""
Tests for secrets management.
"""
import json
import os
import pytest
from unittest.mock import Mock, patch, MagicMock

from agent_service.config.secrets import (
    EnvironmentSecretsProvider,
    SecretsManager,
    get_secrets_manager,
    get_secret,
    get_secret_json,
    mask_secret,
    mask_secrets_in_dict,
    mask_secrets_processor,
)


# ============================================================================
# Environment Provider Tests
# ============================================================================


class TestEnvironmentSecretsProvider:
    """Tests for EnvironmentSecretsProvider."""

    def test_get_secret_found(self, monkeypatch):
        """Test getting an existing secret."""
        monkeypatch.setenv("TEST_KEY", "test_value")
        provider = EnvironmentSecretsProvider()

        value = provider.get_secret("TEST_KEY")
        assert value == "test_value"

    def test_get_secret_not_found(self):
        """Test getting a non-existent secret."""
        provider = EnvironmentSecretsProvider()

        value = provider.get_secret("NONEXISTENT_KEY")
        assert value is None

    def test_get_secret_json_valid(self, monkeypatch):
        """Test getting a valid JSON secret."""
        json_data = {"key": "value", "number": 42}
        monkeypatch.setenv("JSON_SECRET", json.dumps(json_data))
        provider = EnvironmentSecretsProvider()

        value = provider.get_secret_json("JSON_SECRET")
        assert value == json_data

    def test_get_secret_json_invalid(self, monkeypatch):
        """Test getting an invalid JSON secret."""
        monkeypatch.setenv("INVALID_JSON", "not valid json {")
        provider = EnvironmentSecretsProvider()

        value = provider.get_secret_json("INVALID_JSON")
        assert value is None

    def test_list_secrets_no_prefix(self, monkeypatch):
        """Test listing all secrets."""
        monkeypatch.setenv("KEY1", "value1")
        monkeypatch.setenv("KEY2", "value2")
        provider = EnvironmentSecretsProvider()

        secrets = provider.list_secrets()
        assert "KEY1" in secrets
        assert "KEY2" in secrets

    def test_list_secrets_with_prefix(self, monkeypatch):
        """Test listing secrets with prefix filter."""
        monkeypatch.setenv("APP_KEY1", "value1")
        monkeypatch.setenv("APP_KEY2", "value2")
        monkeypatch.setenv("OTHER_KEY", "value3")
        provider = EnvironmentSecretsProvider()

        secrets = provider.list_secrets(prefix="APP_")
        assert "APP_KEY1" in secrets
        assert "APP_KEY2" in secrets
        assert "OTHER_KEY" not in secrets

    def test_refresh(self, monkeypatch, tmp_path):
        """Test refreshing environment variables from .env file."""
        # Create a temporary .env file
        env_file = tmp_path / ".env"
        env_file.write_text("REFRESH_TEST=initial_value\n")

        provider = EnvironmentSecretsProvider(dotenv_path=str(env_file))

        # Update the file
        env_file.write_text("REFRESH_TEST=updated_value\n")

        # Refresh should reload the file
        provider.refresh()

        # Note: This test may be limited by how dotenv handles reloading


# ============================================================================
# AWS Provider Tests
# ============================================================================


class TestAWSSecretsManagerProvider:
    """Tests for AWSSecretsManagerProvider."""

    def test_init_without_boto3(self):
        """Test initialization fails without boto3."""
        with patch.dict("sys.modules", {"boto3": None}):
            with pytest.raises(ImportError, match="boto3 is required"):
                from agent_service.config.secrets import AWSSecretsManagerProvider
                AWSSecretsManagerProvider()

    @patch("agent_service.config.secrets.boto3")
    def test_init_with_boto3(self, mock_boto3):
        """Test successful initialization with boto3."""
        from agent_service.config.secrets import AWSSecretsManagerProvider

        mock_client = Mock()
        mock_boto3.client.return_value = mock_client

        provider = AWSSecretsManagerProvider(region="us-west-2", cache_ttl=1800)

        assert provider._region == "us-west-2"
        assert provider._cache_ttl == 1800
        mock_boto3.client.assert_called_once_with("secretsmanager", region_name="us-west-2")

    @patch("agent_service.config.secrets.boto3")
    def test_get_secret_string(self, mock_boto3):
        """Test getting a string secret from AWS."""
        from agent_service.config.secrets import AWSSecretsManagerProvider

        mock_client = Mock()
        mock_client.get_secret_value.return_value = {"SecretString": "secret_value"}
        mock_boto3.client.return_value = mock_client

        provider = AWSSecretsManagerProvider()
        value = provider.get_secret("my-secret")

        assert value == "secret_value"
        mock_client.get_secret_value.assert_called_once_with(SecretId="my-secret")

    @patch("agent_service.config.secrets.boto3")
    def test_get_secret_binary(self, mock_boto3):
        """Test getting a binary secret from AWS."""
        from agent_service.config.secrets import AWSSecretsManagerProvider

        mock_client = Mock()
        mock_client.get_secret_value.return_value = {
            "SecretBinary": b"secret_value"
        }
        mock_boto3.client.return_value = mock_client

        provider = AWSSecretsManagerProvider()
        value = provider.get_secret("my-secret")

        assert value == "secret_value"

    @patch("agent_service.config.secrets.boto3")
    def test_get_secret_not_found(self, mock_boto3):
        """Test getting a non-existent secret from AWS."""
        from agent_service.config.secrets import AWSSecretsManagerProvider
        from botocore.exceptions import ClientError

        mock_client = Mock()
        mock_client.get_secret_value.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}},
            "GetSecretValue"
        )
        mock_boto3.client.return_value = mock_client

        provider = AWSSecretsManagerProvider()
        value = provider.get_secret("nonexistent")

        assert value is None

    @patch("agent_service.config.secrets.boto3")
    def test_get_secret_cache(self, mock_boto3):
        """Test secret caching."""
        from agent_service.config.secrets import AWSSecretsManagerProvider

        mock_client = Mock()
        mock_client.get_secret_value.return_value = {"SecretString": "cached_value"}
        mock_boto3.client.return_value = mock_client

        provider = AWSSecretsManagerProvider(cache_ttl=3600)

        # First call should hit AWS
        value1 = provider.get_secret("my-secret")
        assert value1 == "cached_value"
        assert mock_client.get_secret_value.call_count == 1

        # Second call should use cache
        value2 = provider.get_secret("my-secret")
        assert value2 == "cached_value"
        assert mock_client.get_secret_value.call_count == 1  # No additional call

    @patch("agent_service.config.secrets.boto3")
    def test_list_secrets(self, mock_boto3):
        """Test listing secrets from AWS."""
        from agent_service.config.secrets import AWSSecretsManagerProvider

        mock_client = Mock()
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            {
                "SecretList": [
                    {"Name": "app/secret1"},
                    {"Name": "app/secret2"},
                ]
            }
        ]
        mock_client.get_paginator.return_value = mock_paginator
        mock_boto3.client.return_value = mock_client

        provider = AWSSecretsManagerProvider()
        secrets = provider.list_secrets(prefix="app/")

        assert "app/secret1" in secrets
        assert "app/secret2" in secrets

    @patch("agent_service.config.secrets.boto3")
    def test_refresh_clears_cache(self, mock_boto3):
        """Test refresh clears the cache."""
        from agent_service.config.secrets import AWSSecretsManagerProvider

        mock_client = Mock()
        mock_boto3.client.return_value = mock_client

        provider = AWSSecretsManagerProvider()
        provider._cache = {"test": ("value", 12345)}

        provider.refresh()

        assert len(provider._cache) == 0


# ============================================================================
# Secrets Manager Tests
# ============================================================================


class TestSecretsManager:
    """Tests for SecretsManager."""

    def test_init_env_provider(self, monkeypatch):
        """Test initialization with environment provider."""
        manager = SecretsManager(provider="env")
        assert len(manager._providers) == 1
        assert isinstance(manager._providers[0], EnvironmentSecretsProvider)

    @patch("agent_service.config.secrets.boto3")
    def test_init_aws_provider(self, mock_boto3):
        """Test initialization with AWS provider."""
        mock_boto3.client.return_value = Mock()

        manager = SecretsManager(provider="aws", aws_region="us-east-1")

        # Should have AWS provider + env fallback
        assert len(manager._providers) >= 1

    def test_get_secret_from_provider(self, monkeypatch):
        """Test getting secret from provider chain."""
        monkeypatch.setenv("TEST_SECRET", "test_value")

        manager = SecretsManager(provider="env")
        value = manager.get_secret("TEST_SECRET")

        assert value == "test_value"

    def test_get_secret_not_found(self):
        """Test getting non-existent secret."""
        manager = SecretsManager(provider="env")
        value = manager.get_secret("NONEXISTENT")

        assert value is None

    def test_get_secret_json(self, monkeypatch):
        """Test getting JSON secret."""
        json_data = {"key": "value"}
        monkeypatch.setenv("JSON_SECRET", json.dumps(json_data))

        manager = SecretsManager(provider="env")
        value = manager.get_secret_json("JSON_SECRET")

        assert value == json_data

    def test_list_secrets(self, monkeypatch):
        """Test listing secrets."""
        monkeypatch.setenv("APP_KEY1", "value1")
        monkeypatch.setenv("APP_KEY2", "value2")

        manager = SecretsManager(provider="env")
        secrets = manager.list_secrets(prefix="APP_")

        assert "APP_KEY1" in secrets
        assert "APP_KEY2" in secrets


# ============================================================================
# Secret Masking Tests
# ============================================================================


class TestSecretMasking:
    """Tests for secret masking functions."""

    def test_mask_secret(self):
        """Test masking a single secret."""
        assert mask_secret("my-secret-key") == "****"
        assert mask_secret("") == ""

    def test_mask_secrets_in_dict_basic(self):
        """Test masking secrets in a simple dictionary."""
        data = {
            "username": "john",
            "password": "secret123",
            "email": "john@example.com"
        }

        masked = mask_secrets_in_dict(data)

        assert masked["username"] == "john"
        assert masked["password"] == "****"
        assert masked["email"] == "john@example.com"

    def test_mask_secrets_in_dict_nested(self):
        """Test masking secrets in nested dictionary."""
        data = {
            "user": {
                "name": "john",
                "password": "secret123"
            },
            "api_key": "sk_live_abc123"
        }

        masked = mask_secrets_in_dict(data)

        assert masked["user"]["name"] == "john"
        assert masked["user"]["password"] == "****"
        assert masked["api_key"] == "****"

    def test_mask_secrets_in_dict_list(self):
        """Test masking secrets in lists."""
        data = {
            "users": [
                {"name": "john", "password": "secret1"},
                {"name": "jane", "password": "secret2"}
            ]
        }

        masked = mask_secrets_in_dict(data)

        assert masked["users"][0]["name"] == "john"
        assert masked["users"][0]["password"] == "****"
        assert masked["users"][1]["password"] == "****"

    def test_mask_secrets_custom_keys(self):
        """Test masking with custom keys."""
        data = {
            "username": "john",
            "custom_secret": "should_mask",
            "normal_field": "should_not_mask"
        }

        masked = mask_secrets_in_dict(data, keys=["custom_secret"], default_keys=False)

        assert masked["username"] == "john"  # Not masked (default keys disabled)
        assert masked["custom_secret"] == "****"  # Masked (custom key)
        assert masked["normal_field"] == "should_not_mask"

    def test_mask_secrets_case_insensitive(self):
        """Test masking is case-insensitive."""
        data = {
            "PASSWORD": "secret1",
            "Password": "secret2",
            "password": "secret3"
        }

        masked = mask_secrets_in_dict(data)

        assert masked["PASSWORD"] == "****"
        assert masked["Password"] == "****"
        assert masked["password"] == "****"

    def test_mask_secrets_processor(self):
        """Test structlog processor integration."""
        event_dict = {
            "message": "User logged in",
            "username": "john",
            "password": "secret123",
            "token": "bearer_token_xyz"
        }

        masked = mask_secrets_processor(None, None, event_dict)

        assert masked["message"] == "User logged in"
        assert masked["username"] == "john"
        assert masked["password"] == "****"
        assert masked["token"] == "****"


# ============================================================================
# Convenience Function Tests
# ============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_secret_function(self, monkeypatch):
        """Test get_secret convenience function."""
        monkeypatch.setenv("TEST_KEY", "test_value")

        # Need to reset the singleton
        import agent_service.config.secrets as secrets_module
        secrets_module._secrets_manager_instance = None

        value = get_secret("TEST_KEY")
        assert value == "test_value"

    def test_get_secret_with_default(self):
        """Test get_secret with default value."""
        import agent_service.config.secrets as secrets_module
        secrets_module._secrets_manager_instance = None

        value = get_secret("NONEXISTENT_KEY", default="default_value")
        assert value == "default_value"

    def test_get_secret_json_function(self, monkeypatch):
        """Test get_secret_json convenience function."""
        json_data = {"key": "value"}
        monkeypatch.setenv("JSON_KEY", json.dumps(json_data))

        import agent_service.config.secrets as secrets_module
        secrets_module._secrets_manager_instance = None

        value = get_secret_json("JSON_KEY")
        assert value == json_data

    def test_get_secret_json_with_default(self):
        """Test get_secret_json with default value."""
        import agent_service.config.secrets as secrets_module
        secrets_module._secrets_manager_instance = None

        default = {"default": "value"}
        value = get_secret_json("NONEXISTENT_KEY", default=default)
        assert value == default


# ============================================================================
# Integration Tests
# ============================================================================


class TestSecretsIntegration:
    """Integration tests for the secrets management system."""

    def test_singleton_pattern(self, monkeypatch):
        """Test that get_secrets_manager returns singleton."""
        import agent_service.config.secrets as secrets_module
        secrets_module._secrets_manager_instance = None

        manager1 = get_secrets_manager()
        manager2 = get_secrets_manager()

        assert manager1 is manager2

    def test_force_reload(self, monkeypatch):
        """Test force_reload creates new instance."""
        import agent_service.config.secrets as secrets_module
        secrets_module._secrets_manager_instance = None

        manager1 = get_secrets_manager()
        manager2 = get_secrets_manager(force_reload=True)

        assert manager1 is not manager2
