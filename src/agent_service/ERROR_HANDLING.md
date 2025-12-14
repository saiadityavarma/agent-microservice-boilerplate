# Comprehensive Error Handling System

This document describes the comprehensive error handling system implemented in the agent service.

## Overview

The error handling system provides:

1. **Structured Exception Hierarchy** - Domain-specific exceptions with error codes and HTTP status mappings
2. **User-Friendly Messages** - Clear, actionable error messages that don't expose internal details
3. **Automatic Error Handling** - Middleware that catches and formats all errors consistently
4. **Contextual Logging** - Errors are logged with user, request, and context information
5. **Sentry Integration** - 5xx errors are automatically sent to Sentry for monitoring
6. **Production Safety** - Internal error details are hidden in production environments

## Architecture

### Components

```
domain/
├── exceptions.py          # Exception hierarchy with error codes
├── error_messages.py      # User-friendly message templates
└── error_handling_examples.py  # Usage examples

api/
├── middleware/
│   └── errors.py         # Error handling middleware
└── schemas/
    └── errors.py         # Error response schemas
```

### Error Flow

```
1. Exception Raised (domain.exceptions)
   ↓
2. Caught by Middleware (api.middleware.errors)
   ↓
3. Logged with Context (with user, request_id, traceback for 5xx)
   ↓
4. Sent to Sentry (if 5xx error)
   ↓
5. Formatted Response (with error code, message, request_id, suggested_action)
   ↓
6. Returned to Client (200-599 HTTP status)
```

## Exception Hierarchy

### Base Exception

All exceptions inherit from `AppError`:

```python
from agent_service.domain import AppError

class AppError(Exception):
    error_code: ErrorCode       # Machine-readable code
    status_code: int = 500      # HTTP status code
    message: str                # Human-readable message
    details: dict = None        # Additional context
    suggested_action: str = None  # User-friendly suggestion
```

### Exception Categories

#### Authentication Errors (401)

```python
from agent_service.domain import (
    InvalidCredentials,    # Wrong username/password/API key
    TokenExpired,         # Session expired
    TokenInvalid,         # Invalid token
    ApiKeyInvalid,        # Invalid API key
)

# Example
raise InvalidCredentials(
    message="The API key you provided is invalid",
    suggested_action="Please check your API key in settings"
)
```

#### Authorization Errors (403)

```python
from agent_service.domain import (
    InsufficientPermissions,  # Missing required permission
    ResourceAccessDenied,     # No access to specific resource
)

# Example
raise InsufficientPermissions(
    message="You need 'agents:delete' permission",
    details={"required_permission": "agents:delete"},
)
```

#### Validation Errors (400)

```python
from agent_service.domain import (
    ValidationError,      # General validation error
    InvalidRequest,       # Invalid request format
    InvalidParameter,     # Invalid parameter value
    MissingField,        # Required field missing
)

# Example
raise ValidationError(
    message="Invalid agent configuration",
    details={
        "fields": {
            "max_tokens": "Must be between 1 and 100000",
            "temperature": "Must be between 0.0 and 2.0"
        }
    }
)
```

#### Resource Errors (404, 409)

```python
from agent_service.domain import (
    NotFound,          # Resource not found
    UserNotFound,      # User not found
    AgentNotFound,     # Agent not found
    AlreadyExists,     # Resource already exists
    ResourceLocked,    # Resource locked for modification
)

# Example
raise AgentNotFound(
    message="Agent 'gpt-assistant' not found",
    details={"agent_id": "gpt-assistant"}
)
```

#### Agent-Specific Errors

```python
from agent_service.domain import (
    AgentNotFound,            # Agent not found (404)
    InvocationFailed,         # Agent execution failed (500)
    AgentTimeout,             # Agent timed out (504)
    AgentConfigurationError,  # Invalid agent config (400)
)

# Example
raise AgentTimeout(
    message="Agent execution timed out after 30 seconds",
    details={"agent_id": "abc123", "timeout": 30}
)
```

#### External Service Errors (502, 503)

```python
from agent_service.domain import (
    LLMError,                # LLM service error (502)
    LLMRateLimitError,       # LLM rate limit (429)
    DatabaseError,           # Database error (503)
    DatabaseConnectionError, # Database connection failed (503)
    CacheError,             # Cache service error (503)
)

# Example
raise LLMError(
    message="AI service is currently unavailable",
    details={"provider": "openai", "error": "timeout"}
)
```

#### Rate Limiting Errors (429)

```python
from agent_service.domain import (
    RateLimitError,    # Rate limit exceeded
    QuotaExceeded,     # Usage quota exceeded
)

# Example
raise RateLimitError(
    message="Rate limit exceeded: 100 requests per hour",
    details={"limit": 100, "window": "1 hour", "reset_in": 1800}
)
```

