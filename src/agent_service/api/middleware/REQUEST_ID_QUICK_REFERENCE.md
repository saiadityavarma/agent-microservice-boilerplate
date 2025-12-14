# Request ID Middleware - Quick Reference

## Import

```python
from agent_service.api.middleware.request_id import (
    get_request_id,
    get_correlation_id,
    preserve_request_id,
)
from agent_service.infrastructure.observability.logging import get_logger
```

## Common Usage Patterns

### 1. Access Request ID in Route
```python
@app.get("/users")
async def get_users(request: Request):
    request_id = request.state.request_id
    # or
    request_id = get_request_id()
    return {"data": [], "request_id": request_id}
```

### 2. Background Task
```python
@preserve_request_id
async def process_data(data_id: str):
    logger.info("Processing", data_id=data_id)  # Has request_id

@app.post("/process")
async def process(background_tasks: BackgroundTasks):
    background_tasks.add_task(process_data, "123")
    return {"status": "queued"}
```

### 3. Call Downstream Service
```python
async def call_api():
    correlation_id = get_correlation_id()
    async with httpx.AsyncClient() as client:
        await client.post(
            url,
            headers={"X-Correlation-ID": correlation_id}
        )
```

### 4. Service Class
```python
class UserService:
    def __init__(self):
        self.logger = get_logger(__name__)

    async def create_user(self, username: str):
        self.logger.info("Creating user", username=username)
        # Logs automatically include request_id
```

### 5. Async Worker
```python
@preserve_request_id
async def worker(task_id: str):
    logger.info("Worker started", task_id=task_id)
    await do_work()

asyncio.create_task(worker("task-123"))
```

## HTTP Headers

### Request
- `X-Request-ID`: Your UUID4 (optional)
- `X-Correlation-ID`: Correlation UUID4 (optional)

### Response
- `X-Request-ID`: The request ID
- `X-Correlation-ID`: The correlation ID

## Testing

```bash
# With custom request ID
curl -H "X-Request-ID: 550e8400-e29b-41d4-a716-446655440000" \
     http://localhost:8000/api/v1/users

# With correlation ID
curl -H "X-Correlation-ID: 123e4567-e89b-12d3-a456-426614174000" \
     http://localhost:8000/api/v1/users
```

## Logging

All logs automatically include:
- `request_id`: Unique ID for this request
- `correlation_id`: ID shared across services

```python
logger.info("User created", user_id="123")
# Output includes: request_id=xxx, correlation_id=yyy
```

## Key Points

1. **Automatic**: Request ID added to all requests automatically
2. **Headers**: Available in request.state and response headers
3. **Logging**: Automatically in all log entries
4. **Background**: Use @preserve_request_id decorator
5. **Distributed**: Pass X-Correlation-ID to other services
6. **Security**: Only valid UUID4s accepted
7. **Testing**: Send X-Request-ID header for testing
