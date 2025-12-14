# API Key Authentication System

Complete implementation of secure API key authentication for the agent service.

## Overview

This system provides secure API key management with:
- Cryptographically secure key generation
- SHA256 hashing (raw keys NEVER stored)
- User-scoped permissions
- Rate limiting tiers
- Key expiration and rotation
- Soft deletion for audit trails

## Directory Structure

```
/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/auth/
├── api_key.py                          # Core utilities for key generation/validation
├── models/
│   ├── __init__.py
│   └── api_key.py                      # SQLAlchemy model
├── schemas/
│   ├── __init__.py
│   └── api_key.py                      # Pydantic schemas
└── services/
    ├── __init__.py
    └── api_key_service.py              # Business logic service
```

## Components

### 1. Core Utilities (`api_key.py`)

**Functions:**
- `generate_api_key(prefix: str = "sk") -> tuple[str, str]`
  - Generates cryptographically secure API keys
  - Returns `(raw_key, hashed_key)` tuple
  - Key format: `{prefix}_{random_32_chars}`
  - Example: `sk_test_EXAMPLE_KEY_REPLACE_ME`

- `hash_api_key(key: str) -> str`
  - SHA256 hash for secure storage
  - Returns 64-character hexadecimal string

- `verify_api_key(key: str, hashed: str) -> bool`
  - Constant-time comparison to prevent timing attacks
  - Returns True if key matches hash

- `parse_api_key(key: str) -> APIKeyParts`
  - Extracts prefix and random parts
  - Returns dataclass with prefix, random_part, full_key

- `validate_api_key_format(key: str) -> bool`
  - Validates key format without database lookup
  - Checks minimum length and structure

**Security Features:**
- Uses `secrets` module for cryptographically secure randomness
- 32-character random part = ~191 bits of entropy
- Constant-time comparison prevents timing attacks
- Raw keys NEVER logged or stored

### 2. Database Model (`models/api_key.py`)

**SQLAlchemy Model: `APIKey`**

Fields:
- `id`: UUID primary key
- `user_id`: UUID foreign key to User
- `name`: Human-friendly name (max 255 chars)
- `key_hash`: SHA256 hash (64 chars, indexed, unique)
- `key_prefix`: First 8-12 chars for identification (indexed)
- `scopes`: JSON array of permission strings
- `rate_limit_tier`: "free" | "pro" | "enterprise"
- `expires_at`: Optional expiration timestamp (indexed)
- `last_used_at`: Last authentication timestamp
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `deleted_at`: Soft delete timestamp

**Properties:**
- `is_active`: True if not deleted and not expired
- `is_expired`: True if past expiration date
- `expires_in_days`: Days until expiration (or None)

**Methods:**
- `has_scope(scope)`: Check single scope
- `has_any_scope(scopes)`: Check any of multiple scopes
- `has_all_scopes(scopes)`: Check all scopes
- `update_last_used()`: Set last_used_at to now
- `soft_delete()`: Mark as deleted

**Indexes:**
- `key_hash` (unique): Fast authentication lookups
- `user_id`: Fast user key listings
- `key_prefix`: Quick key type identification
- Composite indexes for common queries

### 3. Pydantic Schemas (`schemas/api_key.py`)

**Request Schemas:**
- `APIKeyCreate`: For creating new keys
  - name, scopes, rate_limit_tier, expires_in_days, prefix
  - Validates scopes and name formatting

- `APIKeyUpdate`: For updating key metadata
  - Optional name, scopes, rate_limit_tier
  - Cannot change the key itself

**Response Schemas:**
- `APIKeyResponse`: Creation response (CONTAINS RAW KEY)
  - Includes raw key field - shown ONCE only
  - Also includes id, user_id, name, prefix, scopes, etc.

- `APIKeyInfo`: For listing/viewing (NO raw key)
  - All metadata except the raw key
  - Includes is_active, is_expired status
  - Property: `status` returns "active" | "expired" | "revoked"

- `APIKeyValidation`: For authentication validation
  - Minimal fields needed for auth: id, user_id, scopes, tier, is_active

