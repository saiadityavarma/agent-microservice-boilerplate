"""
Examples of using standard response schemas.

This module demonstrates best practices for using the API response schemas.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from agent_service.api.schemas import (
    SuccessResponse,
    ErrorResponse,
    PaginatedResponse,
    PaginationParams,
    PaginationMeta,
    ErrorDetail,
    ErrorCode,
    FieldError,
    ResponseMeta,
)


# Example router
router = APIRouter(prefix="/examples", tags=["Examples"])


# ============================================================================
# Example Models
# ============================================================================


class Item(BaseModel):
    """Example item model."""
    id: str
    name: str
    description: str | None = None
    price: float


class ItemCreate(BaseModel):
    """Example item creation model."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    price: float = Field(..., gt=0)


# ============================================================================
# Example 1: Simple Success Response
# ============================================================================


@router.get(
    "/items/{item_id}",
    response_model=SuccessResponse[Item],
    summary="Get item by ID"
)
async def get_item(item_id: str, request: Request) -> SuccessResponse[Item]:
    """
    Example: Return a single item wrapped in SuccessResponse.

    This shows the basic pattern for returning data with metadata.
    """
    # Simulate database lookup
    if item_id == "999":
        # Example: Raising an error (see example 4 for error handling)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code=ErrorCode.NOT_FOUND,
                message="Item not found",
                context={"item_id": item_id}
            ).model_dump()
        )

    # Return success response
    item = Item(
        id=item_id,
        name="Example Item",
        description="This is an example item",
        price=99.99
    )

    return SuccessResponse(
        data=item,
        meta=ResponseMeta(
            request_id=request.state.request_id if hasattr(request.state, "request_id") else None
        )
    )


# ============================================================================
# Example 2: Paginated List Response
# ============================================================================


@router.get(
    "/items",
    response_model=PaginatedResponse[Item],
    summary="List items with pagination"
)
async def list_items(
    pagination: PaginationParams = Depends()
) -> PaginatedResponse[Item]:
    """
    Example: Return paginated list of items.

    This shows how to use PaginationParams and PaginatedResponse.
    Query parameters: ?page=1&page_size=20&sort_by=name&sort_order=asc
    """
    # Simulate database query with pagination
    # In real code, use pagination.offset and pagination.limit:
    # items = await db.query(...).offset(pagination.offset).limit(pagination.limit)

    # Mock data
    all_items = [
        Item(id=f"item-{i}", name=f"Item {i}", price=float(i * 10))
        for i in range(1, 101)
    ]

    # Apply pagination
    start = pagination.offset
    end = start + pagination.limit
    paginated_items = all_items[start:end]

    # Get total count
    total = len(all_items)

    return PaginatedResponse(
        items=paginated_items,
        pagination=PaginationMeta.from_params(pagination, total)
    )


# ============================================================================
# Example 3: Create with Validation
# ============================================================================


@router.post(
    "/items",
    response_model=SuccessResponse[Item],
    status_code=status.HTTP_201_CREATED,
    summary="Create new item"
)
async def create_item(
    item_data: ItemCreate,
    request: Request
) -> SuccessResponse[Item]:
    """
    Example: Create item with validation.

    Shows automatic Pydantic validation and success response.
    Validation errors are automatically converted to error responses.
    """
    # Pydantic automatically validates:
    # - name is 1-100 characters
    # - description is max 500 characters
    # - price is greater than 0

    # Simulate creating item
    new_item = Item(
        id="new-123",
        name=item_data.name,
        description=item_data.description,
        price=item_data.price
    )

    return SuccessResponse(
        data=new_item,
        meta=ResponseMeta(
            request_id=request.state.request_id if hasattr(request.state, "request_id") else None
        )
    )


# ============================================================================
# Example 4: Error Handling - Not Found
# ============================================================================


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete item"
)
async def delete_item(item_id: str):
    """
    Example: Handle not found error.

    Shows how to raise HTTPException with structured error.
    """
    # Simulate database lookup
    item_exists = item_id != "999"

    if not item_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code=ErrorCode.NOT_FOUND,
                message=f"Item with ID {item_id} not found",
                context={"item_id": item_id}
            ).model_dump()
        )

    # Simulate deletion
    return None


# ============================================================================
# Example 5: Error Handling - Validation Error with Field Details
# ============================================================================


@router.put(
    "/items/{item_id}",
    response_model=SuccessResponse[Item],
    summary="Update item"
)
async def update_item(
    item_id: str,
    item_data: ItemCreate,
    request: Request
) -> SuccessResponse[Item]:
    """
    Example: Custom validation with field-level errors.

    Shows how to provide detailed field errors for validation failures.
    """
    # Custom validation (beyond Pydantic)
    errors = []

    # Check for profanity (example custom validation)
    if "bad_word" in item_data.name.lower():
        errors.append(
            FieldError(
                field="name",
                message="Name contains inappropriate content",
                code="INAPPROPRIATE_CONTENT",
                value=item_data.name
            )
        )

    # Check business rule (example)
    if item_data.price > 10000:
        errors.append(
            FieldError(
                field="price",
                message="Price exceeds maximum allowed value of 10000",
                code="VALUE_OUT_OF_RANGE",
                value=item_data.price
            )
        )

    # If validation errors, raise HTTPException
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorDetail(
                code=ErrorCode.VALIDATION_ERROR,
                message="Request validation failed",
                details=errors
            ).model_dump()
        )

    # Update item
    updated_item = Item(
        id=item_id,
        name=item_data.name,
        description=item_data.description,
        price=item_data.price
    )

    return SuccessResponse(
        data=updated_item,
        meta=ResponseMeta(
            request_id=request.state.request_id if hasattr(request.state, "request_id") else None
        )
    )


