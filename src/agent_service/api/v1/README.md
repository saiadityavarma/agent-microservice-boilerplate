# API v1 Documentation

This directory contains all v1 API routes and documentation.

## Overview

All v1 API routes are mounted under `/api/v1` and include:
- Agent invocation and streaming
- API key management
- Protocol handlers (A2A, MCP, etc.)
- Audit log queries (admin only)

Routes that are **NOT** versioned (kept at root level):
- Health checks (`/health/*`)
- User info (`/auth/me`, `/auth/permissions`)
- Token validation (`/auth/validate`)

## API Structure

```
/api/v1/
├── /agents/                    # Agent endpoints
│   ├── POST /invoke           # Synchronous agent invocation
│   └── POST /stream           # Streaming agent invocation
├── /auth/api-keys/            # API key management
│   ├── POST /                 # Create new API key
│   ├── GET /                  # List user's API keys
│   ├── GET /{key_id}          # Get API key details
│   ├── DELETE /{key_id}       # Revoke API key
│   └── POST /{key_id}/rotate  # Rotate API key
├── /protocols/                # Protocol handlers
│   ├── POST /{protocol}/invoke
│   └── POST /{protocol}/stream
└── /admin/audit/              # Audit logs (admin only)
    ├── GET /                  # Query audit logs
    ├── GET /{audit_id}        # Get specific audit log
    └── GET /stats/summary     # Audit statistics
```

## API Versioning

### Version Headers

All v1 API responses include version headers:

```http
X-API-Version: v1
X-API-Status: stable
```

### Deprecation

When a version is deprecated, additional headers are added:

```http
X-API-Version: v1
X-API-Status: deprecated
X-API-Deprecated: true
Deprecation: @1672531200
Sunset: Sat, 01 Jul 2025 00:00:00 GMT
Link: <https://docs.example.com/api/v1-migration>; rel="deprecation"
```

### Version Status

API versions can have the following statuses:
- **`stable`** - Production-ready, fully supported
- **`beta`** - Testing phase, may have breaking changes
- **`deprecated`** - Still functional but scheduled for removal
- **`sunset`** - No longer available

### Configuring Version Status

Version status is configured in `/api/middleware/versioning.py`:

```python
API_VERSIONS = {
    "v1": {
        "status": "stable",
        "deprecated": False,
        "sunset_date": None,
        "deprecation_message": None,
    },
}
```

To deprecate v1 when releasing v2:

```python
API_VERSIONS = {
    "v1": {
        "status": "deprecated",
        "deprecated": True,
        "deprecation_date": "2025-01-01T00:00:00Z",  # When deprecated
        "sunset_date": "2025-07-01T00:00:00Z",       # When removed
        "deprecation_message": "API v1 is deprecated. Migrate to v2.",
    },
    "v2": {
        "status": "stable",
        "deprecated": False,
        "sunset_date": None,
        "deprecation_message": None,
    },
}
```

## Endpoints

### Agent Endpoints

#### `POST /api/v1/agents/invoke`

Invoke agent synchronously.

**Request:**
```http
POST /api/v1/agents/invoke
Content-Type: application/json

{
    "message": "Hello, agent!"
}
```

**Response:**
```json
{
    "response": "Hello! How can I help you?"
}
```

#### `POST /api/v1/agents/stream`

Invoke agent with streaming response (Server-Sent Events).

**Request:**
```http
POST /api/v1/agents/stream
Content-Type: application/json

{
    "message": "Tell me a story"
}
```

**Response:**
```http
Content-Type: text/event-stream

data: Once upon a time...
data: there was a...
data: [EOF]
```

### API Key Management

All API key endpoints require authentication.

#### `POST /api/v1/auth/api-keys`

Create a new API key.

**Rate Limit:** 10 requests per hour

**Request:**
```json
{
    "name": "Production API",
    "scopes": ["read", "write"],
    "rate_limit_tier": "pro",
    "expires_in_days": 365
}
```

