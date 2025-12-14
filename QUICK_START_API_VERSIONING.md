# Quick Start: API Versioning and Response Schemas

This guide shows you how to quickly start using the new API versioning and response schemas.

## TL;DR

All your routes should now:
1. Be under `/api/v1/` (except health and auth info endpoints)
2. Return `SuccessResponse[YourModel]` for successful responses
3. Use `ErrorDetail` with `ErrorCode` for errors
4. Use `PaginatedResponse[YourModel]` for lists

## Import What You Need

```python
from agent_service.api.schemas import (
    # Success responses
    SuccessResponse,
    ResponseMeta,

    # Pagination
    PaginatedResponse,
    PaginationParams,
    PaginationMeta,

    # Errors
    ErrorDetail,
    ErrorCode,
    FieldError,
)
```

## Quick Examples

### 1. Simple GET endpoint

```python
from fastapi import APIRouter, Request
from agent_service.api.schemas import SuccessResponse, ResponseMeta

router = APIRouter()

@router.get("/items/{item_id}", response_model=SuccessResponse[Item])
async def get_item(item_id: str, request: Request):
    item = await db.get_item(item_id)
    return SuccessResponse(
        data=item,
        meta=ResponseMeta(request_id=request.state.request_id)
    )
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "123",
    "name": "Example Item"
  },
  "meta": {
    "request_id": "550e8400-...",
    "timestamp": "2024-12-13T10:30:00Z",
    "version": "v1"
  }
}
```

### 2. List endpoint with pagination

```python
from fastapi import Depends
from agent_service.api.schemas import (
    PaginatedResponse,
    PaginationParams,
    PaginationMeta,
)

@router.get("/items", response_model=PaginatedResponse[Item])
async def list_items(pagination: PaginationParams = Depends()):
    # Use pagination.offset and pagination.limit for DB query
    items = await db.query(...).offset(pagination.offset).limit(pagination.limit)
    total = await db.count(...)

    return PaginatedResponse(
        items=items,
        pagination=PaginationMeta.from_params(pagination, total)
    )
```

**Request:**
```
GET /api/v1/items?page=1&page_size=20&sort_by=name&sort_order=asc
```

**Response:**
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

### 3. Error handling

```python
from fastapi import HTTPException, status
from agent_service.api.schemas import ErrorDetail, ErrorCode

# Not found error
if not item:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=ErrorDetail(
            code=ErrorCode.NOT_FOUND,
            message="Item not found",
            context={"item_id": item_id}
        ).model_dump()
    )

# Validation error
from agent_service.api.schemas import FieldError

raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail=ErrorDetail(
        code=ErrorCode.VALIDATION_ERROR,
        message="Request validation failed",
        details=[
            FieldError(
                field="email",
                message="Invalid email format",
                code="INVALID_EMAIL"
            )
        ]
    ).model_dump()
)
```

**Error Response:**
```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Item not found",
    "context": {
      "item_id": "123"
    }
  },
  "meta": {
    "request_id": "550e8400-...",
    "timestamp": "2024-12-13T10:30:00Z",
    "version": "v1"
  }
}
```

## Adding Your Route to v1

1. Create your route file in `/src/agent_service/api/routes/`:

```python
# src/agent_service/api/routes/my_feature.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/hello")
async def hello():
    return {"message": "Hello!"}
```

2. Add it to v1 router in `/src/agent_service/api/v1/router.py`:

```python
from agent_service.api.routes import my_feature

router.include_router(
    my_feature.router,
    prefix="/my-feature",
    tags=["My Feature"]
)
```

3. Your endpoint is now available at: `/api/v1/my-feature/hello`

## Common Error Codes

Use these standard error codes:

```python
from agent_service.api.schemas import ErrorCode

# 400 - Bad Request
ErrorCode.VALIDATION_ERROR      # Input validation failed
ErrorCode.INVALID_REQUEST       # Invalid request format
ErrorCode.INVALID_PARAMETER     # Invalid parameter

# 401 - Unauthorized
ErrorCode.UNAUTHORIZED          # Authentication required
ErrorCode.TOKEN_EXPIRED         # Token expired
ErrorCode.API_KEY_INVALID       # Invalid API key

# 403 - Forbidden
ErrorCode.FORBIDDEN             # Access forbidden
ErrorCode.INSUFFICIENT_PERMISSIONS  # Lacking permissions

# 404 - Not Found
ErrorCode.NOT_FOUND            # Resource not found
ErrorCode.USER_NOT_FOUND       # User not found
ErrorCode.AGENT_NOT_FOUND      # Agent not found

# 409 - Conflict
ErrorCode.CONFLICT             # Resource conflict
ErrorCode.DUPLICATE_RESOURCE   # Already exists

# 429 - Rate Limited
ErrorCode.RATE_LIMITED         # Rate limit exceeded

# 500 - Server Error
ErrorCode.INTERNAL_ERROR       # Internal error
ErrorCode.DATABASE_ERROR       # Database error

# 503 - Service Unavailable
ErrorCode.SERVICE_UNAVAILABLE  # Service down
```

## Pagination Parameters

When using `PaginationParams`, clients can use:

```
GET /api/v1/items?page=2&page_size=50&sort_by=created_at&sort_order=desc
```

In your code:
```python
pagination.page        # 2
pagination.page_size   # 50
pagination.sort_by     # "created_at"
pagination.sort_order  # "desc"
pagination.offset      # 50 (calculated automatically)
pagination.limit       # 50 (alias for page_size)
```

## Response Headers

All v1 endpoints automatically include:

```http
X-API-Version: v1
X-API-Status: stable
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

## Unversioned vs Versioned Routes

**Unversioned (Root Level):**
- Health checks: `/health/*`
- User info: `/auth/me`, `/auth/permissions`
- Token validation: `/auth/validate`

**Versioned (`/api/v1/`):**
- All business endpoints
- Agent operations
- API key management
- Protocol handlers
- Admin operations

## Complete Example

Here's a complete CRUD endpoint:

```python
from fastapi import APIRouter, Depends, HTTPException, Request, status
from agent_service.api.schemas import (
    SuccessResponse,
    PaginatedResponse,
    PaginationParams,
    PaginationMeta,
    ResponseMeta,
    ErrorDetail,
    ErrorCode,
)

router = APIRouter()

# List
@router.get("/items", response_model=PaginatedResponse[Item])
async def list_items(pagination: PaginationParams = Depends()):
    items = await db.query(...).offset(pagination.offset).limit(pagination.limit)
    total = await db.count(...)
    return PaginatedResponse(
        items=items,
        pagination=PaginationMeta.from_params(pagination, total)
    )

# Get
@router.get("/items/{item_id}", response_model=SuccessResponse[Item])
async def get_item(item_id: str, request: Request):
    item = await db.get_item(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code=ErrorCode.NOT_FOUND,
                message="Item not found"
            ).model_dump()
        )
    return SuccessResponse(
        data=item,
        meta=ResponseMeta(request_id=request.state.request_id)
    )

# Create
@router.post("/items", response_model=SuccessResponse[Item], status_code=status.HTTP_201_CREATED)
async def create_item(item_data: ItemCreate, request: Request):
    item = await db.create_item(item_data)
    return SuccessResponse(
        data=item,
        meta=ResponseMeta(request_id=request.state.request_id)
    )

# Update
@router.put("/items/{item_id}", response_model=SuccessResponse[Item])
async def update_item(item_id: str, item_data: ItemUpdate, request: Request):
    item = await db.update_item(item_id, item_data)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code=ErrorCode.NOT_FOUND,
                message="Item not found"
            ).model_dump()
        )
    return SuccessResponse(
        data=item,
        meta=ResponseMeta(request_id=request.state.request_id)
    )

# Delete
@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: str):
    success = await db.delete_item(item_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code=ErrorCode.NOT_FOUND,
                message="Item not found"
            ).model_dump()
        )
```

## More Information

- Full documentation: [API_VERSIONING_SUMMARY.md](API_VERSIONING_SUMMARY.md)
- Response schemas guide: [src/agent_service/api/schemas/README.md](src/agent_service/api/schemas/README.md)
- v1 API docs: [src/agent_service/api/v1/README.md](src/agent_service/api/v1/README.md)
- Complete examples: [src/agent_service/api/schemas/examples.py](src/agent_service/api/schemas/examples.py)
