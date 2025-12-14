# Sentry Error Tracking Integration

Comprehensive error tracking and monitoring using Sentry SDK for the Agent Service.

## Features

- **Automatic Error Capture**: Captures unhandled exceptions across the application
- **Performance Monitoring**: Tracks transaction performance with configurable sampling
- **User Context**: Attaches user information to error events
- **Request Context**: Includes request details in error reports
- **Error Filtering**: Filters out expected errors and sensitive data
- **Breadcrumbs**: Tracks user actions leading up to errors
- **Custom Tags & Contexts**: Add structured metadata to errors
- **Integration**: Works with FastAPI, SQLAlchemy, Redis, and logging

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Sentry Configuration
SENTRY_DSN=https://your-key@sentry.io/your-project-id
SENTRY_ENVIRONMENT=production  # or staging, dev, local
SENTRY_SAMPLE_RATE=1.0  # 1.0 = capture all errors (100%)
SENTRY_TRACES_SAMPLE_RATE=0.1  # 0.1 = capture 10% of transactions
```

### Settings

The following settings are available in `agent_service/config/settings.py`:

- `sentry_dsn`: Sentry Data Source Name (required to enable Sentry)
- `sentry_environment`: Environment name (defaults to `environment` setting)
- `sentry_sample_rate`: Error sampling rate (0.0-1.0, default 1.0)
- `sentry_traces_sample_rate`: Transaction sampling rate (0.0-1.0, default 0.1)

## Usage

### Basic Error Capture

```python
from agent_service.infrastructure.observability.error_tracking import (
    capture_exception,
    capture_message,
)

try:
    risky_operation()
except Exception as e:
    capture_exception(
        e,
        extra={
            "operation": "data_processing",
            "input_size": 1000,
        },
        level="error",
    )
    raise
```

### User Context

```python
from agent_service.infrastructure.observability.error_tracking import set_user_context

@app.post("/login")
async def login(username: str, password: str):
    user = authenticate_user(username, password)

    # Attach user info to all subsequent errors
    set_user_context(
        user_id=str(user.id),
        email=user.email,
        username=user.username,
        role=user.role,  # custom field
    )

    return {"status": "success"}
```

### Request Context

```python
from fastapi import Request
from agent_service.infrastructure.observability.error_tracking import set_request_context

@app.get("/process")
async def process_data(request: Request):
    # Add request details to error context
    set_request_context(request)

    # ... endpoint logic
```

### Breadcrumbs

Track user actions leading to errors:

```python
from agent_service.infrastructure.observability.error_tracking import add_breadcrumb

# Track important actions
add_breadcrumb(
    message="User started checkout process",
    category="ecommerce",
    level="info",
    data={"cart_items": 3, "total": 99.99},
)

# ... later if error occurs, breadcrumbs will show the trail
```

### Tags for Filtering

```python
from agent_service.infrastructure.observability.error_tracking import set_tag

# Add tags to filter and search errors in Sentry
set_tag("payment_provider", "stripe")
set_tag("feature_flag", "new_checkout")
set_tag("api_version", "v2")
```

### Custom Contexts

```python
from agent_service.infrastructure.observability.error_tracking import set_context

# Add structured data to errors
set_context("shopping_cart", {
    "item_count": 3,
    "total_value": 99.99,
    "currency": "USD",
    "discount_applied": True,
})

set_context("agent_execution", {
    "agent_id": "agent_123",
    "task_type": "analysis",
    "priority": "high",
})
```

### Capture Messages

Track important events without exceptions:

```python
from agent_service.infrastructure.observability.error_tracking import capture_message

# Track business events
capture_message(
    "User upgraded subscription",
    level="info",
    extra={
        "user_id": user_id,
        "old_tier": "free",
        "new_tier": "pro",
        "revenue_impact": 50.0,
    },
)

# Monitor quota usage
if usage > quota * 0.9:
    capture_message(
        "User approaching quota limit",
        level="warning",
        extra={
            "user_id": user_id,
            "current_usage": usage,
            "quota_limit": quota,
        },
    )
```

## Error Filtering

The integration automatically filters:

1. **Expected Client Errors**: 4xx errors (except 401 and 403)
2. **Rate Limit Errors**: 429 Too Many Requests
3. **Validation Errors**: Request validation failures
4. **Sensitive Data**: Headers, query params, and breadcrumbs

### Filtered Sensitive Data

The following are automatically filtered:

**Headers:**
- authorization
- cookie
- x-api-key
- x-auth-token
- x-csrf-token
- x-session-id

**Query Parameters:**
- password
- token
- api_key
- secret
- access_token
- refresh_token

## Integrations

### FastAPI Integration

Automatically enabled when Sentry is initialized:

- Captures request/response details
- Groups transactions by endpoint (not URL)
- Tracks server errors (5xx status codes)
- Includes request headers (filtered)

### Logging Integration

Automatically captures log messages:

- INFO and above as breadcrumbs
- ERROR and above as Sentry events

### Redis Integration

Tracks Redis operations:

- Command execution
- Connection errors
- Performance metrics

### SQLAlchemy Integration

Tracks database operations:

- Query execution
- Connection pooling
- Database errors

## Performance Monitoring

Sentry automatically tracks:

- HTTP request duration
- Database query performance
- Redis operation timing
- Custom transaction spans

Configure sampling rate to balance performance and cost:

```python
# High-traffic production: sample 1-10%
SENTRY_TRACES_SAMPLE_RATE=0.01  # 1%

