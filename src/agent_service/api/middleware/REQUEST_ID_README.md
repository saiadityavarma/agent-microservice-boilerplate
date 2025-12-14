# Request ID and Correlation Tracking Middleware

This middleware provides comprehensive request identification and correlation tracking for distributed systems, enabling proper log correlation and distributed tracing.

## Features

### 1. Automatic Request ID Generation
- Generates unique UUID4 for each request
- Accepts incoming `X-Request-ID` header for distributed tracing
- Validates incoming IDs to prevent injection attacks
- Returns request ID in `X-Request-ID` response header

### 2. Correlation ID Support
- Accepts `X-Correlation-ID` from upstream services
- Defaults to request ID if not provided
- Enables tracking requests across multiple services
- Returns correlation ID in `X-Correlation-ID` response header

### 3. Security
- Validates all incoming IDs (must be valid UUID4)
- Rejects malicious input (SQL injection, XSS, path traversal)
- Generates new ID if validation fails
- Logs security warnings for invalid IDs

### 4. Logging Integration
- Automatically adds `request_id` to all log entries
- Automatically adds `correlation_id` to all log entries
- Integrates with structlog processors
- No manual logging configuration needed

### 5. Background Task Support
- `@preserve_request_id` decorator for async tasks
- Maintains request ID in spawned tasks
- Works with both sync and async functions
- Enables proper log correlation for background work

## Installation

The middleware is already registered in `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/api/app.py`:

```python
from agent_service.api.middleware.request_id import RequestIDMiddleware

app.add_middleware(RequestIDMiddleware)
```

The logging processor is registered in `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/infrastructure/observability/logging.py`:

```python
from agent_service.api.middleware.request_id import add_request_id_to_log

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        add_request_id_to_log,  # Adds request_id and correlation_id to logs
        # ... other processors
    ]
)
```

## Usage

### Basic Usage in Route Handlers

```python
from fastapi import Request
from agent_service.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

@app.get("/users/{user_id}")
async def get_user(user_id: str, request: Request):
    # Access request ID from request.state
    request_id = request.state.request_id
    correlation_id = request.state.correlation_id

    # Or use context variables (works anywhere)
    from agent_service.api.middleware.request_id import get_request_id
    request_id = get_request_id()

    # All logs automatically include request_id and correlation_id
    logger.info("Fetching user", user_id=user_id)

    return {"user_id": user_id, "request_id": request_id}
```

### Background Tasks

```python
from fastapi import BackgroundTasks, Request
from agent_service.api.middleware.request_id import preserve_request_id
from agent_service.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

@preserve_request_id
async def process_order(order_id: str):
    """Background task with preserved request ID."""
    logger.info("Processing order", order_id=order_id)
    # All logs will have the same request_id as the original request
    await some_processing()
    logger.info("Order completed", order_id=order_id)

@app.post("/orders")
async def create_order(
    request: Request,
    background_tasks: BackgroundTasks
):
    order_id = "ORDER-123"

    # Add background task (decorator preserves request ID)
    background_tasks.add_task(process_order, order_id)

    logger.info("Order created", order_id=order_id)
    return {"order_id": order_id, "request_id": request.state.request_id}
```

### Distributed Tracing

```python
import httpx
from agent_service.api.middleware.request_id import (
    get_request_id,
    get_correlation_id
)

async def call_downstream_service(data: dict):
    """Call downstream service with correlation tracking."""
    request_id = get_request_id()
    correlation_id = get_correlation_id()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://downstream-service.com/api",
            json=data,
            headers={
                # Pass correlation ID to downstream service
                "X-Correlation-ID": correlation_id,
                # Optionally pass our request ID as parent
                "X-Parent-Request-ID": request_id,
            }
        )
    return response.json()
```

### Service Classes

```python
from agent_service.infrastructure.observability.logging import get_logger

class UserService:
    """Service class with automatic request ID logging."""

    def __init__(self):
        self.logger = get_logger(__name__)

    async def create_user(self, username: str, email: str):
        # All logs automatically include request_id
        self.logger.info("Creating user", username=username)

        # Your business logic here
        user = await db.create_user(username, email)

        self.logger.info("User created", user_id=user.id)
        return user
```

### Async Workers

