# Request ID and Correlation Tracking Implementation Summary

## Overview

Successfully implemented comprehensive request ID and correlation tracking middleware at `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/api/middleware/request_id.py` with full integration into the FastAPI application.

## Implementation Status

### ✓ Completed Features

#### 1. RequestIDMiddleware Class
- **Location**: `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/api/middleware/request_id.py`
- Generates unique UUID4 request ID for each request
- Accepts incoming `X-Request-ID` header (validated)
- Accepts incoming `X-Correlation-ID` header (validated)
- Stores IDs in `request.state.request_id` and `request.state.correlation_id`
- Adds `X-Request-ID` and `X-Correlation-ID` to response headers
- Validates all incoming IDs (must be valid UUID4)
- Logs warnings for invalid IDs with client IP

#### 2. Context Variables
- `request_id_var: ContextVar[str]` - Thread-safe storage for request ID
- `correlation_id_var: ContextVar[str]` - Thread-safe storage for correlation ID
- `get_request_id() -> Optional[str]` - Retrieve current request ID
- `set_request_id(id: str)` - Set request ID (for background tasks)
- `get_correlation_id() -> Optional[str]` - Retrieve correlation ID
- `set_correlation_id(id: str)` - Set correlation ID

#### 3. Logging Integration
- **Location**: `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/infrastructure/observability/logging.py`
- `add_request_id_to_log()` processor registered in structlog
- Automatically adds `request_id` and `correlation_id` to all log entries
- No manual configuration needed in application code

#### 4. Background Task Support
- `@preserve_request_id` decorator for async/sync functions
- Automatically captures and restores request ID in background tasks
- Works with FastAPI BackgroundTasks
- Works with asyncio.create_task()
- Supports both async and sync functions

#### 5. Security Features
- `is_valid_uuid()` function validates all incoming IDs
- Rejects non-UUID4 formats
- Prevents SQL injection attempts
- Prevents XSS attempts
- Prevents path traversal attempts
- Generates new UUID4 when invalid ID received

#### 6. Application Integration
- **Location**: `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/api/app.py`
- Middleware registered in correct order (before logging middleware)
- Available to all routes automatically
- Compatible with existing middleware stack

## File Structure

```
/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/
├── src/agent_service/
│   ├── api/
│   │   ├── middleware/
│   │   │   ├── __init__.py (updated with exports)
│   │   │   ├── request_id.py (MAIN IMPLEMENTATION)
│   │   │   ├── request_id_examples.py (usage examples)
│   │   │   ├── test_request_id.py (comprehensive tests)
│   │   │   └── REQUEST_ID_README.md (documentation)
│   │   └── app.py (middleware registration)
│   └── infrastructure/
│       └── observability/
│           └── logging.py (structlog integration)
└── REQUEST_ID_IMPLEMENTATION_SUMMARY.md (this file)
```

## API Reference

### Middleware
```python
from agent_service.api.middleware.request_id import RequestIDMiddleware
app.add_middleware(RequestIDMiddleware)
```

### Context Functions
```python
from agent_service.api.middleware.request_id import (
    get_request_id,
    set_request_id,
    get_correlation_id,
    set_correlation_id,
)

# Get current request ID
request_id = get_request_id()

# Set request ID (for background tasks)
set_request_id("550e8400-e29b-41d4-a716-446655440000")
```

### Decorator
```python
from agent_service.api.middleware.request_id import preserve_request_id

@preserve_request_id
async def background_task():
    # Request ID is preserved here
    logger.info("Processing")
```

### Utilities
```python
from agent_service.api.middleware.request_id import is_valid_uuid

# Validate UUID4
is_valid = is_valid_uuid("550e8400-e29b-41d4-a716-446655440000")
```

## Usage Examples

### Basic Route Handler
```python
from fastapi import Request
from agent_service.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

@app.get("/users")
async def get_users(request: Request):
    # Request ID automatically available
    request_id = request.state.request_id

    # All logs automatically include request_id
    logger.info("Fetching users")

    return {"users": [], "request_id": request_id}
```

### Background Tasks
```python
from fastapi import BackgroundTasks
from agent_service.api.middleware.request_id import preserve_request_id

@preserve_request_id
async def send_email(user_id: str):
    # Request ID preserved in background task
    logger.info("Sending email", user_id=user_id)

@app.post("/send")
async def send(background_tasks: BackgroundTasks):
    background_tasks.add_task(send_email, "user123")
    return {"status": "queued"}
```