**Utility Schemas:**
- `APIKeyParts`: Parsed key components
  - prefix, random_part, full_key

### 4. Business Logic Service (`services/api_key_service.py`)

**Class: `APIKeyService`**

**Methods:**

1. `create_api_key(user_id, name, scopes, expires_in_days, rate_limit_tier, prefix) -> APIKeyResponse`
   - Generates new cryptographically secure key
   - Stores only the hash
   - Returns raw key ONCE in response
   - Auto-calculates expiration timestamp

2. `validate_api_key(raw_key) -> Optional[APIKeyValidation]`
   - Validates key format
   - Looks up by hash
   - Checks not deleted, not expired
   - Verifies hash match (constant-time)
   - Updates last_used_at on success
   - Returns validation info or None

3. `revoke_api_key(key_id, user_id) -> bool`
   - Soft deletes the key
   - Verifies user ownership
   - Returns True if revoked, False if not found

4. `rotate_api_key(key_id, user_id) -> APIKeyResponse`
   - Creates new key with same properties
   - Soft deletes old key
   - Returns new raw key ONCE
   - Preserves expiration, scopes, tier

5. `list_api_keys(user_id) -> List[APIKeyInfo]`
   - Returns all non-deleted keys for user
   - Ordered by created_at descending
   - NO raw keys in response

6. `get_api_key(key_id, user_id) -> Optional[APIKeyInfo]`
   - Gets single key info
   - Verifies user ownership
   - Returns metadata only (no raw key)

7. `update_last_used(key_id) -> bool`
   - Updates last_used_at timestamp
   - Called automatically during validation

## Usage Examples

### Creating a New API Key

```python
from agent_service.auth import APIKeyService
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

# Initialize service
service = APIKeyService(session)

# Create key
key_response = await service.create_api_key(
    user_id=UUID("..."),
    name="Production API",
    scopes=["read", "write"],
    expires_in_days=365,
    rate_limit_tier="pro",
    prefix="sk_live"
)

# IMPORTANT: Show raw key to user ONCE
print(f"Your API key (save this, it won't be shown again): {key_response.key}")
# Output: sk_test_EXAMPLE_KEY_REPLACE_ME
```

### Validating an API Key (Authentication)

```python
# In authentication middleware
service = APIKeyService(session)

# Extract key from Authorization header
raw_key = request.headers.get("X-API-Key")

# Validate
validation = await service.validate_api_key(raw_key)

if validation is None:
    raise AuthenticationError("Invalid API key")

if not validation.is_active:
    raise AuthenticationError("API key is inactive")

# Check permissions
if "write" not in validation.scopes:
    raise AuthorizationError("Insufficient permissions")

# Key is valid, user is validation.user_id
current_user_id = validation.user_id
```

### Listing User's API Keys

```python
service = APIKeyService(session)

keys = await service.list_api_keys(user_id=UUID("..."))

for key in keys:
    print(f"Name: {key.name}")
    print(f"Prefix: {key.key_prefix}...")
    print(f"Status: {key.status}")
    print(f"Created: {key.created_at}")
    print(f"Last used: {key.last_used_at or 'Never'}")
    print(f"Expires: {key.expires_at or 'Never'}")
    print(f"Scopes: {', '.join(key.scopes)}")
    print()
```

### Rotating an API Key

```python
service = APIKeyService(session)

# Rotate key (creates new, revokes old)
new_key = await service.rotate_api_key(
    key_id=UUID("..."),
    user_id=UUID("...")
)

# Show new key to user ONCE
print(f"New API key: {new_key.key}")
print("Old key has been revoked")
```

### Revoking an API Key

```python
service = APIKeyService(session)

success = await service.revoke_api_key(
    key_id=UUID("..."),
    user_id=UUID("...")
)

if success:
    print("Key revoked successfully")
else:
    print("Key not found")
```

## Security Best Practices