```python
import asyncio
from agent_service.api.middleware.request_id import preserve_request_id
from agent_service.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

@preserve_request_id
async def async_worker(task_data: dict):
    """Async worker that maintains request ID."""
    logger.info("Worker started", task_data=task_data)
    await asyncio.sleep(1)
    logger.info("Worker completed", task_data=task_data)

@app.post("/process")
async def process_data(request: Request):
    task_data = {"task": "process_data"}

    # Spawn worker (maintains request ID)
    asyncio.create_task(async_worker(task_data))

    return {"status": "processing", "request_id": request.state.request_id}
```

## API Reference

### Middleware

#### `RequestIDMiddleware`
- Adds request ID and correlation ID to every request
- Validates incoming IDs (must be UUID4)
- Stores IDs in `request.state.request_id` and `request.state.correlation_id`
- Adds IDs to response headers

### Context Variables

#### `get_request_id() -> Optional[str]`
Get current request ID from context.

#### `set_request_id(request_id: str) -> None`
Set request ID in context (for background tasks).

#### `get_correlation_id() -> Optional[str]`
Get current correlation ID from context.

#### `set_correlation_id(correlation_id: str) -> None`
Set correlation ID in context.

### Decorators

#### `@preserve_request_id`
Decorator for background tasks and async operations to preserve request ID.

```python
@preserve_request_id
async def background_task():
    # Has access to original request's ID
    logger.info("Processing in background")
```

### Utilities

#### `is_valid_uuid(value: str) -> bool`
Validate if a string is a valid UUID4.

#### `add_request_id_to_log(logger, method_name, event_dict) -> dict`
Structlog processor that adds request_id and correlation_id to log entries.

## HTTP Headers

### Request Headers

- `X-Request-ID`: Optional UUID4 identifier for this specific request
  - If valid UUID4: Used as request ID
  - If invalid: Rejected, new UUID4 generated
  - If not present: New UUID4 generated

- `X-Correlation-ID`: Optional UUID4 identifier for request correlation
  - If valid UUID4: Used as correlation ID
  - If invalid: Request ID used instead
  - If not present: Request ID used as correlation ID

### Response Headers

- `X-Request-ID`: The request ID for this request
- `X-Correlation-ID`: The correlation ID for this request

## Log Output

All logs automatically include request tracking:

```json
{
  "event": "User created",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user123",
  "timestamp": "2025-12-13T10:30:00.123456Z",
  "level": "info"
}
```

## Testing

### Providing Custom Request ID

```bash
curl -H "X-Request-ID: 550e8400-e29b-41d4-a716-446655440000" \
     http://localhost:8000/api/v1/users
```

### Distributed Tracing

Service A:
```bash
curl -H "X-Correlation-ID: 123e4567-e89b-12d3-a456-426614174000" \
     http://service-a.com/api/process
```

Service A calls Service B with same correlation ID:
```python
# Service A forwards correlation ID
headers = {"X-Correlation-ID": correlation_id}
response = await http_client.post("http://service-b.com/api", headers=headers)
```

Both services will log with the same correlation_id, enabling end-to-end tracing.

## Security Considerations

### UUID Validation

All incoming request IDs and correlation IDs are validated:
- Must be valid UUID4 format
- Invalid IDs are rejected and logged
- New UUID4 generated for invalid requests
- Prevents injection attacks

### Attack Prevention

The middleware protects against:
- SQL Injection: `'; DROP TABLE users; --` → Rejected
- XSS: `<script>alert('xss')</script>` → Rejected
- Path Traversal: `../../../etc/passwd` → Rejected
- Any non-UUID4 input → Rejected

## Examples

See `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/api/middleware/request_id_examples.py` for comprehensive usage examples including:

1. Basic route handler usage
2. Background tasks
3. Distributed tracing
4. Error handling
5. Service classes
6. Async workers
7. Multiple service calls

## Tests

Run tests:
```bash
pytest src/agent_service/api/middleware/test_request_id.py -v
```

Tests cover:
- UUID validation
- Context variables
- Middleware functionality
- Security scenarios
- Background task preservation
- Log processor integration

## Files

- `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/api/middleware/request_id.py` - Main implementation
- `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/api/middleware/test_request_id.py` - Tests
- `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/api/middleware/request_id_examples.py` - Usage examples
- `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/api/app.py` - Middleware registration
- `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/infrastructure/observability/logging.py` - Logging integration