# Low-traffic or staging: sample more
SENTRY_TRACES_SAMPLE_RATE=0.5  # 50%

# Development: sample everything
SENTRY_TRACES_SAMPLE_RATE=1.0  # 100%
```

## Best Practices

### 1. Set User Context Early

```python
# Good: Set user context after authentication
set_user_context(user_id=user.id, email=user.email)

# Bad: Don't forget to clear on logout
clear_user_context()
```

### 2. Add Breadcrumbs for Important Actions

```python
# Track user journey
add_breadcrumb(message="User viewed product", category="navigation")
add_breadcrumb(message="User added to cart", category="ecommerce")
add_breadcrumb(message="User started checkout", category="ecommerce")
# ... error occurs, breadcrumbs show the journey
```

### 3. Use Appropriate Log Levels

```python
# error: Unexpected errors that need immediate attention
capture_exception(e, level="error")

# warning: Expected errors or concerning situations
capture_exception(ValidationError, level="warning")

# info: Business events and monitoring
capture_message("User upgraded", level="info")
```

### 4. Don't Log Sensitive Data

```python
# Good: Generic error info
capture_exception(e, extra={"user_id": user_id})

# Bad: Including passwords or tokens
capture_exception(e, extra={"password": password})  # DON'T DO THIS
```

### 5. Use Tags for Filtering

```python
# Makes it easy to filter errors in Sentry UI
set_tag("environment", "production")
set_tag("payment_provider", "stripe")
set_tag("api_version", "v2")
```

### 6. Add Context for Complex Operations

```python
# Helps debug complex workflows
set_context("agent_execution", {
    "agent_id": agent_id,
    "task_type": task_type,
    "priority": priority,
    "timeout": timeout,
})
```

## Monitoring Recommendations

### Critical Errors (immediate alert)
- Authentication failures (401, 403)
- Payment processing errors
- Data corruption errors
- Critical API failures

### Warning Events (daily review)
- Users approaching quota limits
- High-value transactions
- Slow database queries
- Rate limit near-misses

### Info Events (weekly review)
- Business metrics (upgrades, conversions)
- Feature usage statistics
- Performance benchmarks

## Troubleshooting

### Sentry Not Capturing Errors

1. Check DSN is set: `echo $SENTRY_DSN`
2. Check initialization in logs: "Sentry initialized successfully"
3. Verify sample rate is not 0: `SENTRY_SAMPLE_RATE=1.0`
4. Check if error is being filtered (4xx errors are filtered)

### Too Many Events

1. Lower sample rates:
   ```bash
   SENTRY_SAMPLE_RATE=0.5  # Capture 50% of errors
   SENTRY_TRACES_SAMPLE_RATE=0.01  # Capture 1% of transactions
   ```

2. Review error filtering rules in `error_tracking.py`
3. Consider filtering expected errors at application level

### Missing Context

1. Ensure `set_request_context()` is called early in request
2. Verify `set_user_context()` is called after authentication
3. Check that context is set before error occurs

### Sensitive Data Leaking

1. Review `SENSITIVE_HEADERS` and `SENSITIVE_PARAMS` in `error_tracking.py`
2. Add additional patterns to filter
3. Enable `send_default_pii=False` in Sentry init (already default)

## Testing

Test Sentry integration in development:

```python
# Force an error to test Sentry
@app.get("/test-sentry")
async def test_sentry():
    set_user_context(user_id="test_user")
    add_breadcrumb(message="Testing Sentry integration")

    try:
        1 / 0  # Intentional error
    except Exception as e:
        capture_exception(e, extra={"test": True})
        raise
```

## Resources

- [Sentry Python SDK Documentation](https://docs.sentry.io/platforms/python/)
- [FastAPI Integration Guide](https://docs.sentry.io/platforms/python/guides/fastapi/)
- [Performance Monitoring](https://docs.sentry.io/product/performance/)
- [Best Practices](https://docs.sentry.io/platforms/python/best-practices/)

## Examples

See `error_tracking_examples.py` for comprehensive usage examples including:
- Basic error capture
- User context management
- Tags and filtering
- Custom contexts
- Business event tracking
- Quota monitoring