#### Timeout Errors (504)

```python
from agent_service.domain import (
    TimeoutError,       # Request timeout
    UpstreamTimeout,    # External service timeout
)
```

#### Service Availability Errors (503)

```python
from agent_service.domain import (
    ServiceUnavailable,  # Service temporarily unavailable
    MaintenanceMode,     # Service in maintenance
)
```

## Usage Examples

### Basic Exception Raising

```python
from agent_service.domain import AgentNotFound

# Simple usage with default message
raise AgentNotFound()

# With custom message
raise AgentNotFound("Agent 'my-agent' not found")

# With full details
raise AgentNotFound(
    message="Agent 'my-agent' not found",
    details={"agent_id": "my-agent", "available_agents": ["basic", "advanced"]},
    suggested_action="Please use one of the available agents"
)
```

### In API Endpoints

```python
from fastapi import APIRouter
from agent_service.domain import AgentNotFound, ValidationError

router = APIRouter()

@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    agent = await lookup_agent(agent_id)

    if agent is None:
        # Middleware automatically handles this
        raise AgentNotFound(
            message=f"Agent '{agent_id}' not found",
            details={"agent_id": agent_id}
        )

    return agent

@router.post("/agents")
async def create_agent(config: dict):
    # Validate configuration
    if config.get("max_tokens", 0) < 1:
        raise ValidationError(
            message="Invalid configuration",
            details={"max_tokens": "Must be at least 1"}
        )

    # Create agent...
    return {"id": "new-agent"}
```

### Error Response Format

All errors are returned in a consistent format:

```json
{
  "error": {
    "code": "AGENT_NOT_FOUND",
    "message": "Agent 'my-agent' not found",
    "details": {
      "agent_id": "my-agent"
    }
  },
  "suggested_action": "Please verify the agent ID is correct or create a new agent",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Validation Errors with Field Details

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "max_tokens",
        "message": "Must be a valid integer",
        "code": "INT_TYPE",
        "value": "invalid"
      },
      {
        "field": "temperature",
        "message": "Must be between 0.0 and 2.0",
        "code": "VALUE_OUT_OF_RANGE"
      }
    ]
  },
  "suggested_action": "Please check your input and ensure all required fields are provided correctly",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Error Messages

The system includes user-friendly error messages that:

- Are clear and understandable to non-technical users
- Provide actionable guidance (tell users what they can do)
- Don't expose internal implementation details
- Are consistent in tone and style

### Using Error Message Utilities

```python
from agent_service.domain.error_messages import (
    get_error_message,
    get_suggested_action,
    format_resource_not_found,
    format_validation_message,
    format_rate_limit_message,
)

# Get standard error message
message = get_error_message("AGENT_NOT_FOUND")
# "The agent you're looking for doesn't exist."

# Get suggested action
action = get_suggested_action("TOKEN_EXPIRED")
# "Please log in again to continue."

# Format resource not found
message = format_resource_not_found("agent", "abc123")
# "Agent 'abc123' was not found."

# Format validation message
message = format_validation_message("age", "number_out_of_range", min=0, max=120)
# "Age: The number must be between 0 and 120."

# Format rate limit message
message = format_rate_limit_message(100, "hour", "30 minutes")
# "You can make 100 requests per hour. Your limit will reset in 30 minutes."
```

## Logging and Monitoring

### Automatic Logging

Errors are automatically logged with context:

```python
# 5xx errors - logged as ERROR with full traceback
logger.error(
    "Server error: Agent execution failed",
    extra={
        "request_id": "550e8400-e29b-41d4-a716-446655440000",
        "path": "/agents/abc123/invoke",
        "method": "POST",
        "status_code": 500,
        "error_type": "InvocationFailed",
        "user_id": "user123",
        "email": "user@example.com"
    },
    exc_info=True
)

# 401/403 errors - logged as WARNING
logger.warning(
    "Authentication error: Invalid credentials",
    extra={...}
)

# Other 4xx errors - logged as INFO
logger.info(
    "Client error: Validation failed",
    extra={...}
)
```

### Sentry Integration

5xx errors are automatically sent to Sentry with:

- Full exception details and stack trace
- User context (user_id, email)
- Request context (path, method, query params)
- Custom tags and context
- Request ID for correlation

```python
# Automatic Sentry capture for 5xx errors
# No code needed - middleware handles it
```

## Production vs Development

### Development Mode

In development (`environment != "prod"`):

- Full error messages with exception details
- Stack traces in responses
- Internal error context included

```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred: division by zero",
    "context": {
      "exception_type": "ZeroDivisionError",
      "exception_message": "division by zero"
    }
  },
  "request_id": "..."
}
```

### Production Mode

In production (`environment = "prod"`):

- Generic messages for 5xx errors
- No internal error details exposed
- Stack traces hidden from responses

```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An internal error occurred. Please try again later."
  },
  "suggested_action": "Please try again later. If the problem persists, contact support",
  "request_id": "..."
}
```

## Configuration

Error handling is configured via environment variables in `config/settings.py`:

```python
# Environment (affects error detail visibility)
environment: Literal["local", "dev", "staging", "prod"] = "local"

