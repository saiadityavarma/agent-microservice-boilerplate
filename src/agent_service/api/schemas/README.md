# API Response Schemas

This directory contains standard response schemas and models for consistent API responses across all endpoints.

## Overview

The schemas provide:
- **Standard response wrappers** for success and error responses
- **Pagination support** with consistent metadata
- **Error handling** with structured error codes and field-level details
- **Type safety** with Pydantic models and generics

## Modules

### `base.py` - Standard Response Wrappers

Contains the core response schemas that wrap all API responses:

#### `ResponseMeta`
Metadata included in all responses:
```python
{
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-12-13T10:30:00Z",
    "version": "v1"
}
```

#### `SuccessResponse[T]`
Wrapper for successful responses:
```python
{
    "success": true,
    "data": { ... },  # Your response data
    "meta": { ... }   # ResponseMeta
}
```

**Example usage:**
```python
from agent_service.api.schemas import SuccessResponse, ResponseMeta

@router.get("/items/{item_id}")
async def get_item(item_id: str) -> SuccessResponse[ItemResponse]:
    item = await db.get_item(item_id)
    return SuccessResponse(
        data=item,
        meta=ResponseMeta(request_id=request.state.request_id)
    )
```

#### `ErrorResponse`
Wrapper for error responses:
```python
{
    "success": false,
    "error": {
        "code": "NOT_FOUND",
        "message": "Resource not found",
        "details": [...]  # Optional field errors
    },
    "meta": { ... }
}
```

**Example usage:**
```python
from agent_service.api.schemas import ErrorResponse, ErrorDetail, ErrorCode

raise HTTPException(
    status_code=404,
    detail=ErrorDetail(
        code=ErrorCode.NOT_FOUND,
        message="Item not found"
    ).model_dump()
)
```

### `pagination.py` - Pagination Support

Contains schemas for paginated list responses:

#### `PaginationParams`
Query parameters for pagination (use as FastAPI dependency):
```python
class PaginationParams:
    page: int = 1              # Page number (1-indexed)
    page_size: int = 20        # Items per page (max 100)
    sort_by: str | None = None # Field to sort by
    sort_order: "asc" | "desc" = "desc"
```

**Example usage:**
```python
from fastapi import Depends
from agent_service.api.schemas import PaginationParams

@router.get("/items")
async def list_items(
    pagination: PaginationParams = Depends()
):
    # Access pagination.page, pagination.page_size, etc.
    items = await db.query(...).offset(pagination.offset).limit(pagination.limit)
    ...
```

#### `PaginationMeta`
Pagination metadata in responses:
```python
{
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5,
    "has_next": true,
    "has_prev": false
}
```

#### `PaginatedResponse[T]`
Wrapper for paginated list responses:
```python
{
    "items": [...],      # List of items
    "pagination": {...}  # PaginationMeta
}
```

**Example usage:**
```python
from agent_service.api.schemas import PaginatedResponse, PaginationMeta, PaginationParams

@router.get("/items", response_model=PaginatedResponse[Item])
async def list_items(pagination: PaginationParams = Depends()):
    # Query with pagination
    items = await db.query(...).offset(pagination.offset).limit(pagination.limit)
    total = await db.count(...)

    return PaginatedResponse(
        items=items,
        pagination=PaginationMeta.from_params(pagination, total)
    )
```

### `errors.py` - Error Handling

Contains error codes and error detail schemas:

#### `ErrorCode` (Enum)
Standard error codes categorized by HTTP status:

**Validation Errors (400):**
- `VALIDATION_ERROR` - Input validation failed
- `INVALID_REQUEST` - Invalid request format
- `INVALID_PARAMETER` - Invalid parameter
- `MISSING_FIELD` - Required field missing

**Authentication Errors (401):**
- `UNAUTHORIZED` - Authentication required
- `INVALID_CREDENTIALS` - Invalid credentials
- `TOKEN_EXPIRED` - Token expired
- `TOKEN_INVALID` - Invalid token
- `API_KEY_INVALID` - Invalid API key

**Authorization Errors (403):**
- `FORBIDDEN` - Access forbidden
- `INSUFFICIENT_PERMISSIONS` - Lacking permissions
- `RESOURCE_ACCESS_DENIED` - Resource access denied

**Not Found Errors (404):**
- `NOT_FOUND` - Resource not found
- `ENDPOINT_NOT_FOUND` - Endpoint not found
- `USER_NOT_FOUND` - User not found
- `AGENT_NOT_FOUND` - Agent not found

**Conflict Errors (409):**
- `CONFLICT` - Resource conflict
- `DUPLICATE_RESOURCE` - Resource already exists
- `RESOURCE_LOCKED` - Resource locked

**Rate Limiting (429):**
- `RATE_LIMITED` - Rate limit exceeded
- `QUOTA_EXCEEDED` - Quota exceeded

**Server Errors (500):**
- `INTERNAL_ERROR` - Internal server error
- `DATABASE_ERROR` - Database error
- `EXTERNAL_SERVICE_ERROR` - External service error

**Service Unavailable (503):**
- `SERVICE_UNAVAILABLE` - Service unavailable
- `MAINTENANCE_MODE` - Maintenance mode
- `DATABASE_UNAVAILABLE` - Database unavailable

**Timeout Errors (504):**
- `TIMEOUT` - Request timeout
- `UPSTREAM_TIMEOUT` - Upstream timeout

#### `FieldError`
Field-level error details for validation errors:
```python
{
    "field": "email",
    "message": "Invalid email format",
    "code": "INVALID_EMAIL",
    "value": "not-an-email"
}
```

