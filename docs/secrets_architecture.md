# Secrets Management Architecture

## Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Application Code                             │
│  (API handlers, services, background tasks, etc.)                │
└────────────┬────────────────────────────────────────────────────┘
             │
             │ Import and use
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Public API                                    │
├─────────────────────────────────────────────────────────────────┤
│  get_secrets_manager() → SecretsManager                          │
│  get_secret(key, default) → str | None                           │
│  get_secret_json(key, default) → dict | None                     │
│  mask_secret(value) → str                                        │
│  mask_secrets_in_dict(data, keys) → dict                         │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  SecretsManager (Singleton)                      │
├─────────────────────────────────────────────────────────────────┤
│  - Manages provider chain                                        │
│  - Implements fallback logic                                     │
│  - Delegates to providers                                        │
│                                                                   │
│  Methods:                                                         │
│  ├─ get_secret(key)                                              │
│  ├─ get_secret_json(key)                                         │
│  ├─ list_secrets(prefix)                                         │
│  └─ refresh()                                                    │
└────────────┬────────────────────────────────────────────────────┘
             │
             │ Fallback chain
             │
     ┌───────┴───────┐
     │               │
     ▼               ▼
┌────────────┐  ┌──────────────────┐
│  Provider  │  │  Provider        │
│  #1        │  │  #2 (Fallback)   │
│  (AWS)     │  │  (Environment)   │
└────────────┘  └──────────────────┘
     │               │
     │               │
     ▼               ▼
┌────────────┐  ┌──────────────────┐
│ AWS Secrets│  │ Environment Vars │
│ Manager    │  │ + .env files     │
└────────────┘  └──────────────────┘
```

## Class Hierarchy

```
ISecretsProvider (ABC)
├─ get_secret(key) → str | None
├─ get_secret_json(key) → dict | None
├─ list_secrets(prefix) → list[str]
└─ refresh() → None

        │
        │ Implements
        │
    ┌───┴────┬─────────────┐
    │        │             │
    ▼        ▼             ▼
Environment  AWS      (Future: Vault,
Provider   Provider   Azure, GCP...)
```

## Request Flow

### Getting a Secret

```
1. Application calls get_secret("API_KEY")
                │
                ▼
2. Singleton check: get_secrets_manager()
   ├─ Instance exists? Return it
   └─ Create new instance from Settings
                │
                ▼
3. SecretsManager.get_secret("API_KEY")
   ├─ Try Provider #1 (AWS)
   │  ├─ Check cache
   │  │  ├─ Hit: return cached value
   │  │  └─ Miss: fetch from AWS
   │  ├─ Success: return value
   │  └─ Fail: try next provider
   │
   └─ Try Provider #2 (Environment)
      ├─ Check os.environ
      ├─ Success: return value
      └─ Fail: return None
                │
                ▼
4. Return secret value to application
```

### Secret Masking Flow

```
1. Log statement with secrets
   logger.info("User login", password="secret123")
                │
                ▼
2. Structlog processors chain
   ├─ merge_contextvars
   ├─ add_request_id
   ├─ mask_secrets_processor ◄── Our processor
   │  └─ mask_secrets_in_dict(event_dict)
   │     ├─ Check each key against patterns
   │     ├─ Match: replace value with "****"
   │     └─ Recurse for nested dicts/lists
   ├─ add_log_level
   ├─ add_timestamp
   └─ JSONRenderer / ConsoleRenderer
                │
                ▼
3. Output to log with masked secrets
   {"message": "User login", "password": "****"}
```

## Provider Initialization

```
Settings (from environment)
├─ secrets_provider = "env" | "aws"
├─ secrets_cache_ttl = 3600
└─ secrets_aws_region = "us-east-1"
        │
        ▼
SecretsManager.__init__(provider, aws_region, cache_ttl)
        │
        ├─ If provider == "aws":
        │  ├─ Try: AWSSecretsManagerProvider(region, cache_ttl)
        │  │  ├─ Import boto3
        │  │  ├─ Create AWS client
        │  │  └─ Initialize cache
        │  └─ Catch ImportError: log warning
        │
        └─ Always: EnvironmentSecretsProvider()
           ├─ Load .env file
           └─ Ready to read os.environ
