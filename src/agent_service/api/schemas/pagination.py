"""Pagination schemas for API responses."""

from typing import Generic, TypeVar, Literal
from pydantic import BaseModel, Field, field_validator


# Type variable for generic paginated items
T = TypeVar("T")


class PaginationParams(BaseModel):
    """
    Query parameters for pagination.

    Use this as a dependency in FastAPI routes to automatically
    validate and parse pagination parameters.

    Example:
        ```python
        from fastapi import Depends

        @router.get("/items")
        async def list_items(
            pagination: PaginationParams = Depends()
        ):
            # Use pagination.page, pagination.page_size, etc.
            ...
        ```

    Query Parameters:
        - page: Page number (1-indexed)
        - page_size: Items per page (max 100)
        - sort_by: Field name to sort by
        - sort_order: Sort direction (asc or desc)
    """

    model_config = {"str_strip_whitespace": True}

    page: int = Field(
        default=1,
        ge=1,
        description="Page number (1-indexed)",
        examples=[1, 2, 10]
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page (max 100)",
        examples=[20, 50, 100]
    )
    sort_by: str | None = Field(
        default=None,
        description="Field name to sort by",
        examples=["created_at", "name", "updated_at"]
    )
    sort_order: Literal["asc", "desc"] = Field(
        default="desc",
        description="Sort order direction",
        examples=["asc", "desc"]
    )

    @field_validator("page")
    @classmethod
    def validate_page(cls, v: int) -> int:
        """Ensure page is positive."""
        if v < 1:
            raise ValueError("Page must be >= 1")
        return v

    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        """Ensure page_size is within acceptable range."""
        if v < 1:
            raise ValueError("Page size must be >= 1")
        if v > 100:
            raise ValueError("Page size must be <= 100")
        return v

    @property
    def offset(self) -> int:
        """Calculate the offset for database queries."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Get the limit for database queries (alias for page_size)."""
        return self.page_size


class PaginationMeta(BaseModel):
    """
    Pagination metadata included in paginated responses.

    Contains all information needed for pagination UI/logic:
    - Current page and size
    - Total items and pages
    - Navigation flags (has_next, has_prev)
    """

    model_config = {"str_strip_whitespace": True}

    page: int = Field(
        ...,
        ge=1,
        description="Current page number (1-indexed)",
        examples=[1, 2, 10]
    )
    page_size: int = Field(
        ...,
        ge=1,
        le=100,
        description="Items per page",
        examples=[20, 50, 100]
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of items across all pages",
        examples=[0, 100, 1000]
    )
    total_pages: int = Field(
        ...,
        ge=0,
        description="Total number of pages",
        examples=[0, 5, 50]
    )
    has_next: bool = Field(
        ...,
        description="Whether there is a next page",
        examples=[True, False]
    )
    has_prev: bool = Field(
        ...,
        description="Whether there is a previous page",
        examples=[True, False]
    )

    @classmethod
    def from_params(
        cls,
        params: PaginationParams,
        total: int
    ) -> "PaginationMeta":
        """
        Create pagination metadata from params and total count.

        Args:
            params: Pagination parameters from request
            total: Total number of items

        Returns:
            PaginationMeta with calculated values

        Example:
            ```python
            params = PaginationParams(page=2, page_size=20)
            total_items = 100  # From database count

            meta = PaginationMeta.from_params(params, total_items)
            # meta.total_pages = 5
            # meta.has_next = True
            # meta.has_prev = True
            ```
        """
        total_pages = (total + params.page_size - 1) // params.page_size if total > 0 else 0

        return cls(
            page=params.page,
            page_size=params.page_size,
            total=total,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_prev=params.page > 1
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standard paginated response wrapper.

    Wraps list responses with pagination metadata.
    Generic type T represents the item type in the list.

    Example:
        ```python
        from pydantic import BaseModel

        class Item(BaseModel):
            id: str
            name: str

        @router.get("/items", response_model=PaginatedResponse[Item])
        async def list_items(
            pagination: PaginationParams = Depends()
        ):
            # Query database with pagination
            items = await db.query(...).offset(pagination.offset).limit(pagination.limit)
            total = await db.count(...)

            return PaginatedResponse(
                items=items,
                pagination=PaginationMeta.from_params(pagination, total)
            )
        ```

    Example Response:
        ```json
        {
            "items": [
                {"id": "1", "name": "Item 1"},
                {"id": "2", "name": "Item 2"}
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
        ```
    """

    model_config = {"str_strip_whitespace": True}

    items: list[T] = Field(
        ...,
        description="List of items for current page"
    )
    pagination: PaginationMeta = Field(
        ...,
        description="Pagination metadata"
    )