#### `ErrorDetail`
Structured error information:
```python
{
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
        {
            "field": "email",
            "message": "Invalid email format"
        }
    ],
    "context": {
        "resource_id": "123"
    }
}
```

**Example usage:**
```python
from agent_service.api.schemas import ErrorDetail, ErrorCode, FieldError

# Simple error
error = ErrorDetail(
    code=ErrorCode.NOT_FOUND,
    message="Item not found",
    context={"item_id": item_id}
)

# Validation error with field details
error = ErrorDetail(
    code=ErrorCode.VALIDATION_ERROR,
    message="Request validation failed",
    details=[
        FieldError(
            field="email",
            message="Invalid email format",
            code="INVALID_EMAIL"
        )
    ]
)

# From Pydantic validation error
from pydantic import ValidationError

try:
    MyModel(**data)
except ValidationError as e:
    error = ErrorDetail.from_validation_error(e.errors())

# From exception
try:
    # Some operation
    ...
except ValueError as e:
    error = ErrorDetail.from_exception(e, code=ErrorCode.INVALID_PARAMETER)
```

## Best Practices

### 1. Always Use Response Wrappers

Wrap all API responses in `SuccessResponse` or `ErrorResponse`:

```python
# Good
@router.get("/items/{item_id}", response_model=SuccessResponse[ItemResponse])
async def get_item(item_id: str):
    item = await db.get_item(item_id)
    return SuccessResponse(data=item)

# Avoid - Returning raw data
@router.get("/items/{item_id}")
async def get_item(item_id: str):
    return await db.get_item(item_id)  # Don't do this
```

### 2. Use Standard Error Codes

Always use `ErrorCode` enum values for consistency:

```python
# Good
ErrorDetail(
    code=ErrorCode.NOT_FOUND,
    message="Item not found"
)

# Avoid - String literals
ErrorDetail(
    code="not_found",  # Don't do this
    message="Item not found"
)
```

### 3. Provide Field-Level Errors

For validation errors, include field-level details:

```python
# Good
ErrorDetail(
    code=ErrorCode.VALIDATION_ERROR,
    message="Request validation failed",
    details=[
        FieldError(field="email", message="Invalid format"),
        FieldError(field="age", message="Must be >= 18")
    ]
)

# Avoid - Generic validation error
ErrorDetail(
    code=ErrorCode.VALIDATION_ERROR,
    message="Validation failed"  # Not helpful
)
```

### 4. Use Pagination for Lists

Always paginate list endpoints:

```python
# Good
@router.get("/items", response_model=PaginatedResponse[Item])
async def list_items(pagination: PaginationParams = Depends()):
    items = await db.query(...).offset(pagination.offset).limit(pagination.limit)
    total = await db.count(...)
    return PaginatedResponse(
        items=items,
        pagination=PaginationMeta.from_params(pagination, total)
    )

# Avoid - Returning unbounded lists
@router.get("/items")
async def list_items():
    return await db.query(...)  # Could return millions of items
```

### 5. Include Request ID in Metadata

Always include request ID for tracing:

```python
# Good
@router.get("/items/{item_id}")
async def get_item(item_id: str, request: Request):
    item = await db.get_item(item_id)
    return SuccessResponse(
        data=item,
        meta=ResponseMeta(request_id=request.state.request_id)
    )
```

### 6. Add Context to Errors

Provide helpful context in error responses:

```python
# Good
ErrorDetail(
    code=ErrorCode.RATE_LIMITED,
    message="Rate limit exceeded",
    context={
        "limit": 100,
        "window": "1 hour",
        "retry_after": 3600
    }
)

# Better than
ErrorDetail(
    code=ErrorCode.RATE_LIMITED,
    message="Rate limit exceeded"  # Not actionable
)
```

## Migration Guide

### Migrating Existing Endpoints

To migrate existing endpoints to use the new schemas:

1. **Update response model:**
   ```python
   # Before
   @router.get("/items/{item_id}", response_model=ItemResponse)
   async def get_item(item_id: str):
       return await db.get_item(item_id)

   # After
   @router.get("/items/{item_id}", response_model=SuccessResponse[ItemResponse])
   async def get_item(item_id: str):
       item = await db.get_item(item_id)
       return SuccessResponse(data=item)
   ```

2. **Update error handling:**
   ```python
   # Before
   raise HTTPException(status_code=404, detail="Item not found")

   # After
   from agent_service.api.schemas import ErrorDetail, ErrorCode

   raise HTTPException(
       status_code=404,
       detail=ErrorDetail(
           code=ErrorCode.NOT_FOUND,
           message="Item not found",
           context={"item_id": item_id}
       ).model_dump()
   )
   ```

3. **Add pagination to list endpoints:**
   ```python
   # Before
   @router.get("/items")
   async def list_items():
       return await db.query(...)

   # After
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

## Testing

Example tests for endpoints using these schemas:

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_item_success(client: AsyncClient):
    response = await client.get("/api/v1/items/123")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert "meta" in data
    assert "request_id" in data["meta"]
    assert "timestamp" in data["meta"]

@pytest.mark.asyncio
async def test_get_item_not_found(client: AsyncClient):
    response = await client.get("/api/v1/items/999")
    assert response.status_code == 404

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"
    assert "message" in data["error"]

@pytest.mark.asyncio
async def test_list_items_pagination(client: AsyncClient):
    response = await client.get("/api/v1/items?page=1&page_size=20")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "pagination" in data
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["page_size"] == 20
    assert "total" in data["pagination"]
    assert "has_next" in data["pagination"]
```

## See Also

- [API Versioning Guide](../v1/README.md)
- [Error Handling Middleware](../middleware/errors.py)
- [Request ID Middleware](../middleware/request_id.py)