```

## Cache Management (AWS Provider)

```
Cache Structure:
{
    "secret_key_1": ("secret_value_1", timestamp_1),
    "secret_key_2": ("secret_value_2", timestamp_2),
    ...
}

Get Secret Flow:
1. Check cache validity
   ├─ Key exists?
   │  ├─ Yes: Check TTL
   │  │  ├─ Age < TTL: return cached value
   │  │  └─ Age >= TTL: fetch from AWS
   │  └─ No: fetch from AWS
   │
2. Fetch from AWS
   ├─ Call get_secret_value()
   ├─ Parse response
   ├─ Store in cache with current timestamp
   └─ Return value

Refresh Flow:
1. Call refresh()
2. Clear entire cache
3. Next get_secret() will fetch fresh values
```

## Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Secret Storage                                      │
│ ├─ AWS Secrets Manager (encrypted at rest)                   │
│ ├─ Environment Variables (process memory)                    │
│ └─ .env files (file system, .gitignore)                      │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Retrieval & Caching                                 │
│ ├─ AWS: TLS in transit                                       │
│ ├─ Cache: In-memory only (not persisted)                     │
│ └─ TTL: Automatic expiration                                 │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Usage in Code                                       │
│ ├─ Type-safe access (str | None)                             │
│ ├─ No hardcoded secrets                                      │
│ └─ Fallback to defaults                                      │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: Logging & Observability                             │
│ ├─ Automatic masking of sensitive fields                     │
│ ├─ Pattern-based detection                                   │
│ └─ Recursive masking of nested structures                    │
└─────────────────────────────────────────────────────────────┘
```

## Integration Points

```
┌─────────────────────────────────────────────────────────────┐
│                     agent_service                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────┐            │
│  │  config/                                     │            │
│  │  ├─ settings.py                              │            │
│  │  │  ├─ secrets_provider                      │            │
│  │  │  ├─ secrets_cache_ttl                     │            │
│  │  │  └─ secrets_aws_region                    │            │
│  │  │                                            │            │
│  │  ├─ secrets.py ◄──────────────────────┐      │            │
│  │  │  ├─ ISecretsProvider               │      │            │
│  │  │  ├─ EnvironmentSecretsProvider     │      │            │
│  │  │  ├─ AWSSecretsManagerProvider      │      │            │
│  │  │  ├─ SecretsManager                 │      │            │
│  │  │  └─ Masking utilities              │      │            │
│  │  │                                     │      │            │
│  │  └─ __init__.py (exports)              │      │            │
│  └──────────────────────────────────────────┘   │            │
│                                                  │            │
│  ┌──────────────────────────────────────────────┼────┐       │
│  │  infrastructure/observability/               │    │       │
│  │  └─ logging.py                               │    │       │
│  │     └─ mask_secrets_processor ───────────────┘    │       │
│  └───────────────────────────────────────────────────┘       │
│                                                               │
│  ┌──────────────────────────────────────────────┐            │
│  │  api/, services/, tasks/                     │            │
│  │  (Application code)                          │            │
│  │  └─ Uses get_secret(), mask_secret()         │            │
│  └──────────────────────────────────────────────┘            │
│                                                               │
└─────────────────────────────────────────────────────────────┘

External Dependencies:
├─ python-dotenv (load .env files)
├─ boto3 (optional, for AWS provider)
├─ structlog (logging framework)
└─ pydantic-settings (Settings management)
```

## Error Handling

```
┌─────────────────────────────────────────────────────────────┐
│ Error Scenario                    │ Handling                │
├───────────────────────────────────┼─────────────────────────┤
│ boto3 not installed               │ Skip AWS provider,      │
│                                   │ fall back to env        │
├───────────────────────────────────┼─────────────────────────┤
│ AWS credentials missing           │ AWS calls fail,         │
│                                   │ fall back to env        │
├───────────────────────────────────┼─────────────────────────┤
│ AWS secret not found              │ Log warning,            │
│                                   │ try next provider       │
├───────────────────────────────────┼─────────────────────────┤
│ AWS connection error              │ Log error,              │
│                                   │ try next provider       │
├───────────────────────────────────┼─────────────────────────┤
│ Secret not in any provider        │ Return None,            │
│                                   │ use default if provided │
├───────────────────────────────────┼─────────────────────────┤
│ Invalid JSON in secret            │ Log warning,            │
│                                   │ return None             │
├───────────────────────────────────┼─────────────────────────┤
│ .env file missing                 │ Skip loading,           │
│                                   │ use os.environ only     │
└───────────────────────────────────┴─────────────────────────┘
```

