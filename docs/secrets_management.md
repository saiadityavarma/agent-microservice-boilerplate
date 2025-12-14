# Secrets Management

Comprehensive secrets management system with multiple provider support, caching, and automatic log masking.

## Overview

The secrets management system provides:

- **Multiple Providers**: Environment variables, AWS Secrets Manager
- **Fallback Chain**: Automatic fallback from cloud providers to environment variables
- **Caching**: Configurable TTL for cloud providers to reduce API calls
- **Secret Masking**: Automatic masking of sensitive values in logs
- **Type Safety**: Support for both string and JSON secrets
- **Easy Integration**: Simple API with singleton pattern

## Quick Start

### Basic Usage

```python
from agent_service.config import get_secrets_manager

# Get the secrets manager (singleton)
secrets = get_secrets_manager()

# Get a simple secret
api_key = secrets.get_secret("API_KEY")

# Get a JSON secret
db_config = secrets.get_secret_json("DATABASE_CONFIG")
# Returns: {"host": "localhost", "port": 5432, ...}
```

### Convenience Functions

```python
from agent_service.config import get_secret, get_secret_json

# Direct access with defaults
api_key = get_secret("API_KEY", default="default-key")
config = get_secret_json("APP_CONFIG", default={"mode": "dev"})
```

## Configuration

Add to your `.env` file or environment:

```bash
# Secrets provider selection
SECRETS_PROVIDER=env  # Options: env, aws
SECRETS_CACHE_TTL=3600  # Cache TTL in seconds (AWS provider)
SECRETS_AWS_REGION=us-east-1  # AWS region for Secrets Manager
```

### Settings Integration

The secrets manager integrates with `Settings`:

```python
from agent_service.config import get_settings

settings = get_settings()
print(settings.secrets_provider)  # "env" or "aws"
print(settings.secrets_cache_ttl)  # 3600 (default)
print(settings.secrets_aws_region)  # None or region
```

## Providers

### Environment Variables Provider

Default provider that reads from environment variables and `.env` files.

```python
from agent_service.config.secrets import EnvironmentSecretsProvider

# Initialize (automatically loads .env)
provider = EnvironmentSecretsProvider()

# Or specify custom .env path
provider = EnvironmentSecretsProvider(dotenv_path="/path/to/.env")

# Get secrets
api_key = provider.get_secret("API_KEY")

# List secrets with prefix
app_secrets = provider.list_secrets(prefix="APP_")

# Refresh from .env file
provider.refresh()
```

#### Features:
- Reads from environment variables
- Supports `.env` files via python-dotenv
- Prefix-based listing
- No external dependencies

### AWS Secrets Manager Provider

Cloud-based secrets provider with caching.

```python
from agent_service.config.secrets import AWSSecretsManagerProvider

# Initialize (requires boto3)
provider = AWSSecretsManagerProvider(
    region="us-east-1",
    cache_ttl=3600  # Cache for 1 hour
)

# Get secrets (cached)
db_password = provider.get_secret("prod/database/password")

# Get JSON secrets
db_config = provider.get_secret_json("prod/database/config")

# List secrets
all_prod_secrets = provider.list_secrets(prefix="prod/")

# Clear cache and force refresh
provider.refresh()
```

#### Features:
- Fetches from AWS Secrets Manager
- Automatic caching with configurable TTL
- Support for string and binary secrets
- Pagination support for large secret lists

#### Requirements:
```bash
# Install AWS dependencies
pip install boto3
# or
pip install agent-service[aws]
```

#### AWS Configuration:
Ensure AWS credentials are configured via:
- Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
- AWS credentials file (`~/.aws/credentials`)
- IAM role (when running on EC2/ECS)

#### Required IAM Permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:ListSecrets"
      ],
      "Resource": "*"
    }
  ]
}
```

## Provider Fallback Chain

When using `SecretsManager`, providers are tried in order:

```python
secrets = SecretsManager(provider="aws", aws_region="us-east-1")
# Try AWS Secrets Manager first
# If not found or unavailable, fall back to environment variables
```

Fallback order:
1. AWS Secrets Manager (if configured and available)
2. Environment Variables (always available)

## JSON Secrets

Store complex configuration as JSON:

```python
import json
import os

