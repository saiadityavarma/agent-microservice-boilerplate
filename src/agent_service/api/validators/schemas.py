"""
Pydantic base schemas with strict validation and sanitization.

Provides custom Pydantic models and field types that automatically
sanitize input and enforce security constraints.
"""

from typing import Annotated, Any, Optional
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
    BeforeValidator,
    AfterValidator,
)

from .sanitizers import (
    sanitize_html,
    normalize_whitespace,
    strip_null_bytes,
    truncate_string,
)
from .validators import (
    validate_prompt_injection,
    validate_no_scripts,
    validate_safe_path,
    validate_uuid,
    validate_email,
    validate_url,
    validate_length,
)


class StrictBaseModel(BaseModel):
    """
    Base model with strict validation enabled.

    Features:
    - Strict type validation (no coercion)
    - Forbid extra fields
    - Validate default values
    - Validate assignments after model creation
    """

    model_config = ConfigDict(
        # Strict mode: no type coercion
        strict=True,
        # Don't allow extra fields
        extra='forbid',
        # Validate default values
        validate_default=True,
        # Validate on assignment (after model creation)
        validate_assignment=True,
        # Use enum values instead of raw values
        use_enum_values=True,
        # Populate models by field name
        populate_by_name=True,
    )


class PermissiveBaseModel(BaseModel):
    """
    Base model with permissive validation but with sanitization.

    Use this when you need to accept various input types but still
    want sanitization and security checks.
    """

    model_config = ConfigDict(
        # Allow type coercion
        strict=False,
        # Don't allow extra fields
        extra='forbid',
        # Validate default values
        validate_default=True,
        # Validate on assignment
        validate_assignment=True,
        # Strip whitespace from strings
        str_strip_whitespace=True,
        # Populate by field name
        populate_by_name=True,
    )


# Custom validation functions for use with Annotated types
def _sanitize_html_validator(v: Any) -> str:
    """Validator to sanitize HTML from string input."""
    if not isinstance(v, str):
        return v
    return sanitize_html(v)


def _normalize_whitespace_validator(v: Any) -> str:
    """Validator to normalize whitespace in string input."""
    if not isinstance(v, str):
        return v
    return normalize_whitespace(v)


def _strip_null_bytes_validator(v: Any) -> str:
    """Validator to remove null bytes from string input."""
    if not isinstance(v, str):
        return v
    return strip_null_bytes(v)


def _validate_no_prompt_injection(v: Any) -> str:
    """Validator to check for prompt injection patterns."""
    if not isinstance(v, str):
        return v
    if not validate_prompt_injection(v, strict=True):
        raise ValueError("Potential prompt injection detected")
    return v


def _validate_no_scripts_validator(v: Any) -> str:
    """Validator to check for script tags and event handlers."""
    if not isinstance(v, str):
        return v
    if not validate_no_scripts(v):
        raise ValueError("Script tags or event handlers not allowed")
    return v


# Custom string types with automatic sanitization
SanitizedString = Annotated[
    str,
    BeforeValidator(_strip_null_bytes_validator),
    BeforeValidator(_sanitize_html_validator),
    BeforeValidator(_normalize_whitespace_validator),
]
"""String type that automatically sanitizes HTML, null bytes, and whitespace."""


SafeText = Annotated[
    str,
    BeforeValidator(_strip_null_bytes_validator),
    BeforeValidator(_normalize_whitespace_validator),
    AfterValidator(_validate_no_prompt_injection),
]
"""String type that checks for prompt injection patterns."""


NoScriptString = Annotated[
    str,
    BeforeValidator(_strip_null_bytes_validator),
    AfterValidator(_validate_no_scripts_validator),
]
"""String type that rejects script tags and event handlers."""


def BoundedString(
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    pattern: Optional[str] = None,
) -> type[str]:
    """
    Create a string type with length constraints.

    Args:
        min_length: Minimum string length
        max_length: Maximum string length
        pattern: Regex pattern to match

    Returns:
        Annotated string type with constraints

    Example:
        >>> Username = BoundedString(min_length=3, max_length=32)
        >>> class User(StrictBaseModel):
        ...     username: Username
    """
    return Annotated[
        str,
        Field(
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
        ),
    ]


# Common bounded string types
Username = BoundedString(min_length=3, max_length=32, pattern=r'^[a-zA-Z0-9_-]+$')
"""Username with 3-32 chars, alphanumeric plus underscore and hyphen."""