## Configuration Matrix

```
┌──────────────┬─────────────┬──────────────┬─────────────────┐
│ Environment  │ Provider    │ Cache TTL    │ Behavior        │
├──────────────┼─────────────┼──────────────┼─────────────────┤
│ local/dev    │ env         │ N/A          │ Read from .env  │
│              │             │              │ Fast, no API    │
├──────────────┼─────────────┼──────────────┼─────────────────┤
│ staging      │ aws         │ 300 (5m)     │ Short cache,    │
│              │             │              │ rapid updates   │
├──────────────┼─────────────┼──────────────┼─────────────────┤
│ production   │ aws         │ 3600 (1h)    │ Long cache,     │
│              │             │              │ reduce AWS cost │
└──────────────┴─────────────┴──────────────┴─────────────────┘
```

## Lifecycle

```
Application Startup
    │
    ├─ Load Settings from environment
    │  └─ Determine secrets_provider
    │
    ├─ First get_secret() call
    │  └─ Create SecretsManager singleton
    │     ├─ Initialize providers based on config
    │     └─ Load .env if using env provider
    │
    ├─ Configure logging
    │  └─ Add mask_secrets_processor to structlog
    │
    └─ Application running
       ├─ Secrets fetched on-demand
       ├─ AWS secrets cached per TTL
       └─ All logs automatically masked

Runtime
    │
    ├─ Secret accessed: get_secret("KEY")
    │  └─ Check providers in order
    │
    ├─ Cache expires (AWS)
    │  └─ Next access fetches fresh value
    │
    └─ Manual refresh: secrets.refresh()
       └─ Clear all caches

Application Shutdown
    │
    └─ Cache discarded (not persisted)
```

## Performance Characteristics

```
┌──────────────────┬─────────────┬──────────────┬─────────────┐
│ Operation        │ Env Provider│ AWS (Cached) │ AWS (Fresh) │
├──────────────────┼─────────────┼──────────────┼─────────────┤
│ get_secret()     │ ~1μs        │ ~10μs        │ ~50-200ms   │
├──────────────────┼─────────────┼──────────────┼─────────────┤
│ get_secret_json()│ ~100μs      │ ~100μs       │ ~50-200ms   │
├──────────────────┼─────────────┼──────────────┼─────────────┤
│ list_secrets()   │ ~50μs       │ N/A          │ ~100-500ms  │
├──────────────────┼─────────────┼──────────────┼─────────────┤
│ refresh()        │ ~1ms        │ ~1μs         │ N/A         │
└──────────────────┴─────────────┴──────────────┴─────────────┘

Memory Usage:
├─ Environment provider: ~1KB
├─ AWS provider (no cache): ~10KB
└─ AWS provider (100 cached secrets): ~100KB
```

## Extension Points

Want to add a new provider? Implement `ISecretsProvider`:

```python
class VaultSecretsProvider(ISecretsProvider):
    def __init__(self, vault_url: str, token: str):
        # Initialize Vault client
        pass

    def get_secret(self, key: str) -> str | None:
        # Fetch from Vault
        pass

    def get_secret_json(self, key: str) -> dict | None:
        # Fetch and parse JSON from Vault
        pass

    def list_secrets(self, prefix: str) -> list[str]:
        # List secrets in Vault
        pass

    def refresh(self) -> None:
        # Clear cache / renew token
        pass
```

Then add to `SecretsManager`:

```python
if provider == "vault":
    vault_provider = VaultSecretsProvider(
        vault_url=settings.vault_url,
        token=settings.vault_token
    )
    self._providers.append(vault_provider)
```

## Summary

This architecture provides:
- ✅ Separation of concerns (providers, manager, masking)
- ✅ Extensibility (easy to add new providers)
- ✅ Resilience (fallback chain)
- ✅ Performance (caching with TTL)
- ✅ Security (automatic masking)
- ✅ Testability (mock-friendly interfaces)
- ✅ Type safety (explicit return types)
- ✅ Observability (comprehensive logging)
