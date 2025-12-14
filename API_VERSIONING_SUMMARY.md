# API Versioning and Standard Response Schemas - Implementation Summary

## Overview

This implementation provides a complete API versioning system with standard response schemas for consistent API responses across all endpoints.

## Files Created

### 1. Standard Response Schemas (`/src/agent_service/api/schemas/`)

- **`__init__.py`** - Package exports
- **`base.py`** - Core response wrappers:
  - `ResponseMeta` - Metadata for all responses (request_id, timestamp, version)
  - `SuccessResponse[T]` - Generic success response wrapper
  - `ErrorResponse` - Error response wrapper

- **`pagination.py`** - Pagination support:
  - `PaginationParams` - Query parameter model for pagination
  - `PaginationMeta` - Pagination metadata in responses
  - `PaginatedResponse[T]` - Generic paginated list wrapper

- **`errors.py`** - Error handling:
  - `ErrorCode` - Enum of standard error codes (40+ codes)
  - `FieldError` - Field-level validation error details
  - `ErrorDetail` - Structured error information

- **`examples.py`** - Comprehensive usage examples
- **`README.md`** - Complete documentation with examples

### 2. API v1 Structure (`/src/agent_service/api/v1/`)

- **`__init__.py`** - Package exports
- **`router.py`** - Aggregates all v1 routes:
  - `/agents` - Agent invocation endpoints
  - `/auth/api-keys` - API key management
  - `/protocols` - Protocol handlers (A2A, MCP)
  - `/admin/audit` - Audit log queries (admin only)
- **`README.md`** - Complete v1 API documentation

### 3. Versioning Middleware (`/src/agent_service/api/middleware/`)

- **`versioning.py`** - API versioning middleware:
  - Adds version headers to responses (`X-API-Version`, `X-API-Status`)
  - Deprecation support with RFC 8594 headers
  - Version configuration management
  - Sunset date handling

### 4. Updated Files

- **`api/app.py`** - Updated to mount versioned routers:
  - Root level: `/health/*`, `/auth/me`, `/auth/permissions`, `/auth/validate`
  - Versioned: `/api/v1/*` (all business endpoints)
  - Added versioning middleware

- **`api/routes/auth.py`** - Removed hardcoded `/api/v1` prefix from api_keys_router
- **`api/routes/audit.py`** - Removed hardcoded `/api/v1/admin` prefix
- **`api/routes/agents.py`** - Already clean (no changes needed)
- **`api/routes/protocols.py`** - Already clean (no changes needed)

## API Structure

```
Root Level (Unversioned):
├── /health/live              # Liveness probe
├── /health/ready             # Readiness probe
├── /health/startup           # Startup probe
├── /health                   # Detailed health check
├── /metrics                  # Prometheus metrics
├── /auth/me                  # Current user info
├── /auth/permissions         # User permissions
└── /auth/validate            # Token validation

Versioned (/api/v1/):
├── /agents/
│   ├── POST /invoke         # Sync invocation
│   └── POST /stream         # Streaming invocation
├── /auth/api-keys/
│   ├── POST /               # Create API key
│   ├── GET /                # List API keys
│   ├── GET /{key_id}        # Get API key
│   ├── DELETE /{key_id}     # Revoke API key
│   └── POST /{key_id}/rotate # Rotate API key
├── /protocols/
│   ├── POST /{protocol}/invoke
│   └── POST /{protocol}/stream
└── /admin/audit/
    ├── GET /                # Query audit logs
    ├── GET /{audit_id}      # Get audit log
    └── GET /stats/summary   # Audit statistics
```

## Response Formats

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
        "message": "Invalid ID format",
        "code": "INVALID_FORMAT"
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

## Version Headers

All v1 API responses include:

```http
X-API-Version: v1
X-API-Status: stable
```

When deprecated:

```http
X-API-Version: v1
X-API-Status: deprecated
X-API-Deprecated: true
Deprecation: @1672531200
Sunset: Sat, 01 Jul 2025 00:00:00 GMT
Link: <https://docs.example.com/api/v1-migration>; rel="deprecation"
```

## Usage Examples

### 1. Simple Endpoint

```python
from agent_service.api.schemas import SuccessResponse, ResponseMeta

@router.get("/items/{item_id}", response_model=SuccessResponse[Item])
async def get_item(item_id: str, request: Request):
    item = await db.get_item(item_id)
    return SuccessResponse(
        data=item,
        meta=ResponseMeta(request_id=request.state.request_id)
    )
```