# Store JSON in environment
config = {
    "database": {
        "host": "localhost",
        "port": 5432,
        "credentials": {
            "username": "admin",
            "password": "secret"
        }
    }
}
os.environ["DB_CONFIG"] = json.dumps(config)

# Retrieve and parse
from agent_service.config import get_secret_json

db_config = get_secret_json("DB_CONFIG")
print(db_config["database"]["host"])  # "localhost"
```

## Secret Masking

Automatic masking for sensitive values in logs.

### Mask Individual Secrets

```python
from agent_service.config import mask_secret

api_key = "sk_live_1234567890abcdef"
print(f"API Key: {mask_secret(api_key)}")
# Output: API Key: ****
```

### Mask Dictionaries

```python
from agent_service.config import mask_secrets_in_dict

data = {
    "username": "john_doe",
    "password": "secret123",
    "api_key": "sk_live_abc123",
    "email": "john@example.com"
}

masked = mask_secrets_in_dict(data)
print(masked)
# {
#     "username": "john_doe",
#     "password": "****",
#     "api_key": "****",
#     "email": "john@example.com"
# }
```

### Nested Masking

Automatically handles nested structures:

```python
data = {
    "user": {
        "name": "john",
        "credentials": {
            "password": "secret123",
            "token": "bearer_xyz"
        }
    },
    "settings": {
        "timeout": 30
    }
}

masked = mask_secrets_in_dict(data)
# Passwords and tokens in nested dicts are masked
```

### Custom Sensitive Keys

```python
masked = mask_secrets_in_dict(
    data,
    keys=["custom_secret", "internal_token"],
    default_keys=True  # Also use default patterns
)
```

### Default Sensitive Patterns

The following patterns are masked by default (case-insensitive):
- password
- secret
- token
- api_key / apikey
- auth
- credentials
- private_key
- access_key
- secret_key
- session_id
- jwt
- bearer

## Structlog Integration

Secrets are automatically masked in logs via structlog processor.

### Configuration

Already configured in `infrastructure/observability/logging.py`:

```python
import structlog
from agent_service.config.secrets import mask_secrets_processor

structlog.configure(
    processors=[
        # ... other processors ...
        mask_secrets_processor,  # Automatically masks secrets
        # ... more processors ...
    ]
)
```

### Usage

```python
from agent_service.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

# These will be automatically masked in logs
logger.info(
    "User authenticated",
    username="john",
    password="secret123",  # Will be masked as ****
    api_key="sk_live_abc"  # Will be masked as ****
)
```

## Advanced Usage

### Custom Provider Implementation

Implement `ISecretsProvider` for custom backends:

```python
from agent_service.config.secrets import ISecretsProvider

class CustomSecretsProvider(ISecretsProvider):
    def get_secret(self, key: str) -> str | None:
        # Your implementation
        pass

    def get_secret_json(self, key: str) -> dict | None:
        # Your implementation
        pass

    def list_secrets(self, prefix: str = "") -> list[str]:
        # Your implementation
        pass

    def refresh(self) -> None:
        # Your implementation
        pass
```

### Manual Provider Chaining

```python
from agent_service.config.secrets import SecretsManager

# Create manager with multiple providers
manager = SecretsManager(provider="aws", aws_region="us-west-2")

# Manually add providers if needed
from agent_service.config.secrets import EnvironmentSecretsProvider
custom_provider = EnvironmentSecretsProvider(dotenv_path="/custom/.env")
manager._providers.insert(0, custom_provider)
```

### Singleton Management

```python
from agent_service.config.secrets import get_secrets_manager

# Get singleton
manager = get_secrets_manager()

# Force reload (recreate singleton)
manager = get_secrets_manager(force_reload=True)
```

## Best Practices

### 1. Use the Singleton

Always use `get_secrets_manager()` instead of creating instances:

```python
# Good
from agent_service.config import get_secrets_manager
secrets = get_secrets_manager()

# Avoid
from agent_service.config.secrets import SecretsManager
secrets = SecretsManager(provider="env")  # Creates new instance
```

### 2. Use Convenience Functions for Simple Cases

```python
# Simple one-off access
from agent_service.config import get_secret

api_key = get_secret("API_KEY", default="dev-key")
```

### 3. Mask Secrets Before Logging

```python
from agent_service.config import mask_secret

