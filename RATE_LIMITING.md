# Rate Limiting System

This document describes the Redis-backed rate limiting system implemented for the agent service.

## Overview

The rate limiting system provides:
- Redis-backed distributed rate limiting
- Graceful fallback to in-memory storage when Redis is unavailable
- Tier-based rate limits (free, pro, enterprise)
- Multiple rate limiting strategies (by user ID, API key, or IP)
- Standard X-RateLimit-* response headers
- Configurable rate limits per endpoint

## Architecture

### Components

1. **Redis Manager** (`infrastructure/cache/redis.py`)
   - Async connection pool management
   - Health checks and monitoring
   - Graceful degradation when Redis is unavailable

2. **Rate Limit Middleware** (`api/middleware/rate_limit.py`)
   - Integration with slowapi library
   - Tier-based rate limiting
   - Custom key functions for different strategies
   - Response headers management

3. **Configuration** (`config/settings.py`)
   - Redis connection settings
   - Rate limiting feature flags
   - Default tier configuration

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT_TIER=free
```

### Settings

In `config/settings.py`:

```python
redis_url: SecretStr | None = None
rate_limit_enabled: bool = True
rate_limit_default_tier: str = "free"
```

## Rate Limit Tiers

Default tier limits (configured in `api/middleware/rate_limit.py`):

| Tier       | Rate Limit       | Use Case                |
|------------|------------------|-------------------------|
| free       | 100/hour         | Free tier users         |
| pro        | 1000/hour        | Paid users              |
| enterprise | 10000/hour       | Enterprise customers    |

## Usage

### Basic Rate Limiting

#### 1. By IP Address (Default)

```python
from fastapi import APIRouter, Request
from agent_service.api.middleware.rate_limit import limiter

router = APIRouter()

@router.get("/public/data")
@limiter.limit("10/minute")
async def get_public_data(request: Request):
    return {"data": "public information"}
```

#### 2. By User ID

```python
from agent_service.api.middleware.rate_limit import limiter, get_user_key

@router.get("/user/profile")
@limiter.limit("50/hour", key_func=get_user_key)
async def get_user_profile(request: Request):
    return {"profile": {}}
```

#### 3. By API Key

```python
from agent_service.api.middleware.rate_limit import limiter, get_api_key_key

@router.post("/api/analyze")
@limiter.limit("200/hour", key_func=get_api_key_key)
async def analyze_data(request: Request, data: dict):
    return {"analysis": "results"}
```

### Tier-Based Rate Limiting

Automatically adjusts rate limits based on user tier:

```python
from agent_service.api.middleware.rate_limit import rate_limit_by_tier

@router.post("/premium/process")
@rate_limit_by_tier()
async def process_premium(request: Request, data: dict):
    return {"status": "processed"}
```

### Custom Rate Limits

```python
from agent_service.api.middleware.rate_limit import rate_limit

@router.get("/search")
@rate_limit("100/hour")
async def search(request: Request, query: str):
    return {"results": [], "query": query}
```

### Multiple Rate Limits

Apply both short-term and long-term limits:

```python
@router.post("/api/submit")
@limiter.limit("5/minute")   # Short-term limit
@limiter.limit("100/hour")   # Long-term limit
async def submit_data(request: Request, data: dict):
    return {"submission_id": "12345"}
```

## Rate Limit Strategies

### 1. IP-Based (Default)

Rate limits by client IP address. Good for public endpoints.

```python
from agent_service.api.middleware.rate_limit import get_ip_key

@limiter.limit("10/minute", key_func=get_ip_key)
```

### 2. User-Based

Rate limits by authenticated user ID. Falls back to IP if not authenticated.

```python
from agent_service.api.middleware.rate_limit import get_user_key

@limiter.limit("50/hour", key_func=get_user_key)
```

### 3. API Key-Based

Rate limits by API key from Authorization or X-API-Key header.

```python
from agent_service.api.middleware.rate_limit import get_api_key_key

@limiter.limit("200/hour", key_func=get_api_key_key)
```

### 4. Custom Strategy

Create your own key function:

```python
def get_organization_key(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "organization_id"):
        return f"org:{user.organization_id}"
    return get_ip_key(request)

@limiter.limit("1000/hour", key_func=get_organization_key)
```

## Response Headers

All rate-limited endpoints include these headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1702483200
```

- `X-RateLimit-Limit`: Maximum requests allowed in the window
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Unix timestamp when the limit resets

## Error Handling

### 429 Too Many Requests

When rate limit is exceeded:

**Response:**
```json
{
    "error": "rate_limit_exceeded",
    "message": "Too many requests. Please try again later.",
    "detail": "1 per 1 minute"
}
```

**Headers:**
```
Status: 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1702483200
```

## Redis Setup

### Local Development

Using Docker:

```bash
docker run -d \
  --name redis \
  -p 6379:6379 \
  redis:7-alpine
```

### Production

Recommended configuration:
- Redis 6.0 or higher
- Persistent storage enabled
- Memory limits configured
- Authentication enabled
- TLS/SSL for connections

Example production Redis URL:
```
redis://:password@redis.example.com:6379/0
rediss://:password@redis.example.com:6380/0  # TLS
```