# ============================================================================
# Example 6: Error Handling - From Exception
# ============================================================================


@router.post(
    "/items/{item_id}/process",
    response_model=SuccessResponse[dict],
    summary="Process item"
)
async def process_item(item_id: str, request: Request) -> SuccessResponse[dict]:
    """
    Example: Convert exceptions to structured errors.

    Shows how to handle exceptions and convert them to ErrorDetail.
    """
    try:
        # Simulate some processing that might fail
        if item_id == "error":
            raise ValueError("Invalid item ID format")

        # Simulate processing
        result = {"status": "processed", "item_id": item_id}

        return SuccessResponse(
            data=result,
            meta=ResponseMeta(
                request_id=request.state.request_id if hasattr(request.state, "request_id") else None
            )
        )

    except ValueError as e:
        # Convert exception to structured error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorDetail.from_exception(
                e,
                code=ErrorCode.INVALID_PARAMETER
            ).model_dump()
        )
    except Exception as e:
        # Catch-all for unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorDetail.from_exception(
                e,
                code=ErrorCode.INTERNAL_ERROR
            ).model_dump()
        )


# ============================================================================
# Example 7: Error Handling - Conflict
# ============================================================================


@router.post(
    "/items/{item_id}/duplicate",
    response_model=SuccessResponse[Item],
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate item"
)
async def duplicate_item(
    item_id: str,
    request: Request
) -> SuccessResponse[Item]:
    """
    Example: Handle conflict errors.

    Shows how to return conflict error when resource already exists.
    """
    # Simulate checking if duplicate already exists
    duplicate_exists = item_id == "duplicate-me"

    if duplicate_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ErrorDetail(
                code=ErrorCode.DUPLICATE_RESOURCE,
                message="Duplicate of this item already exists",
                context={
                    "item_id": item_id,
                    "existing_duplicate_id": f"{item_id}-copy"
                }
            ).model_dump()
        )

    # Create duplicate
    duplicate = Item(
        id=f"{item_id}-copy",
        name=f"Copy of Item {item_id}",
        price=99.99
    )

    return SuccessResponse(
        data=duplicate,
        meta=ResponseMeta(
            request_id=request.state.request_id if hasattr(request.state, "request_id") else None
        )
    )


# ============================================================================
# Example 8: Error Handling - Rate Limiting
# ============================================================================


@router.post(
    "/items/{item_id}/expensive-operation",
    response_model=SuccessResponse[dict],
    summary="Expensive operation (rate limited)"
)
async def expensive_operation(
    item_id: str,
    request: Request
) -> SuccessResponse[dict]:
    """
    Example: Handle rate limiting errors.

    Shows how to return rate limit error with retry information.
    """
    # Simulate rate limit check (in real code, use rate limiting middleware)
    is_rate_limited = False  # Replace with actual check

    if is_rate_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorDetail(
                code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded. Please try again later.",
                context={
                    "limit": 100,
                    "window": "1 hour",
                    "retry_after": 3600  # seconds
                }
            ).model_dump(),
            headers={"Retry-After": "3600"}
        )

    # Perform operation
    result = {"status": "completed", "item_id": item_id}

    return SuccessResponse(
        data=result,
        meta=ResponseMeta(
            request_id=request.state.request_id if hasattr(request.state, "request_id") else None
        )
    )


# ============================================================================
# Example Response Samples
# ============================================================================

"""
Example Success Response:
{
    "success": true,
    "data": {
        "id": "item-1",
        "name": "Example Item",
        "description": "This is an example",
        "price": 99.99
    },
    "meta": {
        "request_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2024-12-13T10:30:00Z",
        "version": "v1"
    }
}

Example Paginated Response:
{
    "items": [
        {"id": "item-1", "name": "Item 1", "price": 10.0},
        {"id": "item-2", "name": "Item 2", "price": 20.0}
    ],
    "pagination": {
        "page": 1,
        "page_size": 20,
        "total": 100,
        "total_pages": 5,
        "has_next": true,
        "has_prev": false
    }
}

Example Error Response (Not Found):
{
    "success": false,
    "error": {
        "code": "NOT_FOUND",
        "message": "Item with ID 999 not found",
        "details": null,
        "context": {
            "item_id": "999"
        }
    },
    "meta": {
        "request_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2024-12-13T10:30:00Z",
        "version": "v1"
    }
}

Example Error Response (Validation):
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Request validation failed",
        "details": [
            {
                "field": "name",
                "message": "Name contains inappropriate content",
                "code": "INAPPROPRIATE_CONTENT",
                "value": "bad_word item"
            },
            {
                "field": "price",
                "message": "Price exceeds maximum allowed value of 10000",
                "code": "VALUE_OUT_OF_RANGE",
                "value": 15000.0
            }
        ],
        "context": null
    },
    "meta": {
        "request_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2024-12-13T10:30:00Z",
        "version": "v1"
    }
}

Example Error Response (Rate Limited):
{
    "success": false,
    "error": {
        "code": "RATE_LIMITED",
        "message": "Rate limit exceeded. Please try again later.",
        "details": null,
        "context": {
            "limit": 100,
            "window": "1 hour",
            "retry_after": 3600
        }
    },
    "meta": {
        "request_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2024-12-13T10:30:00Z",
        "version": "v1"
    }
}
"""