### Distributed Tracing
```python
import httpx
from agent_service.api.middleware.request_id import get_correlation_id

async def call_service():
    correlation_id = get_correlation_id()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.example.com/process",
            headers={"X-Correlation-ID": correlation_id}
        )
    return response.json()
```

## HTTP Headers

### Request Headers
- `X-Request-ID`: Optional UUID4 for this specific request
- `X-Correlation-ID`: Optional UUID4 for distributed tracing

### Response Headers
- `X-Request-ID`: The request ID (generated or accepted)
- `X-Correlation-ID`: The correlation ID (defaults to request ID)

## Testing

### Run Tests
```bash
# All tests
pytest src/agent_service/api/middleware/test_request_id.py -v

# Specific test classes
pytest src/agent_service/api/middleware/test_request_id.py::TestUUIDValidation -v
pytest src/agent_service/api/middleware/test_request_id.py::TestRequestIDMiddleware -v
pytest src/agent_service/api/middleware/test_request_id.py::TestPreserveRequestID -v
pytest src/agent_service/api/middleware/test_request_id.py::TestLogProcessor -v
pytest src/agent_service/api/middleware/test_request_id.py::TestSecurityScenarios -v
```

### Manual Testing
```bash
# Test with custom request ID
curl -H "X-Request-ID: 550e8400-e29b-41d4-a716-446655440000" \
     http://localhost:8000/health

# Test with correlation ID
curl -H "X-Correlation-ID: 123e4567-e89b-12d3-a456-426614174000" \
     http://localhost:8000/health

# Test with invalid ID (should generate new one)
curl -H "X-Request-ID: invalid-id" \
     http://localhost:8000/health
```

## Log Output Example

```json
{
  "event": "User created",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user123",
  "level": "info",
  "timestamp": "2025-12-13T10:30:00.123456Z"
}
```

## Security Features

### UUID Validation
All incoming IDs are validated as UUID4:
- Valid: `550e8400-e29b-41d4-a716-446655440000` ✓
- Invalid: `not-a-uuid` ✗ (new UUID generated)
- Invalid: `<script>alert('xss')</script>` ✗ (rejected)
- Invalid: `'; DROP TABLE users; --` ✗ (rejected)

### Attack Prevention
- SQL Injection: Rejected
- XSS: Rejected
- Path Traversal: Rejected
- Invalid UUIDs: Rejected with warning log

## Verification

All components tested and verified:
- ✓ UUID validation works correctly
- ✓ Context variables set/get properly
- ✓ Correlation ID tracking functional
- ✓ Log processor adds IDs to logs
- ✓ preserve_request_id decorator works
- ✓ RequestIDMiddleware class implemented
- ✓ Integration with app.py complete
- ✓ Integration with logging.py complete
- ✓ Python 3.9 compatibility ensured

## Dependencies

- `uuid` (standard library)
- `functools` (standard library)
- `inspect` (standard library)
- `contextvars` (standard library)
- `typing` (standard library)
- `starlette` (already installed)
- `structlog` (installed as part of this implementation)

## Next Steps (Optional Enhancements)

1. **Database Integration**: Store request IDs in database for audit trails
2. **Metrics**: Track request ID distribution and correlation patterns
3. **Tracing**: Integrate with OpenTelemetry for distributed tracing
4. **Rate Limiting**: Use request IDs for per-client rate limiting
5. **Error Tracking**: Send request IDs to error tracking services (Sentry, etc.)

## Documentation

- **Main Documentation**: `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/api/middleware/REQUEST_ID_README.md`
- **Usage Examples**: `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/api/middleware/request_id_examples.py`
- **Tests**: `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/api/middleware/test_request_id.py`

## Summary

The request ID and correlation tracking middleware is fully implemented, tested, and integrated into the application. All specified features are working correctly:

1. ✓ Request ID generation and validation
2. ✓ Correlation ID support
3. ✓ Context variables for non-request contexts
4. ✓ Automatic logging integration
5. ✓ Background task support with @preserve_request_id
6. ✓ Security validation (UUID4 only)
7. ✓ Application registration in app.py

The implementation is production-ready and includes comprehensive documentation, examples, and tests.
