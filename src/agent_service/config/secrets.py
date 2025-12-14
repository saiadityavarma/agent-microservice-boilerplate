"""
Secrets management with multiple provider support.

This module provides a flexible secrets management system with support for:
- Environment variables (default)
- AWS Secrets Manager
- Secret masking for logs

Usage:
    from agent_service.config.secrets import get_secrets_manager

    secrets = get_secrets_manager()
    api_key = secrets.get_secret("API_KEY")
    db_config = secrets.get_secret_json("DATABASE_CONFIG")
"""
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any, Literal
import json
import os
import time
from dotenv import load_dotenv


def _get_logger():
    """Lazy import of logger to avoid circular dependencies."""
    try:
        from agent_service.infrastructure.observability.logging import get_logger
        return get_logger(__name__)
    except ImportError:
        # Fallback to a simple logger if structlog not available
        import logging
        return logging.getLogger(__name__)


# ============================================================================
# Abstract Base Class
# ============================================================================


class ISecretsProvider(ABC):
    """Abstract base class for secrets providers."""

    @abstractmethod
    def get_secret(self, key: str) -> str | None:
        """
        Get a secret value by key.

        Args:
            key: The secret key/name

        Returns:
            Secret value or None if not found
        """
        pass

    @abstractmethod
    def get_secret_json(self, key: str) -> dict | None:
        """
        Get a secret value as parsed JSON.

        Args:
            key: The secret key/name

        Returns:
            Parsed JSON dict or None if not found or invalid JSON
        """
        pass

    @abstractmethod
    def list_secrets(self, prefix: str = "") -> list[str]:
        """
        List all secret keys with optional prefix filter.

        Args:
            prefix: Optional prefix to filter secrets

        Returns:
            List of secret keys
        """
        pass

    @abstractmethod
    def refresh(self) -> None:
        """Reload/refresh secrets if cached."""
        pass


# ============================================================================
# Environment Variables Provider
# ============================================================================


class EnvironmentSecretsProvider(ISecretsProvider):
    """
    Secrets provider that reads from environment variables.

    Supports:
    - Standard environment variables
    - .env files via python-dotenv
    - Prefix-based secret listing
    """

    def __init__(self, dotenv_path: str | None = None):
        """
        Initialize the environment secrets provider.

        Args:
            dotenv_path: Optional path to .env file (defaults to .env in current directory)
        """
        self._dotenv_path = dotenv_path or ".env"
        self._load_dotenv()
        _get_logger().info("Initialized environment secrets provider", dotenv_path=self._dotenv_path)

    def _load_dotenv(self) -> None:
        """Load environment variables from .env file if it exists."""
        if os.path.exists(self._dotenv_path):
            load_dotenv(self._dotenv_path, override=False)
            _get_logger().debug("Loaded environment variables from .env file", path=self._dotenv_path)

    def get_secret(self, key: str) -> str | None:
        """Get a secret from environment variables."""
        value = os.getenv(key)
        if value is not None:
            _get_logger().debug("Retrieved secret from environment", key=key, found=True)
        else:
            _get_logger().debug("Secret not found in environment", key=key, found=False)
        return value

    def get_secret_json(self, key: str) -> dict | None:
        """Get a secret from environment and parse as JSON."""
        value = self.get_secret(key)
        if value is None:
            return None

        try:
            parsed = json.loads(value)
            _get_logger().debug("Parsed secret as JSON", key=key, success=True)
            return parsed
        except json.JSONDecodeError as e:
            _get_logger().warning("Failed to parse secret as JSON", key=key, error=str(e))
            return None

    def list_secrets(self, prefix: str = "") -> list[str]:
        """
        List all environment variables with optional prefix filter.

        Args:
            prefix: Filter variables that start with this prefix

        Returns:
            List of matching environment variable names
        """
        all_vars = list(os.environ.keys())
        if prefix:
            filtered = [var for var in all_vars if var.startswith(prefix)]
            _get_logger().debug("Listed secrets with prefix", prefix=prefix, count=len(filtered))
            return filtered
        _get_logger().debug("Listed all secrets", count=len(all_vars))
        return all_vars

    def refresh(self) -> None:
        """Reload environment variables from .env file."""
        self._load_dotenv()
        _get_logger().info("Refreshed environment variables")


