# Integration Guide

This guide shows how to integrate the validation and sanitization system into your existing FastAPI application.

## Step 1: Install Dependencies

The validation system requires `bleach` for enhanced HTML sanitization:

```bash
pip install -e .  # This will install bleach>=6.0.0 from pyproject.toml
```

Or if using a different package manager:

```bash
poetry add bleach>=6.0.0
# or
pip install bleach>=6.0.0
```

## Step 2: Add Validation Middleware to App

Update `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/api/app.py`:

```python
from agent_service.api.middleware.validation import setup_validation_middleware

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.debug else None,
        lifespan=lifespan,
    )

    # Middleware (order matters - added in reverse order of execution)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    # ADD THIS: Request validation middleware
    setup_validation_middleware(
        app,
        max_body_size=10 * 1024 * 1024,  # 10MB
        check_prompt_injection=True,
        check_scripts=True,
    )

    # CORS middleware
    cors_config = get_cors_middleware_config(settings)
    app.add_middleware(CORSMiddleware, **cors_config)

    # ... rest of app setup
```

Alternatively, add the middleware manually:

```python
from agent_service.api.middleware.validation import RequestValidationMiddleware

app.add_middleware(
    RequestValidationMiddleware,
    max_body_size=10 * 1024 * 1024,
    allowed_content_types={
        'application/json',
        'application/x-www-form-urlencoded',
        'multipart/form-data',
    },
    check_prompt_injection=True,
    check_scripts=True,
)
```

## Step 3: Use Validators in Existing Routes

### Example: Update Agent Routes

Update `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/api/routes/agents.py`:

```python
from agent_service.api.validators import (
    StrictBaseModel,
    SafeText,
    UUID,
    SecureAgentPrompt,
    PaginationParams,
)
from pydantic import Field

# Before (unsafe):
class AgentExecuteRequest(BaseModel):
    prompt: str
    max_tokens: int = 1000

# After (secure):
class AgentExecuteRequest(StrictBaseModel):
    prompt: SafeText = Field(
        ...,
        description="Agent prompt (validated for injection)",
        min_length=1,
        max_length=8000,
    )
    max_tokens: int = Field(
        default=1000,
        ge=1,
        le=8000,
        description="Maximum tokens to generate",
    )

@router.post("/{agent_id}/execute")
async def execute_agent(
    agent_id: UUID,
    request: AgentExecuteRequest,
):
    # The prompt is now automatically validated
    # - No prompt injection patterns
    # - No script tags
    # - Length constraints enforced
    return await agent_service.execute(agent_id, request.prompt)
```

### Example: Update Authentication Routes

Update `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/api/routes/auth.py`:

```python
from agent_service.api.validators import (
    PermissiveBaseModel,
    Username,
    Email,
    SanitizedString,
)

# Before (unsafe):
class UserRegistration(BaseModel):
    username: str
    email: str
    full_name: str

# After (secure):
class UserRegistration(PermissiveBaseModel):
    username: Username  # 3-32 chars, alphanumeric + _ -
    email: Email  # Valid email format, normalized
    full_name: SanitizedString = Field(
        ...,
        min_length=1,
        max_length=100,
    )
```

## Step 4: Add Manual Validation Where Needed

For routes that need additional custom validation:

```python
from fastapi import HTTPException, status
from agent_service.api.validators import (
    sanitize_html,
    validate_prompt_injection,
    validate_no_scripts,
)

@router.post("/content")
async def create_content(content: str):
    # Sanitize input
    clean_content = sanitize_html(content)

    # Validate for security
    if not validate_prompt_injection(clean_content, strict=True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content contains suspicious patterns",
        )

    if not validate_no_scripts(clean_content):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Script tags are not allowed",
        )

    # Process the validated content
    return await content_service.create(clean_content)
```

## Step 5: Testing

Run the test suite to verify validators work:

```bash
# Run validation tests
pytest src/agent_service/api/validators/test_validators.py -v

# Run all tests
pytest -v
```

## Step 6: Optional - Add Example Routes

To see examples in action, add the example router to your app:

```python
# In app.py
from agent_service.api.validators.examples import router as examples_router

# Add with other routers
app.include_router(examples_router, prefix="/api/v1", tags=["Examples"])
```

Then visit:
- `http://localhost:8000/docs` to see the example endpoints
- Try sending requests with malicious content to see validation in action

## Configuration

### Environment-Based Configuration

Add validation settings to your config:

```python
# src/agent_service/config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... existing settings ...

    # Validation settings
    max_request_body_size: int = 10 * 1024 * 1024  # 10MB
    enable_prompt_injection_check: bool = True
    enable_script_check: bool = True
    strict_validation: bool = False  # Enable for production
```

Then use in app setup:

```python
settings = get_settings()

setup_validation_middleware(
    app,
    max_body_size=settings.max_request_body_size,
    check_prompt_injection=settings.enable_prompt_injection_check,
    check_scripts=settings.enable_script_check,
)
```

## Best Practices

### 1. Use StrictBaseModel for Sensitive Data

```python
# For API keys, credentials, etc.
class ApiKeyCreate(StrictBaseModel):  # Strict validation
    name: str
    permissions: list[str]
```

### 2. Use PermissiveBaseModel for User Input

```python
# For user-generated content
class UserComment(PermissiveBaseModel):  # Allow type coercion
    text: SafeText
    rating: int  # Will accept "5" as int
```

### 3. Layer Your Defenses

```python
# 1. Middleware validates request structure
# 2. Pydantic schema validates and sanitizes fields
# 3. Business logic adds additional checks

class SecureInput(StrictBaseModel):
    data: SafeText  # Pydantic validation

@router.post("/process")
async def process(input: SecureInput):
    # Additional business logic validation
    if len(input.data) > business_rule_max_length:
        raise HTTPException(400, "Too long")

    # Process validated data
    return await service.process(input.data)
```

### 4. Monitor Validation Failures

The middleware automatically logs validation failures with structlog. Monitor these logs:

```python
# Validation failures are logged as:
logger.warning(
    "rejected_content_type",
    content_type=content_type,
    path=request.url.path,
)

logger.warning(
    "potential_injection",
    path=path,
)
```

Set up alerts for frequent validation failures - they may indicate an attack.

## Common Patterns

### Pattern 1: Search with Pagination

```python
from agent_service.api.validators import SafeText, PaginationParams

class SearchRequest(PermissiveBaseModel):
    query: SafeText
    pagination: PaginationParams = Field(default_factory=PaginationParams)

@router.post("/search")
async def search(request: SearchRequest):
    offset = (request.pagination.page - 1) * request.pagination.page_size
    return await db.search(
        request.query,
        limit=request.pagination.page_size,
        offset=offset,
    )
```

### Pattern 2: Bulk Operations

```python
from agent_service.api.validators import UUID

class BulkOperation(StrictBaseModel):
    item_ids: list[UUID] = Field(
        ...,
        min_length=1,
        max_length=100,
    )

@router.post("/bulk")
async def bulk_update(request: BulkOperation):
    return await service.bulk_update(request.item_ids)
```

### Pattern 3: File Upload

```python
from agent_service.api.validators import sanitize_filename, validate_safe_path

@router.post("/upload")
async def upload(file: UploadFile):
    # Sanitize filename
    safe_name = sanitize_filename(file.filename)

    # Validate path
    if not validate_safe_path(safe_name):
        raise HTTPException(400, "Invalid filename")

    # Process file
    return await storage.save(safe_name, file)
```

## Troubleshooting

### Issue: ValidationError on Valid Input

If you're getting validation errors on input that should be valid:

```python
# Check if strict mode is too restrictive
class MyModel(PermissiveBaseModel):  # Try permissive instead of strict
    field: str
```

### Issue: Prompt Injection False Positives

If legitimate text is being flagged:

```python
# Use non-strict mode
if not validate_prompt_injection(text, strict=False):
    # Only basic checks
    pass
```

### Issue: Performance Concerns

The middleware validates all requests. To improve performance:

1. Skip validation for read-only endpoints
2. Adjust `_should_skip_validation()` in the middleware
3. Use caching for repeated validations

```python
# Skip validation for GET requests
def _should_skip_validation(self, path: str, method: str) -> bool:
    if method == "GET":
        return True
    # ... rest of checks
```

## Migration Checklist

- [ ] Install bleach dependency
- [ ] Add validation middleware to app
- [ ] Update critical routes (authentication, agent execution)
- [ ] Add validators to user input endpoints
- [ ] Run test suite
- [ ] Test in staging environment
- [ ] Monitor validation failure logs
- [ ] Deploy to production

## Support

For issues or questions:
1. Check the README.md for examples
2. Review test_validators.py for usage patterns
3. See examples.py for complete route examples
