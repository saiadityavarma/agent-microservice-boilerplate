"""
Example usage of the secrets management system.

This demonstrates how to use the various secrets providers and features.
"""
import os
from agent_service.config.secrets import (
    get_secrets_manager,
    get_secret,
    get_secret_json,
    mask_secret,
    mask_secrets_in_dict,
    EnvironmentSecretsProvider,
)


def example_basic_usage():
    """Example: Basic secrets retrieval."""
    print("\n=== Basic Usage ===")

    # Get the configured secrets manager (singleton)
    secrets = get_secrets_manager()

    # Get a simple secret
    api_key = secrets.get_secret("API_KEY")
    print(f"API_KEY: {mask_secret(api_key) if api_key else 'Not found'}")

    # Get a JSON secret
    db_config = secrets.get_secret_json("DATABASE_CONFIG")
    if db_config:
        print(f"Database config keys: {list(db_config.keys())}")
    else:
        print("DATABASE_CONFIG: Not found")


def example_convenience_functions():
    """Example: Using convenience functions."""
    print("\n=== Convenience Functions ===")

    # Direct access with defaults
    api_key = get_secret("API_KEY", default="default-key")
    print(f"API_KEY: {mask_secret(api_key)}")

    # JSON secret with default
    config = get_secret_json("APP_CONFIG", default={"mode": "development"})
    print(f"Config: {config}")


def example_environment_provider():
    """Example: Using environment provider directly."""
    print("\n=== Environment Provider ===")

    # Create an environment provider
    env_provider = EnvironmentSecretsProvider()

    # Set a test secret
    os.environ["TEST_SECRET"] = "my-secret-value"

    # Retrieve it
    value = env_provider.get_secret("TEST_SECRET")
    print(f"TEST_SECRET: {mask_secret(value) if value else 'Not found'}")

    # List all secrets with prefix
    secrets_list = env_provider.list_secrets(prefix="TEST_")
    print(f"Secrets with TEST_ prefix: {secrets_list}")


def example_secret_masking():
    """Example: Secret masking for logs."""
    print("\n=== Secret Masking ===")

    # Mask a single secret
    secret = "super-secret-api-key-12345"
    masked = mask_secret(secret)
    print(f"Original: {secret}")
    print(f"Masked: {masked}")

    # Mask secrets in a dictionary
    data = {
        "username": "john_doe",
        "password": "secret123",
        "api_key": "sk_live_abc123",
        "email": "john@example.com",
        "settings": {
            "timeout": 30,
            "secret_token": "hidden-token",
        },
    }

    masked_data = mask_secrets_in_dict(data)
    print(f"\nOriginal data: {data}")
    print(f"Masked data: {masked_data}")


def example_aws_provider():
    """Example: Using AWS Secrets Manager (requires boto3 and AWS credentials)."""
    print("\n=== AWS Secrets Manager Provider ===")

    try:
        from agent_service.config.secrets import AWSSecretsManagerProvider

        # This will only work if:
        # 1. boto3 is installed (pip install boto3 or agent-service[aws])
        # 2. AWS credentials are configured
        # 3. You have access to AWS Secrets Manager

        provider = AWSSecretsManagerProvider(
            region="us-east-1",
            cache_ttl=3600
        )

        # Try to get a secret (replace with your actual secret name)
        secret_name = "my-app/database/credentials"
        value = provider.get_secret(secret_name)

        if value:
            print(f"Retrieved secret: {mask_secret(value)}")
        else:
            print(f"Secret '{secret_name}' not found")

        # List secrets with prefix
        secrets = provider.list_secrets(prefix="my-app/")
        print(f"Secrets with 'my-app/' prefix: {len(secrets)} found")

    except ImportError:
        print("AWS provider not available (boto3 not installed)")
    except Exception as e:
        print(f"AWS provider error: {e}")


def example_json_secret():
    """Example: Storing and retrieving JSON secrets."""
    print("\n=== JSON Secrets ===")

    # Set a JSON secret in environment
    import json
    config = {
        "database": {
            "host": "localhost",
            "port": 5432,
            "username": "admin",
            "password": "secret123"
        },
        "cache": {
            "host": "redis",
            "port": 6379
        }
    }

    os.environ["APP_CONFIG"] = json.dumps(config)

    # Retrieve and parse it
    secrets = get_secrets_manager()
    retrieved_config = secrets.get_secret_json("APP_CONFIG")

    if retrieved_config:
        print("Retrieved JSON config:")
        # Mask secrets before printing
        masked_config = mask_secrets_in_dict(retrieved_config)
        print(json.dumps(masked_config, indent=2))


def example_refresh():
    """Example: Refreshing secrets."""
    print("\n=== Refresh Secrets ===")

    secrets = get_secrets_manager()

    # Initial value
    os.environ["REFRESHABLE_SECRET"] = "value1"
    value1 = secrets.get_secret("REFRESHABLE_SECRET")
    print(f"Initial value: {value1}")

    # Change the environment variable
    os.environ["REFRESHABLE_SECRET"] = "value2"

    # Without refresh, might get cached value (depends on provider)
    value2 = secrets.get_secret("REFRESHABLE_SECRET")
    print(f"After change (may be cached): {value2}")

    # Refresh to force reload
    secrets.refresh()
    value3 = secrets.get_secret("REFRESHABLE_SECRET")
    print(f"After refresh: {value3}")


def main():
    """Run all examples."""
    print("Secrets Management Examples")
    print("=" * 50)

    # Set up some test environment variables
    os.environ["API_KEY"] = "sk_live_test_key_12345"
    os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost/db"

    # Run examples
    example_basic_usage()
    example_convenience_functions()
    example_environment_provider()
    example_secret_masking()
    example_json_secret()
    example_refresh()
    example_aws_provider()  # This may fail if AWS is not configured

    print("\n" + "=" * 50)
    print("Examples complete!")


if __name__ == "__main__":
    main()
