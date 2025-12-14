"""
Example usage of validators and sanitizers in API routes.

This file demonstrates how to integrate the validation and sanitization
utilities with FastAPI routes.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import Field

from agent_service.api.validators import (
    # Base models
    StrictBaseModel,
    PermissiveBaseModel,
    # String types
    SanitizedString,
    SafeText,
    Username,
    Email,
    UUID,
    # Schemas
    ValidatedTextInput,
    SecureAgentPrompt,
    PaginationParams,
    BoundedListInput,
    # Sanitizers
    sanitize_html,
    normalize_whitespace,
    # Validators
    validate_prompt_injection,
    validate_no_scripts,
)


# Example 1: User Registration with Validated Input
# ================================================

class UserRegistrationRequest(PermissiveBaseModel):
    """User registration with sanitized and validated fields."""

    username: Username = Field(
        ...,
        description="Username (3-32 chars, alphanumeric + _ -)",
        examples=["john_doe"],
    )

    email: Email = Field(
        ...,
        description="Valid email address",
        examples=["user@example.com"],
    )

    full_name: SanitizedString = Field(
        ...,
        description="Full name (HTML will be escaped)",
        min_length=1,
        max_length=100,
        examples=["John Doe"],
    )

    bio: Optional[SafeText] = Field(
        default=None,
        description="User bio (checked for prompt injection)",
        max_length=500,
    )


router = APIRouter(prefix="/examples", tags=["Validation Examples"])


@router.post("/register")
async def register_user(user: UserRegistrationRequest):
    """
    Register a new user with validated input.

    Input is automatically:
    - Sanitized (HTML escaped, null bytes removed)
    - Validated (length, format, security patterns)
    """
    return {
        "status": "success",
        "user": {
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "bio": user.bio,
        }
    }


# Example 2: Agent Interaction with Security Checks
# ================================================

class AgentExecutionRequest(StrictBaseModel):
    """Request to execute an agent with secure prompt handling."""

    agent_id: UUID = Field(
        ...,
        description="Agent UUID",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    prompt: SecureAgentPrompt = Field(
        ...,
        description="Agent prompt with security validation",
    )

    max_tokens: int = Field(
        default=1000,
        ge=1,
        le=8000,
        description="Maximum tokens to generate",
    )


@router.post("/agent/execute")
async def execute_agent(request: AgentExecutionRequest):
    """
    Execute an agent with validated and sanitized prompts.

    The prompt is checked for:
    - Prompt injection patterns
    - Script tags
    - Length constraints
    """
    return {
        "status": "processing",
        "agent_id": request.agent_id,
        "prompt_length": len(request.prompt.prompt),
        "max_tokens": request.max_tokens,
    }


# Example 3: Content Submission with HTML Sanitization
# ================================================

class ContentSubmissionRequest(PermissiveBaseModel):
    """Submit content with HTML sanitization."""

    title: SanitizedString = Field(
        ...,
        description="Content title (HTML escaped)",
        min_length=1,
        max_length=200,
    )

    body: SanitizedString = Field(
        ...,
        description="Content body (HTML escaped)",
        min_length=10,
        max_length=10000,
    )

    tags: BoundedListInput = Field(
        ...,
        description="Content tags (1-100 items)",
    )


@router.post("/content/submit")
async def submit_content(content: ContentSubmissionRequest):
    """
    Submit content with automatic HTML sanitization.

    All HTML tags are escaped to prevent XSS attacks.
    """
    return {
        "status": "success",
        "content": {
            "title": content.title,
            "body": content.body[:100] + "..." if len(content.body) > 100 else content.body,
            "tags": content.tags.items,
        }
    }


# Example 4: Search with Pagination
# ================================================

class SearchRequest(PermissiveBaseModel):
    """Search request with validated query."""

    query: SafeText = Field(
        ...,
        description="Search query",
        min_length=1,
        max_length=200,
    )

    pagination: PaginationParams = Field(
        default_factory=PaginationParams,
        description="Pagination parameters",
    )

    filters: Optional[dict] = Field(
        default=None,
        description="Optional search filters",
    )


@router.post("/search")
async def search(request: SearchRequest):
    """
    Search with validated query and pagination.

    Query is checked for prompt injection and pagination is bounded.
    """
    # Calculate offset for database query
    offset = (request.pagination.page - 1) * request.pagination.page_size

    return {
        "query": request.query,
        "results": [],  # Would fetch from database
        "pagination": {
            "page": request.pagination.page,
            "page_size": request.pagination.page_size,
            "offset": offset,
        }
    }


# Example 5: Manual Validation in Route Handler
# ================================================

class CommentRequest(PermissiveBaseModel):
    """Comment request - demonstrates manual validation."""

    text: str = Field(
        ...,
        description="Comment text",
        min_length=1,
        max_length=1000,
    )

    parent_id: Optional[UUID] = Field(
        default=None,
        description="Parent comment ID",
    )


@router.post("/comments")
async def create_comment(comment: CommentRequest):
    """
    Create a comment with manual security validation.

    Demonstrates how to use validators manually in route handlers
    for custom validation logic.
    """
    # Manual sanitization
    sanitized_text = sanitize_html(comment.text)
    sanitized_text = normalize_whitespace(sanitized_text)

    # Manual validation
    if not validate_prompt_injection(sanitized_text, strict=True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comment contains suspicious content",
        )

    if not validate_no_scripts(sanitized_text):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Script tags are not allowed in comments",
        )

    # Additional custom validation
    if len(sanitized_text.strip()) < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comment cannot be empty",
        )

    return {
        "status": "success",
        "comment": {
            "text": sanitized_text,
            "parent_id": comment.parent_id,
        }
    }


# Example 6: Bulk Operations with List Validation
# ================================================

class BulkUserUpdate(PermissiveBaseModel):
    """Bulk user update with bounded list."""

    user_ids: list[UUID] = Field(
        ...,
        description="List of user UUIDs to update",
        min_length=1,
        max_length=100,
    )

    updates: dict = Field(
        ...,
        description="Updates to apply",
    )


@router.post("/users/bulk-update")
async def bulk_update_users(request: BulkUserUpdate):
    """
    Bulk update users with list size validation.

    List size is bounded to prevent DoS attacks.
    """
    if len(request.user_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update more than 100 users at once",
        )

    return {
        "status": "success",
        "updated_count": len(request.user_ids),
    }


# Example 7: File Upload with Safe Path Validation
# ================================================

class FileUploadRequest(StrictBaseModel):
    """File upload with safe path validation."""

    filename: str = Field(
        ...,
        description="File name (will be sanitized)",
        min_length=1,
        max_length=255,
    )

    content: str = Field(
        ...,
        description="File content (base64 encoded)",
    )


@router.post("/files/upload")
async def upload_file(request: FileUploadRequest):
    """
    Upload a file with sanitized filename.

    Demonstrates safe filename handling.
    """
    from agent_service.api.validators import sanitize_filename, validate_safe_path

    # Sanitize filename
    safe_filename = sanitize_filename(request.filename)

    # Validate it's a safe path (no traversal)
    if not validate_safe_path(safe_filename, allow_absolute=False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    return {
        "status": "success",
        "filename": safe_filename,
        "size": len(request.content),
    }


# Example 8: Combining Multiple Validation Layers
# ================================================

class SecureDataSubmission(StrictBaseModel):
    """
    Demonstrates combining multiple validation layers for maximum security.
    """

    user_id: UUID
    data: SafeText = Field(..., min_length=1, max_length=5000)
    metadata: Optional[dict] = None


@router.post("/secure/submit")
async def secure_submit(request: SecureDataSubmission):
    """
    Submit data with multiple validation layers.

    Validation layers:
    1. Pydantic schema validation (types, lengths)
    2. Custom type validators (SafeText checks prompt injection)
    3. Manual validation in handler
    4. Middleware validation (from RequestValidationMiddleware)
    """
    # Additional manual checks
    if request.metadata:
        # Validate metadata keys and values
        for key, value in request.metadata.items():
            if not isinstance(key, str) or len(key) > 100:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid metadata key",
                )
            if isinstance(value, str) and len(value) > 1000:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Metadata value too large",
                )

    return {
        "status": "success",
        "user_id": request.user_id,
        "data_length": len(request.data),
    }


# Example 9: Custom Validator Composition
# ================================================

def validate_user_content(text: str) -> tuple[bool, Optional[str]]:
    """
    Custom validator that composes multiple validators.

    Returns:
        Tuple of (is_valid, error_message)
    """
    from agent_service.api.validators import (
        validate_prompt_injection,
        validate_no_scripts,
        validate_length,
    )

    # Check length
    if not validate_length(text, min_length=1, max_length=5000):
        return False, "Text must be between 1 and 5000 characters"

    # Check for scripts
    if not validate_no_scripts(text):
        return False, "Script tags are not allowed"

    # Check for prompt injection
    if not validate_prompt_injection(text, strict=True):
        return False, "Text contains suspicious patterns"

    # All checks passed
    return True, None


class UserContentRequest(PermissiveBaseModel):
    """User content with custom validation."""

    content: str = Field(..., min_length=1, max_length=5000)


@router.post("/user/content")
async def submit_user_content(request: UserContentRequest):
    """
    Submit user content with custom composed validators.
    """
    is_valid, error_message = validate_user_content(request.content)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message,
        )

    return {
        "status": "success",
        "content_length": len(request.content),
    }


# To use these examples, include the router in your app:
# from agent_service.api.validators.examples import router as examples_router
# app.include_router(examples_router)