**Response:**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "user123",
    "name": "Production API",
    "key": "sk_live_a1b2c3d4e5f6...",  // ONLY SHOWN ONCE
    "key_prefix": "sk_live",
    "scopes": ["read", "write"],
    "rate_limit_tier": "pro",
    "expires_at": "2025-12-13T00:00:00Z",
    "created_at": "2024-12-13T00:00:00Z"
}
```

#### `GET /api/v1/auth/api-keys`

List all API keys for the authenticated user.

**Response:**
```json
[
    {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "user_id": "user123",
        "name": "Production API",
        "key_prefix": "sk_live",
        "scopes": ["read", "write"],
        "rate_limit_tier": "pro",
        "expires_at": "2025-12-13T00:00:00Z",
        "last_used_at": "2024-12-12T15:30:00Z",
        "created_at": "2024-12-13T00:00:00Z",
        "updated_at": "2024-12-13T00:00:00Z",
        "is_active": true,
        "is_expired": false
    }
]
```

#### `GET /api/v1/auth/api-keys/{key_id}`

Get details about a specific API key.

**Response:**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "user123",
    "name": "Production API",
    "key_prefix": "sk_live",
    "scopes": ["read", "write"],
    "rate_limit_tier": "pro",
    "expires_at": "2025-12-13T00:00:00Z",
    "last_used_at": "2024-12-12T15:30:00Z",
    "created_at": "2024-12-13T00:00:00Z",
    "updated_at": "2024-12-13T00:00:00Z",
    "is_active": true,
    "is_expired": false
}
```

#### `DELETE /api/v1/auth/api-keys/{key_id}`

Revoke an API key.

**Response:** `204 No Content`

#### `POST /api/v1/auth/api-keys/{key_id}/rotate`

Rotate an API key (create new key and revoke old one).

**Rate Limit:** 10 requests per hour

**Response:**
```json
{
    "old_key_id": "550e8400-e29b-41d4-a716-446655440000",
    "new_key": {
        "id": "660e8400-e29b-41d4-a716-446655440001",
        "user_id": "user123",
        "name": "Production API",
        "key": "sk_live_x9y8z7w6...",  // ONLY SHOWN ONCE
        "key_prefix": "sk_live",
        "scopes": ["read", "write"],
        "rate_limit_tier": "pro",
        "expires_at": "2025-12-13T00:00:00Z",
        "created_at": "2024-12-13T01:00:00Z"
    },
    "message": "API key rotated successfully. Old key revoked, new key created."
}
```

### Protocol Endpoints

#### `GET /.well-known/agent.json`

Get A2A agent card (agent capability information).

**Response:**
```json
{
    "name": "My Agent",
    "version": "1.0.0",
    "capabilities": [...]
}
```

#### `POST /api/v1/protocols/{protocol}/invoke`

Invoke agent via specific protocol (e.g., `a2a`, `mcp`).

**Example:**
```http
POST /api/v1/protocols/a2a/invoke
Content-Type: application/json

{
    "message": "Hello via A2A protocol"
}
```

#### `POST /api/v1/protocols/{protocol}/stream`

Stream agent response via specific protocol.

**Example:**
```http
POST /api/v1/protocols/a2a/stream
Content-Type: application/json

{
    "message": "Stream via A2A protocol"
}
```

### Audit Endpoints (Admin Only)

All audit endpoints require `ADMIN` or `SUPER_ADMIN` role.

#### `GET /api/v1/admin/audit`

Query audit logs with filters.

**Query Parameters:**
- `user_id` (UUID) - Filter by user ID
- `action` (string) - Filter by action type (CREATE, READ, UPDATE, DELETE)
- `resource_type` (string) - Filter by resource type
- `resource_id` (string) - Filter by resource ID
- `request_id` (UUID) - Filter by request ID
- `ip_address` (string) - Filter by IP address
- `start_date` (datetime) - Filter by start date
- `end_date` (datetime) - Filter by end date
- `response_status` (int) - Filter by HTTP status code
- `limit` (int, 1-1000) - Number of items (default: 100)
- `offset` (int) - Pagination offset

**Response:**
```json
{
    "items": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2024-12-13T10:30:00Z",
            "user_id": "user123",
            "action": "CREATE",
            "resource_type": "agent",
            "resource_id": "agent123",
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0...",
            "request_id": "660e8400-e29b-41d4-a716-446655440001",
            "request_path": "/api/v1/agents",
            "request_method": "POST",
            "response_status": 201
        }
    ],
    "total": 100,
    "limit": 100,
    "offset": 0,
    "has_more": false
}
```

#### `GET /api/v1/admin/audit/{audit_id}`

Get a specific audit log entry.

