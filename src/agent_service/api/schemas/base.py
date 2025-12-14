"""Base response schemas for API standardization."""

from datetime import datetime
from typing import Generic, TypeVar, Literal
from uuid import uuid4, UUID

from pydantic import BaseModel, Field


# Type variable for generic response data
T = TypeVar("T")


class ResponseMeta(BaseModel):
    """Metadata included in all API responses."""

    model_config = {"str_strip_whitespace": True}

    request_id: UUID = Field(
        default_factory=uuid4,
        description="Unique request identifier for tracing and debugging",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp in UTC",
        examples=["2024-12-13T10:30:00Z"]
    )
    version: str = Field(
        default="v1",
        description="API version used for this response",
        examples=["v1", "v2"]
    )


class SuccessResponse(BaseModel, Generic[T]):
    """
    Standard success response wrapper.

    Wraps successful API responses with consistent metadata.
    Used for all successful API operations that return data.

    Example:
        ```python
        return SuccessResponse(
            data={"id": "123", "name": "Example"},
            meta=ResponseMeta(request_id=request_id)
        )
        ```

    Example Response:
        ```json
        {
            "success": true,
            "data": {
                "id": "123",
                "name": "Example"
            },
            "meta": {
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2024-12-13T10:30:00Z",
                "version": "v1"
            }
        }
        ```
    """

    model_config = {"str_strip_whitespace": True}

    success: Literal[True] = Field(
        default=True,
        description="Indicates successful response"
    )
    data: T = Field(
        ...,
        description="Response data payload"
    )
    meta: ResponseMeta = Field(
        default_factory=ResponseMeta,
        description="Response metadata"
    )


class ErrorResponse(BaseModel):
    """
    Standard error response wrapper.

    Wraps error responses with consistent structure and metadata.
    Used for all API errors and exceptions.

    Example:
        ```python
        from agent_service.api.schemas.errors import ErrorDetail, ErrorCode

        return ErrorResponse(
            error=ErrorDetail(
                code=ErrorCode.NOT_FOUND,
                message="Resource not found",
                details=[{"field": "id", "message": "Invalid ID format"}]
            ),
            meta=ResponseMeta(request_id=request_id)
        )
        ```

    Example Response:
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
                ]
            },
            "meta": {
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2024-12-13T10:30:00Z",
                "version": "v1"
            }
        }
        ```
    """

    model_config = {"str_strip_whitespace": True}

    success: Literal[False] = Field(
        default=False,
        description="Indicates error response"
    )
    error: "ErrorDetail" = Field(
        ...,
        description="Error details"
    )
    meta: ResponseMeta = Field(
        default_factory=ResponseMeta,
        description="Response metadata"
    )


# Import ErrorDetail for forward reference resolution
from agent_service.api.schemas.errors import ErrorDetail  # noqa: E402

# Update forward references
ErrorResponse.model_rebuild()