# ============================================================================
# AWS Secrets Manager Provider
# ============================================================================


class AWSSecretsManagerProvider(ISecretsProvider):
    """
    Secrets provider that fetches secrets from AWS Secrets Manager.

    Features:
    - Automatic caching with configurable TTL
    - Automatic refresh when cache expires
    - Support for both string and JSON secrets
    - Regional configuration
    """

    def __init__(self, region: str | None = None, cache_ttl: int = 3600):
        """
        Initialize AWS Secrets Manager provider.

        Args:
            region: AWS region (defaults to AWS_DEFAULT_REGION env var)
            cache_ttl: Cache time-to-live in seconds (default: 3600)

        Raises:
            ImportError: If boto3 is not installed
        """
        try:
            import boto3
            from botocore.exceptions import BotoCoreError, ClientError

            self._ClientError = ClientError
            self._BotoCoreError = BotoCoreError
        except ImportError as e:
            _get_logger().error("boto3 not installed - AWS Secrets Manager provider unavailable")
            raise ImportError(
                "boto3 is required for AWS Secrets Manager. "
                "Install with: pip install boto3 or pip install agent-service[aws]"
            ) from e

        self._region = region or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        self._cache_ttl = cache_ttl
        self._cache: dict[str, tuple[Any, float]] = {}  # {key: (value, timestamp)}

        # Initialize AWS Secrets Manager client
        self._client = boto3.client("secretsmanager", region_name=self._region)

        _get_logger().info(
            "Initialized AWS Secrets Manager provider",
            region=self._region,
            cache_ttl=cache_ttl
        )

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached value is still valid."""
        if key not in self._cache:
            return False

        _, timestamp = self._cache[key]
        age = time.time() - timestamp
        is_valid = age < self._cache_ttl

        if not is_valid:
            _get_logger().debug("Cache expired for secret", key=key, age=age, ttl=self._cache_ttl)

        return is_valid

    def _get_from_cache(self, key: str) -> Any | None:
        """Get value from cache if valid."""
        if self._is_cache_valid(key):
            value, _ = self._cache[key]
            _get_logger().debug("Retrieved secret from cache", key=key)
            return value
        return None

    def _set_cache(self, key: str, value: Any) -> None:
        """Store value in cache with current timestamp."""
        self._cache[key] = (value, time.time())
        _get_logger().debug("Cached secret", key=key, ttl=self._cache_ttl)

    def get_secret(self, key: str) -> str | None:
        """
        Get a secret from AWS Secrets Manager.

        Args:
            key: Secret name/ARN

        Returns:
            Secret value or None if not found
        """
        # Check cache first
        cached = self._get_from_cache(key)
        if cached is not None:
            return cached

        try:
            response = self._client.get_secret_value(SecretId=key)

            # Secrets can be stored as SecretString or SecretBinary
            if "SecretString" in response:
                value = response["SecretString"]
            else:
                # For binary secrets, decode as UTF-8
                value = response["SecretBinary"].decode("utf-8")

            self._set_cache(key, value)
            _get_logger().info("Retrieved secret from AWS Secrets Manager", key=key)
            return value

        except self._ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")

            if error_code == "ResourceNotFoundException":
                _get_logger().warning("Secret not found in AWS Secrets Manager", key=key)
            else:
                _get_logger().error(
                    "Failed to retrieve secret from AWS Secrets Manager",
                    key=key,
                    error_code=error_code,
                    error=str(e)
                )
            return None

        except self._BotoCoreError as e:
            _get_logger().error(
                "AWS Secrets Manager connection error",
                key=key,
                error=str(e)
            )
            return None
        except Exception as e:
            _get_logger().error(
                "Unexpected error retrieving secret from AWS",
                key=key,
                error=str(e)
            )
            return None

    def get_secret_json(self, key: str) -> dict | None:
        """
        Get a secret from AWS Secrets Manager and parse as JSON.

        Args:
            key: Secret name/ARN

        Returns:
            Parsed JSON dict or None if not found or invalid JSON
        """
        value = self.get_secret(key)
        if value is None:
            return None

        try:
            parsed = json.loads(value)
            _get_logger().debug("Parsed AWS secret as JSON", key=key, success=True)
            return parsed
        except json.JSONDecodeError as e:
            _get_logger().warning("Failed to parse AWS secret as JSON", key=key, error=str(e))
            return None

    def list_secrets(self, prefix: str = "") -> list[str]:
        """
        List all secrets in AWS Secrets Manager with optional prefix filter.

        Args:
            prefix: Filter secrets that start with this prefix

        Returns:
            List of secret names
        """
        try:
            secrets = []
            paginator = self._client.get_paginator("list_secrets")

            # Build filters
            filters = []
            if prefix:
                filters.append({"Key": "name", "Values": [prefix]})

            page_iterator = paginator.paginate(
                Filters=filters if filters else [],
                PaginationConfig={"PageSize": 100}
            )

            for page in page_iterator:
                for secret in page.get("SecretList", []):
                    name = secret.get("Name", "")
                    if not prefix or name.startswith(prefix):
                        secrets.append(name)

            _get_logger().debug("Listed AWS secrets", prefix=prefix, count=len(secrets))
            return secrets

        except (self._ClientError, self._BotoCoreError) as e:
            _get_logger().error("Failed to list secrets from AWS Secrets Manager", error=str(e))
            return []

    def refresh(self) -> None:
        """Clear the cache to force refresh on next access."""
        cache_size = len(self._cache)
        self._cache.clear()
        _get_logger().info("Cleared AWS Secrets Manager cache", cleared_count=cache_size)


# ============================================================================
# Secrets Manager (Main Interface)
# ============================================================================


class SecretsManager:
    """
    Main secrets management interface with provider fallback chain.

    Supports multiple providers with automatic fallback:
    1. AWS Secrets Manager (if configured)
    2. Environment variables (always available)

    Usage:
        secrets = get_secrets_manager()
        api_key = secrets.get_secret("API_KEY")
    """

    def __init__(
        self,
        provider: Literal["env", "aws"] = "env",
        aws_region: str | None = None,
        cache_ttl: int = 3600,
    ):
        """
        Initialize secrets manager with specified provider.

        Args:
            provider: Provider type ("env" or "aws")
            aws_region: AWS region for AWS provider
            cache_ttl: Cache TTL for AWS provider (seconds)
        """
        self._provider_type = provider
        self._providers: list[ISecretsProvider] = []

        # Initialize primary provider
        if provider == "aws":
            try:
                aws_provider = AWSSecretsManagerProvider(
                    region=aws_region,
                    cache_ttl=cache_ttl
                )
                self._providers.append(aws_provider)
                _get_logger().info("Primary provider: AWS Secrets Manager")
            except ImportError:
                _get_logger().warning(
                    "AWS provider requested but boto3 not available, falling back to environment"
                )

        # Always add environment provider as fallback
        env_provider = EnvironmentSecretsProvider()
        self._providers.append(env_provider)

        if provider == "env":
            _get_logger().info("Primary provider: Environment variables")

        _get_logger().info(
            "Initialized SecretsManager",
            provider=provider,
            provider_count=len(self._providers)
        )

    def get_secret(self, key: str) -> str | None:
        """
        Get a secret from the provider chain.

        Tries each provider in order until a value is found.

        Args:
            key: Secret key/name

        Returns:
            Secret value or None if not found in any provider
        """
        for provider in self._providers:
            value = provider.get_secret(key)
            if value is not None:
                return value

        _get_logger().warning("Secret not found in any provider", key=key)
        return None

    def get_secret_json(self, key: str) -> dict | None:
        """
        Get a secret as JSON from the provider chain.

        Args:
            key: Secret key/name

        Returns:
            Parsed JSON dict or None if not found or invalid JSON
        """
        for provider in self._providers:
            value = provider.get_secret_json(key)
            if value is not None:
                return value

        _get_logger().warning("JSON secret not found in any provider", key=key)
        return None

    def list_secrets(self, prefix: str = "") -> list[str]:
        """
        List secrets from the primary provider.

        Args:
            prefix: Optional prefix filter

        Returns:
            List of secret keys
        """
        if self._providers:
            return self._providers[0].list_secrets(prefix)
        return []

    def refresh(self) -> None:
        """Refresh all providers."""
        for provider in self._providers:
            provider.refresh()
        _get_logger().info("Refreshed all secrets providers")


# ============================================================================
# Singleton Access
# ============================================================================


_secrets_manager_instance: SecretsManager | None = None


def get_secrets_manager(force_reload: bool = False) -> SecretsManager:
    """
    Get the singleton secrets manager instance.

    Creates the instance on first call based on application settings.

    Args:
        force_reload: Force recreation of the instance

    Returns:
        SecretsManager instance
    """
    global _secrets_manager_instance

    if _secrets_manager_instance is None or force_reload:
        from agent_service.config.settings import get_settings

        settings = get_settings()

        _secrets_manager_instance = SecretsManager(
            provider=settings.secrets_provider,
            aws_region=settings.secrets_aws_region,
            cache_ttl=settings.secrets_cache_ttl,
        )

        _get_logger().info(
            "Created SecretsManager singleton",
            provider=settings.secrets_provider
        )

    return _secrets_manager_instance


# ============================================================================
# Secret Masking for Logs
# ============================================================================


def mask_secret(value: str) -> str:
    """
    Mask a secret value for safe logging.

    Args:
        value: The secret value to mask

    Returns:
        Masked string (always "****")
    """
    return "****" if value else ""


def mask_secrets_in_dict(
    data: dict,
    keys: list[str] | None = None,
    default_keys: bool = True
) -> dict:
    """
    Mask sensitive values in a dictionary for safe logging.

    Args:
        data: Dictionary potentially containing secrets
        keys: Custom list of keys to mask
        default_keys: Include default sensitive key names (default: True)

    Returns:
        New dictionary with sensitive values masked
    """
    # Default sensitive key patterns (case-insensitive)
    default_sensitive_keys = {
        "password",
        "secret",
        "token",
        "api_key",
        "apikey",
        "auth",
        "credentials",
        "private_key",
        "access_key",
        "secret_key",
        "session_id",
        "jwt",
        "bearer",
    }

    # Build set of keys to mask
    keys_to_mask = set()
    if default_keys:
        keys_to_mask.update(default_sensitive_keys)
    if keys:
        keys_to_mask.update(k.lower() for k in keys)

    # Create masked copy
    masked = {}
    for key, value in data.items():
        key_lower = key.lower()

        # Check if key should be masked
        should_mask = any(sensitive in key_lower for sensitive in keys_to_mask)

        if should_mask and isinstance(value, str):
            masked[key] = mask_secret(value)
        elif isinstance(value, dict):
            # Recursively mask nested dictionaries
            masked[key] = mask_secrets_in_dict(value, keys, default_keys)
        elif isinstance(value, list):
            # Handle lists (mask if items are dicts)
            masked[key] = [
                mask_secrets_in_dict(item, keys, default_keys) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            masked[key] = value

    return masked


# ============================================================================
# Structlog Integration
# ============================================================================


def mask_secrets_processor(logger_obj: Any, method_name: str, event_dict: dict) -> dict:
    """
    Structlog processor that automatically masks sensitive fields.

    Add this to your structlog configuration:
        structlog.configure(
            processors=[
                ...,
                mask_secrets_processor,
                ...,
            ]
        )

    Args:
        logger_obj: Logger object (unused)
        method_name: Method name (unused)
        event_dict: Event dictionary from structlog

    Returns:
        Event dictionary with secrets masked
    """
    return mask_secrets_in_dict(event_dict)


# ============================================================================
# Convenience Functions
# ============================================================================


def get_secret(key: str, default: str | None = None) -> str | None:
    """
    Convenience function to get a secret.

    Args:
        key: Secret key
        default: Default value if not found

    Returns:
        Secret value or default
    """
    manager = get_secrets_manager()
    value = manager.get_secret(key)
    return value if value is not None else default


def get_secret_json(key: str, default: dict | None = None) -> dict | None:
    """
    Convenience function to get a JSON secret.

    Args:
        key: Secret key
        default: Default value if not found

    Returns:
        Parsed JSON dict or default
    """
    manager = get_secrets_manager()
    value = manager.get_secret_json(key)
    return value if value is not None else default