logger.info(f"Using API key: {mask_secret(api_key)}")
```

### 4. Store Complex Config as JSON

```python
# In AWS Secrets Manager or .env
{
    "database": {
        "host": "prod-db.example.com",
        "port": 5432,
        "ssl": true
    }
}

# In code
db_config = get_secret_json("DATABASE_CONFIG")
```

### 5. Use Appropriate TTL for Caching

```bash
# Development: short TTL for rapid changes
SECRETS_CACHE_TTL=300  # 5 minutes

# Production: longer TTL to reduce AWS API calls
SECRETS_CACHE_TTL=3600  # 1 hour
```

### 6. Refresh on Configuration Changes

```python
secrets = get_secrets_manager()

# After deploying new secrets
secrets.refresh()
```

## Environment Variables Reference

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SECRETS_PROVIDER` | string | `env` | Provider type: `env` or `aws` |
| `SECRETS_CACHE_TTL` | int | `3600` | Cache TTL in seconds (AWS) |
| `SECRETS_AWS_REGION` | string | `None` | AWS region for Secrets Manager |

## Testing

### Mock Secrets in Tests

```python
import pytest

def test_with_secrets(monkeypatch):
    # Set test secrets
    monkeypatch.setenv("TEST_API_KEY", "test-key")

    from agent_service.config import get_secret
    api_key = get_secret("TEST_API_KEY")

    assert api_key == "test-key"
```

### Reset Singleton in Tests

```python
import pytest

@pytest.fixture(autouse=True)
def reset_secrets_manager():
    """Reset singleton between tests."""
    import agent_service.config.secrets as secrets_module
    secrets_module._secrets_manager_instance = None
    yield
    secrets_module._secrets_manager_instance = None
```

## Troubleshooting

### AWS Provider Not Available

**Error**: `ImportError: boto3 is required`

**Solution**: Install AWS dependencies:
```bash
pip install boto3
# or
pip install agent-service[aws]
```

### AWS Credentials Not Found

**Error**: `NoCredentialsError`

**Solution**: Configure AWS credentials via:
```bash
# Environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1

# Or use AWS CLI
aws configure
```

### Secret Not Found

**Error**: Secret returns `None`

**Solution**:
1. Check secret name/key spelling
2. Verify provider has access to the secret
3. For AWS: check IAM permissions
4. For env: verify `.env` file is loaded

### Cache Not Refreshing

**Issue**: Updated secrets not reflected

**Solution**: Call `refresh()`:
```python
secrets = get_secrets_manager()
secrets.refresh()
```

## Migration Guide

### From Direct Environment Access

Before:
```python
import os
api_key = os.getenv("API_KEY")
```

After:
```python
from agent_service.config import get_secret
api_key = get_secret("API_KEY")
```

### From Settings-based Secrets

Before:
```python
from agent_service.config import get_settings
settings = get_settings()
api_key = settings.api_key
```

After:
```python
from agent_service.config import get_secret
api_key = get_secret("API_KEY")

# Or keep sensitive values in Settings as SecretStr
# and use secrets manager for runtime secrets
```

## Security Considerations

1. **Never log raw secrets**: Always use `mask_secret()` or rely on automatic masking
2. **Use AWS Secrets Manager in production**: More secure than environment variables
3. **Rotate secrets regularly**: Use AWS Secrets Manager rotation features
4. **Limit IAM permissions**: Grant only necessary permissions to secret resources
5. **Use different secrets per environment**: Separate dev/staging/prod secrets
6. **Audit secret access**: Enable AWS CloudTrail for Secrets Manager

## Examples

See `/examples/secrets_usage.py` for comprehensive examples.

## API Reference

### Functions

- `get_secrets_manager(force_reload: bool = False) -> SecretsManager`
- `get_secret(key: str, default: str | None = None) -> str | None`
- `get_secret_json(key: str, default: dict | None = None) -> dict | None`
- `mask_secret(value: str) -> str`
- `mask_secrets_in_dict(data: dict, keys: list[str] | None = None, default_keys: bool = True) -> dict`

### Classes

- `ISecretsProvider` - Abstract base class
- `EnvironmentSecretsProvider` - Environment variables provider
- `AWSSecretsManagerProvider` - AWS Secrets Manager provider
- `SecretsManager` - Main interface with fallback chain