Email = Annotated[
    str,
    Field(pattern=r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$'),
]
"""Email address string type."""

UUID = Annotated[
    str,
    Field(
        pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
    ),
]
"""UUID string type."""

Url = Annotated[
    str,
    Field(pattern=r'^https?://[^\s/$.?#].[^\s]*$'),
]
"""HTTP/HTTPS URL string type."""


class ValidatedTextInput(PermissiveBaseModel):
    """
    Schema for text input with comprehensive validation.

    Use this for user-provided text that will be processed by LLMs
    or stored in the database.
    """

    text: SafeText = Field(
        ...,
        description="Text input with prompt injection protection",
        min_length=1,
        max_length=10000,
    )

    @field_validator('text')
    @classmethod
    def validate_text_content(cls, v: str) -> str:
        """Additional text validation."""
        # Ensure not just whitespace
        if not v.strip():
            raise ValueError("Text cannot be empty or only whitespace")

        # Check for excessive length
        if len(v) > 10000:
            raise ValueError("Text exceeds maximum length of 10000 characters")

        return v


class SanitizedHtmlInput(PermissiveBaseModel):
    """
    Schema for HTML input with sanitization.

    Automatically sanitizes HTML tags while preserving content.
    """

    content: SanitizedString = Field(
        ...,
        description="HTML content (will be sanitized)",
        max_length=50000,
    )

    @field_validator('content')
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        """Ensure content is not empty after sanitization."""
        if not v.strip():
            raise ValueError("Content cannot be empty after sanitization")
        return v


class SafePathInput(StrictBaseModel):
    """
    Schema for file path input with path traversal protection.
    """

    path: str = Field(
        ...,
        description="File path (relative, no path traversal)",
        max_length=500,
    )

    @field_validator('path')
    @classmethod
    def validate_path_safety(cls, v: str) -> str:
        """Validate path is safe from traversal attacks."""
        if not validate_safe_path(v, allow_absolute=False):
            raise ValueError("Invalid or unsafe file path")
        return v


class UuidInput(StrictBaseModel):
    """Schema for UUID input with validation."""

    id: UUID = Field(
        ...,
        description="UUID identifier",
    )

    @field_validator('id')
    @classmethod
    def validate_uuid_format(cls, v: str) -> str:
        """Validate UUID format."""
        if not validate_uuid(v):
            raise ValueError("Invalid UUID format")
        return v


class EmailInput(PermissiveBaseModel):
    """Schema for email input with validation."""

    email: Email = Field(
        ...,
        description="Email address",
        max_length=254,
    )

    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        """Validate email format."""
        # Strip and lowercase
        v = v.strip().lower()

        if not validate_email(v, strict=True):
            raise ValueError("Invalid email format")

        return v


class UrlInput(StrictBaseModel):
    """Schema for URL input with validation."""

    url: Url = Field(
        ...,
        description="HTTP/HTTPS URL",
        max_length=2048,
    )

    @field_validator('url')
    @classmethod
    def validate_url_format(cls, v: str) -> str:
        """Validate URL format and scheme."""
        if not validate_url(v, allowed_schemes={'http', 'https'}, require_tld=True):
            raise ValueError("Invalid URL format or disallowed scheme")

        return v


class PaginationParams(StrictBaseModel):
    """
    Schema for pagination parameters with bounds.
    """

    page: int = Field(
        default=1,
        ge=1,
        le=10000,
        description="Page number (1-indexed)",
    )

    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Items per page (max 100)",
    )

    @model_validator(mode='after')
    def validate_pagination(self) -> 'PaginationParams':
        """Validate pagination parameters."""
        # Calculate offset to ensure it doesn't overflow
        offset = (self.page - 1) * self.page_size
        if offset > 1_000_000:  # Reasonable limit
            raise ValueError("Pagination offset too large")

        return self


class BoundedListInput(StrictBaseModel):
    """
    Schema for list input with size constraints.

    Prevents DoS attacks via excessively large lists.
    """

    items: list[str] = Field(
        ...,
        description="List of items",
        min_length=1,
        max_length=100,
    )

    @field_validator('items')
    @classmethod
    def validate_items(cls, v: list[str]) -> list[str]:
        """Validate individual items."""
        # Ensure each item is within length bounds
        for item in v:
            if not validate_length(item, min_length=1, max_length=1000):
                raise ValueError("Item length must be between 1 and 1000 characters")

        # Remove duplicates while preserving order
        seen = set()
        unique_items = []
        for item in v:
            if item not in seen:
                seen.add(item)
                unique_items.append(item)

        return unique_items


class SecureAgentPrompt(PermissiveBaseModel):
    """
    Schema for agent prompts with comprehensive security checks.

    Use this for any user input that will be sent to LLMs.
    """

    prompt: SafeText = Field(
        ...,
        description="Agent prompt with injection protection",
        min_length=1,
        max_length=8000,
    )

    system_context: Optional[SafeText] = Field(
        default=None,
        description="Optional system context",
        max_length=2000,
    )

    @field_validator('prompt', 'system_context')
    @classmethod
    def validate_prompt_content(cls, v: Optional[str]) -> Optional[str]:
        """Validate prompt content for security."""
        if v is None:
            return v

        # Ensure not just whitespace
        if not v.strip():
            raise ValueError("Prompt cannot be empty or only whitespace")

        # Additional security check
        if not validate_no_scripts(v):
            raise ValueError("Script content not allowed in prompts")

        return v

    @model_validator(mode='after')
    def validate_total_length(self) -> 'SecureAgentPrompt':
        """Validate total prompt length."""
        total_length = len(self.prompt)
        if self.system_context:
            total_length += len(self.system_context)

        if total_length > 10000:
            raise ValueError("Total prompt length exceeds maximum of 10000 characters")

        return self