**Response:**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-12-13T10:30:00Z",
    "user_id": "user123",
    "action": "CREATE",
    "resource_type": "agent",
    "resource_id": "agent123",
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "request_id": "660e8400-e29b-41d4-a716-446655440001",
    "request_path": "/api/v1/agents",
    "request_method": "POST",
    "request_body": "{...}",
    "response_status": 201,
    "changes": {...},
    "metadata": {...},
    "created_at": "2024-12-13T10:30:00Z",
    "updated_at": "2024-12-13T10:30:00Z"
}
```

#### `GET /api/v1/admin/audit/stats/summary`

Get audit log statistics.

**Query Parameters:**
- `start_date` (datetime) - Filter by start date
- `end_date` (datetime) - Filter by end date

**Response:**
```json
{
    "total_events": 1000,
    "events_by_action": {
        "CREATE": 500,
        "READ": 300,
        "UPDATE": 150,
        "DELETE": 50
    },
    "events_by_resource": {
        "agent": 600,
        "api_key": 400
    },
    "unique_users": 50,
    "date_range": {
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-12-13T00:00:00Z"
    }
}
```

## Authentication

All API endpoints (except health checks) require authentication via:

1. **Bearer Token** (JWT):
   ```http
   Authorization: Bearer eyJhbGciOiJSUzI1...
   ```

2. **API Key**:
   ```http
   X-API-Key: sk_live_a1b2c3d4e5f6...
   ```

## Response Format

All v1 API responses follow the standard response format defined in `/api/schemas/`:

### Success Response

```json
{
    "success": true,
    "data": { ... },
    "meta": {
        "request_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2024-12-13T10:30:00Z",
        "version": "v1"
    }
}
```

### Error Response

```json
{
    "success": false,
    "error": {
        "code": "NOT_FOUND",
        "message": "Resource not found",
        "details": [
            {
                "field": "id",
                "message": "Invalid ID format"
            }
        ],
        "context": {
            "resource_id": "123"
        }
    },
    "meta": {
        "request_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2024-12-13T10:30:00Z",
        "version": "v1"
    }
}
```

### Paginated Response

```json
{
    "items": [...],
    "pagination": {
        "page": 1,
        "page_size": 20,
        "total": 100,
        "total_pages": 5,
        "has_next": true,
        "has_prev": false
    }
}
```

## Error Codes

Standard error codes are defined in `/api/schemas/errors.py`:

- `VALIDATION_ERROR` (400) - Input validation failed
- `UNAUTHORIZED` (401) - Authentication required
- `FORBIDDEN` (403) - Insufficient permissions
- `NOT_FOUND` (404) - Resource not found
- `CONFLICT` (409) - Resource conflict
- `RATE_LIMITED` (429) - Rate limit exceeded
- `INTERNAL_ERROR` (500) - Internal server error
- `SERVICE_UNAVAILABLE` (503) - Service unavailable
- `TIMEOUT` (504) - Request timeout

See [Error Codes Documentation](../schemas/README.md#errorcode-enum) for the complete list.

## Rate Limiting

Rate limits are enforced per user/API key:

| Endpoint | Limit |
|----------|-------|
| API Key Creation | 10 per hour |
| API Key Rotation | 10 per hour |
| Token Validation | 100 per minute |
| Default | 1000 per hour |

Rate limit headers are included in responses:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1672531200
```

## Adding New Endpoints

To add new endpoints to v1:

1. **Create route file** in `/api/routes/`:
   ```python
   # src/agent_service/api/routes/my_feature.py
   from fastapi import APIRouter

   router = APIRouter()

   @router.get("/items")
   async def list_items():
       return {"items": []}
   ```

2. **Add to v1 router** in `/api/v1/router.py`:
   ```python
   from agent_service.api.routes import my_feature

   router.include_router(
       my_feature.router,
       prefix="/my-feature",
       tags=["My Feature"]
   )
   ```

3. **Use standard schemas**:
   ```python
   from agent_service.api.schemas import SuccessResponse, PaginatedResponse

   @router.get("/items", response_model=PaginatedResponse[Item])
   async def list_items(pagination: PaginationParams = Depends()):
       ...
   ```

## Testing

Example test for v1 endpoints:

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_invoke_agent(client: AsyncClient):
    response = await client.post(
        "/api/v1/agents/invoke",
        json={"message": "Hello"},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.headers["X-API-Version"] == "v1"

    data = response.json()
    assert "response" in data

@pytest.mark.asyncio
async def test_api_version_headers(client: AsyncClient):
    response = await client.get("/api/v1/agents/status")

    assert "X-API-Version" in response.headers
    assert response.headers["X-API-Version"] == "v1"
    assert "X-API-Status" in response.headers
```

## See Also

- [API Response Schemas](../schemas/README.md)
- [Versioning Middleware](../middleware/versioning.py)
- [Authentication Documentation](../../auth/README.md)
- [Rate Limiting](../middleware/rate_limit.py)
