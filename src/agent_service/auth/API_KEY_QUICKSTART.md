# API Key Authentication - Quick Start Guide

5-minute guide to implementing API key authentication in your application.

## Installation

No additional dependencies required. The system uses standard library cryptography (`hashlib`, `secrets`).

## Step 1: Database Setup

Create the `api_keys` table in your database:

```python
# In your alembic migration or database setup
from agent_service.auth.models import APIKey
from agent_service.infrastructure.database import engine

# Create table
await APIKey.metadata.create_all(engine)
```

## Step 2: Create API Keys

```python
from agent_service.auth import APIKeyService
from uuid import UUID

# In your API key management endpoint
async def create_user_api_key(session, user_id: UUID):
    service = APIKeyService(session)

    response = await service.create_api_key(
        user_id=user_id,
        name="My API Key",
        scopes=["read", "write"],
        expires_in_days=365
    )

    # Return this to the user ONCE
    return {
        "message": "API key created. Save this - it won't be shown again!",
        "api_key": response.key,  # sk_abc123...
        "created_at": response.created_at
    }
```

## Step 3: Validate API Keys (Authentication)

```python
from fastapi import Header, HTTPException, Depends
from agent_service.auth import APIKeyService

async def authenticate_api_key(
    x_api_key: str = Header(..., description="API Key"),
    session: AsyncSession = Depends(get_session)
):
    service = APIKeyService(session)
    validation = await service.validate_api_key(x_api_key)

    if not validation:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Return user info for downstream use
    return {
        "user_id": validation.user_id,
        "scopes": validation.scopes,
        "tier": validation.rate_limit_tier
    }

# Use in your routes
@app.get("/api/protected")
async def protected_endpoint(auth=Depends(authenticate_api_key)):
    user_id = auth["user_id"]
    return {"message": f"Hello user {user_id}"}
```

## Step 4: Check Permissions

```python
from fastapi import HTTPException

async def require_scope(required_scope: str, auth=Depends(authenticate_api_key)):
    if required_scope not in auth["scopes"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return auth

# Use in routes
@app.post("/api/write-data")
async def write_data(
    data: dict,
    auth=Depends(lambda: require_scope("write"))
):
    return {"message": "Data written", "user_id": auth["user_id"]}
```

## Step 5: List User's Keys

```python
@app.get("/api/keys")
async def list_my_keys(
    auth=Depends(authenticate_api_key),
    session: AsyncSession = Depends(get_session)
):
    service = APIKeyService(session)
    keys = await service.list_api_keys(auth["user_id"])

    return {
        "keys": [
            {
                "id": str(key.id),
                "name": key.name,
                "prefix": key.key_prefix,
                "status": key.status,
                "created": key.created_at,
                "last_used": key.last_used_at
            }
            for key in keys
        ]
    }
```

## Step 6: Revoke a Key

```python
@app.delete("/api/keys/{key_id}")
async def revoke_key(
    key_id: UUID,
    auth=Depends(authenticate_api_key),
    session: AsyncSession = Depends(get_session)
):
    service = APIKeyService(session)
    success = await service.revoke_api_key(key_id, auth["user_id"])

    if not success:
        raise HTTPException(status_code=404, detail="Key not found")

    return {"message": "Key revoked successfully"}
```

## Complete Example: FastAPI Application

```python
from fastapi import FastAPI, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from agent_service.auth import APIKeyService

app = FastAPI()

# Database dependency
async def get_session():
    async with async_session_maker() as session:
        yield session

# Auth dependency
async def get_current_user(
    x_api_key: str = Header(...),
    session: AsyncSession = Depends(get_session)
) -> dict:
    service = APIKeyService(session)
    validation = await service.validate_api_key(x_api_key)

    if not validation:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return {
        "user_id": validation.user_id,
        "scopes": validation.scopes,
        "tier": validation.rate_limit_tier
    }

# Create API key
@app.post("/keys")
async def create_key(
    name: str,
    scopes: list[str],
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    service = APIKeyService(session)
    response = await service.create_api_key(
        user_id=current_user["user_id"],
        name=name,
        scopes=scopes,
        expires_in_days=365
    )

    return {
        "api_key": response.key,  # Show ONCE
        "created_at": response.created_at
    }

# Protected endpoint
@app.get("/data")
async def get_data(current_user: dict = Depends(get_current_user)):
    return {
        "message": "Protected data",
        "user_id": str(current_user["user_id"])
    }

# Scope-protected endpoint
@app.post("/data")
async def create_data(
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    if "write" not in current_user["scopes"]:
        raise HTTPException(status_code=403, detail="Write permission required")

    return {"message": "Data created"}
```

## Testing with curl

```bash
# Create a key (requires initial auth - JWT, session, etc.)
curl -X POST http://localhost:8000/keys \
  -H "Authorization: Bearer <your-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Key", "scopes": ["read", "write"]}'

# Response:
# {"api_key": "sk_abc123...", "created_at": "2024-01-01T00:00:00"}

# Use the key
curl http://localhost:8000/data \
  -H "X-API-Key: sk_abc123..."

# Response:
# {"message": "Protected data", "user_id": "..."}
```

## Common Patterns

### 1. Rate Limiting by Tier

```python
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

TIER_LIMITS = {
    "free": "100/hour",
    "pro": "1000/hour",
    "enterprise": "10000/hour"
}

@app.get("/data")
@limiter.limit(lambda: TIER_LIMITS.get(request.state.tier, "100/hour"))
async def get_data(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    # Store tier in request state for rate limiter
    request.state.tier = current_user["tier"]
    return {"data": "..."}
```

### 2. Scope-Based Authorization Decorator

```python
from functools import wraps

def require_scopes(*required_scopes):
    async def dependency(current_user: dict = Depends(get_current_user)):
        user_scopes = set(current_user["scopes"])
        required = set(required_scopes)

        if not required.issubset(user_scopes):
            raise HTTPException(
                status_code=403,
                detail=f"Missing scopes: {required - user_scopes}"
            )

        return current_user

    return dependency

# Usage
@app.post("/admin/action")
async def admin_action(current_user: dict = Depends(require_scopes("admin"))):
    return {"message": "Admin action performed"}
```

### 3. Key Rotation Endpoint

```python
@app.post("/keys/{key_id}/rotate")
async def rotate_key(
    key_id: UUID,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    service = APIKeyService(session)
    new_key = await service.rotate_api_key(key_id, current_user["user_id"])

    return {
        "message": "Key rotated. Old key revoked.",
        "new_key": new_key.key,  # Show ONCE
        "created_at": new_key.created_at
    }
```

## Security Checklist

- [ ] Raw keys shown only once during creation
- [ ] Raw keys never logged
- [ ] HTTPS enforced in production
- [ ] Rate limiting implemented
- [ ] Key expiration dates set
- [ ] Monitoring for failed auth attempts
- [ ] Soft delete preserves audit trail
- [ ] Ownership verification in all operations

## Next Steps

1. Implement rate limiting middleware
2. Add monitoring/alerting for suspicious activity
3. Create admin dashboard for key management
4. Set up automatic key rotation policies
5. Implement key usage quotas
6. Add webhook notifications for key events

## Support

For questions or issues, see:
- Full documentation: `API_KEY_README.md`
- Source code: `/src/agent_service/auth/`
- Models: `/src/agent_service/auth/models/api_key.py`
- Service: `/src/agent_service/auth/services/api_key_service.py`