### 2. Paginated List

```python
from agent_service.api.schemas import PaginatedResponse, PaginationParams, PaginationMeta

@router.get("/items", response_model=PaginatedResponse[Item])
async def list_items(pagination: PaginationParams = Depends()):
    items = await db.query(...).offset(pagination.offset).limit(pagination.limit)
    total = await db.count(...)
    return PaginatedResponse(
        items=items,
        pagination=PaginationMeta.from_params(pagination, total)
    )
```

### 3. Error Handling

```python
from agent_service.api.schemas import ErrorDetail, ErrorCode, FieldError

# Not found
raise HTTPException(
    status_code=404,
    detail=ErrorDetail(
        code=ErrorCode.NOT_FOUND,
        message="Item not found",
        context={"item_id": item_id}
    ).model_dump()
)

# Validation error with field details
raise HTTPException(
    status_code=400,
    detail=ErrorDetail(
        code=ErrorCode.VALIDATION_ERROR,
        message="Request validation failed",
        details=[
            FieldError(field="email", message="Invalid format")
        ]
    ).model_dump()
)
```

## Error Codes

Standard error codes are organized by HTTP status:

- **400** - `VALIDATION_ERROR`, `INVALID_REQUEST`, `INVALID_PARAMETER`, `MISSING_FIELD`
- **401** - `UNAUTHORIZED`, `INVALID_CREDENTIALS`, `TOKEN_EXPIRED`, `TOKEN_INVALID`, `API_KEY_INVALID`
- **403** - `FORBIDDEN`, `INSUFFICIENT_PERMISSIONS`, `RESOURCE_ACCESS_DENIED`
- **404** - `NOT_FOUND`, `ENDPOINT_NOT_FOUND`, `USER_NOT_FOUND`, `AGENT_NOT_FOUND`
- **409** - `CONFLICT`, `DUPLICATE_RESOURCE`, `RESOURCE_LOCKED`
- **429** - `RATE_LIMITED`, `QUOTA_EXCEEDED`
- **500** - `INTERNAL_ERROR`, `DATABASE_ERROR`, `EXTERNAL_SERVICE_ERROR`
- **503** - `SERVICE_UNAVAILABLE`, `MAINTENANCE_MODE`, `DATABASE_UNAVAILABLE`
- **504** - `TIMEOUT`, `UPSTREAM_TIMEOUT`

## Adding New Versions

To add v2 in the future:

1. Create `/api/v2/router.py`
2. Update versioning middleware:

```python
API_VERSIONS = {
    "v1": {
        "status": "deprecated",
        "deprecated": True,
        "deprecation_date": "2025-01-01T00:00:00Z",
        "sunset_date": "2025-07-01T00:00:00Z",
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

3. Mount in `app.py`:

```python
from agent_service.api import v1, v2

app.include_router(v1.router, prefix="/api/v1")
app.include_router(v2.router, prefix="/api/v2")
```

## Benefits

1. **Consistency** - All endpoints use the same response format
2. **Type Safety** - Full Pydantic validation and type hints
3. **Client-Friendly** - Structured errors with field-level details
4. **Versioning** - Built-in support for API versioning and deprecation
5. **Pagination** - Standard pagination pattern across all list endpoints
6. **Traceability** - Request IDs in all responses for debugging
7. **Documentation** - Auto-generated OpenAPI docs with proper schemas
8. **Maintainability** - Easy to extend and modify

## Documentation

- [Response Schemas Documentation](src/agent_service/api/schemas/README.md)
- [v1 API Documentation](src/agent_service/api/v1/README.md)
- [Usage Examples](src/agent_service/api/schemas/examples.py)
- [Versioning Middleware](src/agent_service/api/middleware/versioning.py)

## Testing

All endpoints can be tested with standard patterns:

```python
@pytest.mark.asyncio
async def test_endpoint_success(client: AsyncClient):
    response = await client.get("/api/v1/items/123")
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert "meta" in data
    assert data["meta"]["version"] == "v1"

@pytest.mark.asyncio
async def test_endpoint_error(client: AsyncClient):
    response = await client.get("/api/v1/items/999")
    assert response.status_code == 404
    
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"
```

## Next Steps

1. Update existing endpoints to use new response schemas
2. Add integration tests for versioning
3. Configure migration guide URLs for deprecation
4. Add monitoring for deprecated API usage
5. Document migration guides for clients