### DO:
- ✅ Show raw keys to users ONLY once during creation
- ✅ Store only SHA256 hashes in the database
- ✅ Use constant-time comparison for verification
- ✅ Validate key format before database lookup
- ✅ Soft delete keys to maintain audit trail
- ✅ Update last_used_at for monitoring
- ✅ Use scopes for fine-grained permissions
- ✅ Set expiration dates for temporary access

### DON'T:
- ❌ NEVER log raw API keys
- ❌ NEVER return raw keys in list/get operations
- ❌ NEVER store raw keys in database
- ❌ NEVER include raw keys in error messages
- ❌ NEVER send raw keys in emails (except initial creation)
- ❌ NEVER reuse deleted key hashes
- ❌ NEVER skip ownership verification
- ❌ NEVER use timing-vulnerable comparison

## Database Migration

To use this system, you need to create the `api_keys` table:

```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(64) NOT NULL UNIQUE,
    key_prefix VARCHAR(12) NOT NULL,
    scopes JSONB DEFAULT '[]'::jsonb,
    rate_limit_tier VARCHAR(20) DEFAULT 'free',
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE INDEX ix_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX ix_api_keys_user_id ON api_keys(user_id);
CREATE INDEX ix_api_keys_key_prefix ON api_keys(key_prefix);
CREATE INDEX ix_api_keys_expires_at ON api_keys(expires_at);
CREATE INDEX ix_api_keys_user_id_deleted_at ON api_keys(user_id, deleted_at);
CREATE INDEX ix_api_keys_key_hash_deleted_at ON api_keys(key_hash, deleted_at);
```

## Rate Limiting Tiers

The system supports three rate limiting tiers:

- **free**: Basic rate limits for free tier users
- **pro**: Higher limits for paid users
- **enterprise**: Custom/unlimited for enterprise customers

Rate limiting implementation should check the `rate_limit_tier` field from `APIKeyValidation` during request processing.

## Scope Examples

Common scope patterns:

- Read-only: `["read"]`
- Read-write: `["read", "write"]`
- Admin: `["admin"]` or `["read", "write", "admin"]`
- Resource-specific: `["agents:read", "agents:write", "tools:read"]`
- Custom: Define your own scope namespace

## Integration with FastAPI

Example FastAPI dependency:

```python
from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from agent_service.auth import APIKeyService

async def get_current_user(
    x_api_key: str = Header(...),
    session: AsyncSession = Depends(get_session)
) -> UUID:
    service = APIKeyService(session)
    validation = await service.validate_api_key(x_api_key)

    if not validation:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return validation.user_id

# Use in routes
@app.get("/protected")
async def protected_route(user_id: UUID = Depends(get_current_user)):
    return {"user_id": str(user_id)}
```

## Testing

Example test cases:

```python
import pytest
from agent_service.auth import generate_api_key, verify_api_key, APIKeyService

def test_generate_api_key():
    raw_key, hashed_key = generate_api_key("sk_test")
    assert raw_key.startswith("sk_test_")
    assert len(raw_key) == len("sk_test_") + 32
    assert len(hashed_key) == 64

def test_verify_api_key():
    raw_key, hashed_key = generate_api_key()
    assert verify_api_key(raw_key, hashed_key) is True
    assert verify_api_key("wrong_key", hashed_key) is False

@pytest.mark.asyncio
async def test_create_and_validate(session):
    service = APIKeyService(session)

    # Create
    response = await service.create_api_key(
        user_id=test_user_id,
        name="Test Key",
        scopes=["read"]
    )

    # Validate
    validation = await service.validate_api_key(response.key)
    assert validation is not None
    assert validation.user_id == test_user_id
    assert "read" in validation.scopes
```

## Monitoring and Metrics

Key metrics to track:

- API key creation rate
- Validation success/failure rate
- Average key age at revocation
- Keys approaching expiration
- Never-used keys (last_used_at is None)
- Failed validation attempts by key prefix

## Future Enhancements

Potential improvements:

1. Key usage quotas (requests per day/month)
2. IP whitelist/blacklist per key
3. Key hierarchies (master keys, sub-keys)
4. Automatic key rotation policies
5. Key compromise detection
6. Multi-tenancy support
7. Key metadata tags
8. Webhook notifications for key events
