# Secrets Management - Quick Reference

## Import
```python
from agent_service.config import (
    get_secrets_manager,
    get_secret,
    get_secret_json,
    mask_secret,
    mask_secrets_in_dict,
)
```

## Basic Usage

### Get a Secret
```python
# Using manager
secrets = get_secrets_manager()
api_key = secrets.get_secret("API_KEY")

# Convenience function
api_key = get_secret("API_KEY", default="dev-key")
```

### Get JSON Secret
```python
# Using manager
db_config = secrets.get_secret_json("DATABASE_CONFIG")

# Convenience function
db_config = get_secret_json("DATABASE_CONFIG", default={})
```

### List Secrets
```python
secrets = get_secrets_manager()
all_secrets = secrets.list_secrets()
app_secrets = secrets.list_secrets(prefix="APP_")
```

### Refresh Secrets
```python
secrets = get_secrets_manager()
secrets.refresh()  # Clear cache and reload
```

## Secret Masking

### Mask Single Value
```python
secret = "sk_live_abc123"
masked = mask_secret(secret)  # Returns "****"

# Safe logging
logger.info(f"API Key: {mask_secret(api_key)}")
```

### Mask Dictionary
```python
data = {
    "username": "john",
    "password": "secret123",
    "api_key": "sk_live_abc"
}

safe_data = mask_secrets_in_dict(data)
# {"username": "john", "password": "****", "api_key": "****"}
```

### Custom Keys
```python
masked = mask_secrets_in_dict(
    data,
    keys=["custom_secret", "internal_token"],
    default_keys=True  # Also use default patterns
)
```

## Configuration

### .env File
```bash
SECRETS_PROVIDER=env
SECRETS_CACHE_TTL=3600
SECRETS_AWS_REGION=us-east-1

# Your secrets
API_KEY=your-api-key
DATABASE_CONFIG={"host":"localhost","port":5432}
```

### Settings
```python
from agent_service.config import get_settings

settings = get_settings()
settings.secrets_provider      # "env" or "aws"
settings.secrets_cache_ttl     # 3600
settings.secrets_aws_region    # None or region
```

## Providers

### Environment (Default)
```python
# Automatically reads from:
# - Environment variables
# - .env file
```

### AWS Secrets Manager
```bash
# 1. Install boto3
pip install agent-service[aws]

# 2. Configure AWS credentials
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret

# 3. Set provider
export SECRETS_PROVIDER=aws
export SECRETS_AWS_REGION=us-east-1
```

## Common Patterns

### Safe Request Logging
```python
from agent_service.config import mask_secrets_in_dict

@app.post("/api/endpoint")
async def endpoint(request: dict):
    safe_request = mask_secrets_in_dict(request)
    logger.info("Received request", data=safe_request)
    # ... process request
```

### Configuration Object
```python
from agent_service.config import get_secret_json

# Store complex config as JSON in secrets
db_config = get_secret_json("DATABASE_CONFIG", default={
    "host": "localhost",
    "port": 5432
})

engine = create_engine(f"postgresql://{db_config['host']}")
```

### Environment-Based Secrets
```python
from agent_service.config import get_settings, get_secret

settings = get_settings()

if settings.environment == "prod":
    api_key = get_secret("PROD_API_KEY")
else:
    api_key = get_secret("DEV_API_KEY", default="dev-key")
```

## Auto-Masking in Logs

No code changes needed! Secrets are automatically masked:

```python
logger.info(
    "User login",
    username="john",
    password="secret123",  # Automatically masked in logs
    api_key="sk_live_abc"  # Automatically masked in logs
)
```

## Sensitive Key Patterns (Auto-Masked)

Case-insensitive patterns:
- password
- secret
- token
- api_key / apikey
- auth / authorization
- credentials
- private_key
- access_key / secret_key
- session_id
- jwt / bearer

## Testing

### Mock Secrets
```python
def test_with_secrets(monkeypatch):
    monkeypatch.setenv("TEST_SECRET", "test-value")

    secret = get_secret("TEST_SECRET")
    assert secret == "test-value"
```

### Reset Singleton
```python
@pytest.fixture(autouse=True)
def reset_secrets():
    import agent_service.config.secrets as secrets_module
    secrets_module._secrets_manager_instance = None
    yield
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| ImportError: boto3 | `pip install agent-service[aws]` |
| Secret not found | Check spelling, verify .env loaded |
| Cache not refreshing | Call `secrets.refresh()` |
| AWS credentials error | Configure AWS credentials |

## Best Practices

1. ✅ Use `get_secret()` for simple access
2. ✅ Use `mask_secret()` when logging
3. ✅ Store complex config as JSON
4. ✅ Use AWS in production
5. ✅ Set appropriate cache TTL
6. ❌ Never log raw secrets
7. ❌ Never hardcode secrets
8. ❌ Don't commit .env files

## Examples

See `/examples/secrets_usage.py` for runnable examples.

## Full Documentation

See `/docs/secrets_management.md` for complete documentation.
