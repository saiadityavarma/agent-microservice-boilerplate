# Sentry Error Tracking - Quick Start Guide

## 5-Minute Setup

### 1. Get Your Sentry DSN

```bash
# Sign up at https://sentry.io (free tier available)
# Create a new Python project
# Copy your DSN (looks like: https://abc123@o123.ingest.sentry.io/456)
```

### 2. Configure Environment

Add to your `.env` file:

```bash
SENTRY_DSN=https://your-key@sentry.io/your-project-id
SENTRY_ENVIRONMENT=production
```

### 3. Start Your App

```bash
python -m uvicorn agent_service.api.app:app --reload
```

Look for: `Sentry initialized successfully` in startup logs.

### 4. Test It Works

Trigger a test error:

```python
# Add this temporary endpoint to test
@app.get("/test-sentry")
async def test_sentry():
    1 / 0  # This will be captured by Sentry
```

Visit: http://localhost:8000/test-sentry

Check your Sentry dashboard - you should see the error!

## Basic Usage Patterns

### Pattern 1: Capture Exceptions

```python
from agent_service.infrastructure.observability.error_tracking import capture_exception

try:
    risky_operation()
except Exception as e:
    capture_exception(e, extra={"context": "what was happening"})
    raise
```

### Pattern 2: Add User Context

```python
from agent_service.infrastructure.observability.error_tracking import set_user_context

# After user logs in
set_user_context(user_id=user.id, email=user.email, username=user.username)
```

### Pattern 3: Track Request Context

```python
from fastapi import Request
from agent_service.infrastructure.observability.error_tracking import set_request_context

@app.post("/api/endpoint")
async def endpoint(request: Request):
    set_request_context(request)  # Add this at the start
    # ... rest of your code
```

### Pattern 4: Track Important Events

```python
from agent_service.infrastructure.observability.error_tracking import capture_message

# Track business events
capture_message(
    "User upgraded subscription",
    level="info",
    extra={"user_id": user_id, "new_plan": "premium"}
)
```

## Common Use Cases

### Use Case 1: API Endpoint Error Tracking

```python
@app.post("/process-data")
async def process_data(request: Request, data: dict):
    set_request_context(request)

    try:
        result = process(data)
        return {"status": "success", "result": result}
    except Exception as e:
        capture_exception(e, extra={"data_size": len(data)})
        raise HTTPException(status_code=500, detail="Processing failed")
```

### Use Case 2: User Action Tracking

```python
from agent_service.infrastructure.observability.error_tracking import (
    add_breadcrumb,
    capture_exception,
)

@app.post("/checkout")
async def checkout(request: Request, cart: dict):
    add_breadcrumb(message="Checkout started", category="ecommerce")

    try:
        payment_result = process_payment(cart)
        add_breadcrumb(message="Payment processed", category="ecommerce")
        return {"status": "success"}
    except Exception as e:
        # Breadcrumbs will show the journey leading to the error
        capture_exception(e)
        raise
```

### Use Case 3: Monitoring Quotas

```python
from agent_service.infrastructure.observability.error_tracking import capture_message

usage = get_user_usage(user_id)
quota = get_user_quota(user_id)

if usage >= quota * 0.9:
    capture_message(
        "User approaching quota limit",
        level="warning",
        extra={
            "user_id": user_id,
            "usage": usage,
            "quota": quota,
            "percentage": (usage/quota)*100
        }
    )
```

## Configuration Options

```bash
# .env file settings
SENTRY_DSN=https://key@sentry.io/project       # Required to enable Sentry
SENTRY_ENVIRONMENT=production                  # Environment tag
SENTRY_SAMPLE_RATE=1.0                        # 1.0 = capture all errors
SENTRY_TRACES_SAMPLE_RATE=0.1                 # 0.1 = capture 10% of transactions
```

### Sample Rate Recommendations

**Production (High Traffic)**:
```bash
SENTRY_SAMPLE_RATE=1.0          # Capture all errors (important!)
SENTRY_TRACES_SAMPLE_RATE=0.01  # Sample 1% of transactions
```

**Staging**:
```bash
SENTRY_SAMPLE_RATE=1.0          # Capture all errors
SENTRY_TRACES_SAMPLE_RATE=0.5   # Sample 50% of transactions
```

**Development**:
```bash
SENTRY_SAMPLE_RATE=1.0          # Capture all errors
SENTRY_TRACES_SAMPLE_RATE=1.0   # Sample 100% of transactions
```

## What Gets Automatically Filtered?

Sentry won't send these (to reduce noise):

- 400 Bad Request
- 404 Not Found
- 429 Rate Limit Exceeded
- Validation errors
- Sensitive headers (Authorization, Cookie, API-Key)
- Sensitive params (password, token, secret)

## What Gets Automatically Sent?

Sentry will send these (important to track):

- 500 Internal Server Error
- 401 Unauthorized (security concern)
- 403 Forbidden (security concern)
- Unexpected exceptions
- Messages you explicitly capture

## Available Functions

```python
# Initialization (automatic in app.py)
init_sentry(dsn, environment, release)

# Context Management
set_user_context(user_id, email, username)
set_request_context(request)
clear_user_context()

# Capturing Events
capture_exception(error, extra={}, level="error")
capture_message(message, level="info", extra={})

# Tracking
add_breadcrumb(message, category, level, data)
set_tag(key, value)
set_context(key, value_dict)

# Cleanup
flush(timeout=2.0)
```

## Troubleshooting

### Not seeing errors in Sentry?

1. Check DSN is set: `echo $SENTRY_DSN`
2. Check logs for: "Sentry initialized successfully"
3. Verify error isn't filtered (4xx errors are filtered)
4. Check sample rate isn't 0

### Too many events?

Lower the sample rates:
```bash
SENTRY_SAMPLE_RATE=0.5          # Capture 50% of errors
SENTRY_TRACES_SAMPLE_RATE=0.01  # Capture 1% of transactions
```

### Missing context in errors?

Make sure you're calling context functions:
```python
set_request_context(request)  # Call early in request
set_user_context(...)          # Call after authentication
```

## Next Steps

- Read the full documentation: `ERROR_TRACKING_README.md`
- See code examples: `error_tracking_examples.py`
- Set up alerts in Sentry dashboard
- Configure integrations (Slack, email, etc.)

## Resources

- Sentry Dashboard: https://sentry.io
- Python SDK Docs: https://docs.sentry.io/platforms/python/
- FastAPI Guide: https://docs.sentry.io/platforms/python/guides/fastapi/