## Graceful Degradation

The system automatically handles Redis unavailability:

1. **Redis Available**: Uses Redis for distributed rate limiting
2. **Redis Unavailable**: Falls back to in-memory storage
   - Works for single-instance deployments
   - Not shared across multiple instances
   - Data lost on restart

Logs indicate the current mode:
```
INFO: Redis connection established and healthy
WARNING: Redis is not available - rate limiting will use in-memory storage
```

## Testing

### Manual Testing

Test rate limiting with curl:

```bash
# Make multiple requests to trigger rate limit
for i in {1..15}; do
  curl -i http://localhost:8000/public/data
  sleep 1
done
```

Expected behavior:
- First 10 requests: 200 OK with decreasing X-RateLimit-Remaining
- Request 11+: 429 Too Many Requests

### Unit Testing

```python
from fastapi.testclient import TestClient
from agent_service.api.app import app

client = TestClient(app)

def test_rate_limit():
    # Make requests up to the limit
    for i in range(10):
        response = client.get("/public/data")
        assert response.status_code == 200

    # Next request should be rate limited
    response = client.get("/public/data")
    assert response.status_code == 429
    assert "rate_limit_exceeded" in response.json()["error"]
```

## Monitoring

### Redis Health Check

Check Redis connection health:

```python
from agent_service.infrastructure.cache.redis import get_redis_manager

redis_manager = await get_redis_manager()
is_healthy = await redis_manager.health_check()
```

### Rate Limit Metrics

Monitor these metrics:
- Total rate limit hits (429 responses)
- Rate limit hits by endpoint
- Rate limit hits by tier
- Redis connection failures
- Fallback to in-memory storage events

## Best Practices

1. **Choose Appropriate Limits**
   - Public endpoints: Stricter limits (10-50/minute)
   - Authenticated endpoints: Moderate limits (100-1000/hour)
   - Premium endpoints: Generous limits (1000-10000/hour)

2. **Use Correct Strategy**
   - Public data: IP-based
   - User actions: User-based
   - API access: API key-based
   - Multi-tenant: Organization-based

3. **Apply Multiple Limits**
   - Combine short-term and long-term limits
   - Prevents burst attacks and sustained abuse

4. **Document Limits**
   - Include rate limits in API documentation
   - Communicate limits to users
   - Provide upgrade paths for higher limits

5. **Monitor and Adjust**
   - Track rate limit hits
   - Adjust limits based on usage patterns
   - Alert on unusual patterns

## Customization

### Modify Tier Limits

Edit `api/middleware/rate_limit.py`:

```python
RATE_LIMIT_TIERS = {
    "free": "50/hour",      # Changed from 100/hour
    "pro": "2000/hour",     # Changed from 1000/hour
    "enterprise": "unlimited",  # No limit
}
```

### Add New Tier

1. Add to `RATE_LIMIT_TIERS` dict
2. Update user/API key metadata to include new tier
3. Document in API docs

### Custom Rate Limit Window

Supported windows:
- `second`
- `minute`
- `hour`
- `day`

Example:
```python
@limiter.limit("1000/day")
@limiter.limit("100/hour")
@limiter.limit("10/minute")
```

## Troubleshooting

### Rate Limits Not Working

1. Check if rate limiting is enabled:
   ```bash
   RATE_LIMIT_ENABLED=true
   ```

2. Verify Redis connection:
   ```bash
   redis-cli ping
   ```

3. Check application logs for errors

### Redis Connection Issues

1. Verify Redis URL:
   ```bash
   REDIS_URL=redis://localhost:6379/0
   ```

2. Test Redis connectivity:
   ```bash
   redis-cli -u redis://localhost:6379/0 ping
   ```

3. Check firewall/network rules

### Incorrect Rate Limit Key

Ensure user/API key metadata is set correctly:

```python
# In auth middleware
request.state.user = user  # Must have 'id' and 'tier' attributes
request.state.api_key_meta = api_key  # Must have 'tier' attribute
```

## Migration Guide

### From No Rate Limiting

1. Add Redis to your infrastructure
2. Update environment variables
3. No code changes needed - defaults to disabled

### From In-Memory to Redis

1. Set `REDIS_URL` in environment
2. Restart application
3. Rate limits now shared across instances

## Security Considerations

1. **DoS Protection**: Rate limiting helps prevent DoS attacks
2. **API Abuse**: Prevents API abuse and resource exhaustion
3. **Fair Usage**: Ensures fair resource allocation among users
4. **Cost Control**: Limits infrastructure costs from excessive usage

## Performance

- **Redis Overhead**: ~1-2ms per request
- **In-Memory Overhead**: <1ms per request
- **Scalability**: Linear scaling with Redis cluster
- **Memory Usage**: ~100 bytes per unique key

## Future Enhancements

Potential improvements:
- [ ] Dynamic rate limits based on system load
- [ ] Rate limit analytics dashboard
- [ ] Automatic tier upgrades
- [ ] Geographic rate limiting
- [ ] Time-based rate limits (different limits for peak hours)
- [ ] Rate limit pooling (share limits across organization)