# Sentry configuration
sentry_dsn: str | None = None
sentry_environment: str | None = None
sentry_sample_rate: float = 1.0
sentry_traces_sample_rate: float = 0.1
```

## Best Practices

### 1. Use Specific Exceptions

```python
# Good - specific exception
raise AgentNotFound(message=f"Agent '{agent_id}' not found")

# Bad - generic exception
raise Exception("Agent not found")
```

### 2. Provide Context in Details

```python
# Good - includes helpful context
raise ValidationError(
    message="Invalid agent configuration",
    details={
        "max_tokens": "Must be between 1 and 100000",
        "temperature": "Must be between 0.0 and 2.0"
    }
)

# Bad - no details
raise ValidationError("Invalid configuration")
```

### 3. Use Suggested Actions

```python
# Good - tells user what to do
raise RateLimitError(
    message="Rate limit exceeded",
    suggested_action="Please wait 30 seconds before making more requests"
)

# Bad - no guidance
raise RateLimitError("Too many requests")
```

### 4. Wrap External Errors

```python
# Good - wraps external error with domain exception
try:
    result = await llm_service.call()
except ExternalServiceError as e:
    raise LLMError(
        message="AI service error",
        details={"error": str(e)}
    )

# Bad - lets external error propagate
result = await llm_service.call()  # May raise unfamiliar exception
```

### 5. Don't Expose Internal Details

```python
# Good - user-friendly message
raise DatabaseError(
    message="Unable to save agent configuration",
    suggested_action="Please try again. If the problem persists, contact support"
)

# Bad - exposes internal details
raise DatabaseError(
    message="PostgreSQL connection refused on localhost:5432",
    details={"connection_string": "postgresql://user:pass@localhost/db"}
)
```

## Testing

### Testing Error Responses

```python
from fastapi.testclient import TestClient

def test_agent_not_found():
    client = TestClient(app)
    response = client.get("/agents/nonexistent")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "AGENT_NOT_FOUND"
    assert "request_id" in response.json()
    assert "suggested_action" in response.json()

def test_validation_error():
    client = TestClient(app)
    response = client.post("/agents", json={"config": {"max_tokens": -1}})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in response.json()["error"]
```

### Testing Exception Raising

```python
import pytest
from agent_service.domain import AgentNotFound

def test_exception_attributes():
    exc = AgentNotFound(
        message="Test agent not found",
        details={"agent_id": "test"}
    )

    assert exc.status_code == 404
    assert exc.error_code.value == "AGENT_NOT_FOUND"
    assert exc.message == "Test agent not found"
    assert exc.details["agent_id"] == "test"
    assert exc.suggested_action is not None
```

## Migration Guide

If you have existing code using the old error classes, here's how to migrate:

### Old Code (api/middleware/errors.py)

```python
from agent_service.api.middleware.errors import NotFoundError, ValidationError

raise NotFoundError("Agent not found")
raise ValidationError("Invalid input")
```

### New Code (domain/exceptions.py)

```python
from agent_service.domain import NotFound, ValidationError

raise NotFound("Agent not found")
raise ValidationError("Invalid input")
```

The old classes are still available for backward compatibility but are deprecated.

## Troubleshooting

### Error Not Being Caught

- Ensure you're raising exceptions that inherit from `AppError`
- Check that `register_error_handlers(app)` is called in `api/app.py`
- Verify the exception is raised within an endpoint, not in startup code

### Sentry Not Receiving Errors

- Check `sentry_dsn` is set in environment variables
- Verify the error is a 5xx error (4xx errors aren't sent to Sentry)
- Check Sentry logs for initialization errors

### Error Messages Not User-Friendly

- Use exceptions from `domain.exceptions` (not raw exceptions)
- Provide custom messages with the `message` parameter
- Use `suggested_action` parameter for guidance
- Check `domain/error_messages.py` for message utilities

## References

- Exception Hierarchy: `domain/exceptions.py`
- Error Messages: `domain/error_messages.py`
- Error Middleware: `api/middleware/errors.py`
- Error Schemas: `api/schemas/errors.py`
- Usage Examples: `domain/error_handling_examples.py`
