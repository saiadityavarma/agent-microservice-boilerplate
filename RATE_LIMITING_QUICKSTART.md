# Rate Limiting - Quick Start Guide

Get rate limiting up and running in 5 minutes.

## Step 1: Install Dependencies

Add to your `requirements.txt` or install directly:

```bash
pip install redis[hiredis]>=5.0.0 slowapi>=0.1.9
```

Or if using poetry:

```bash
poetry add redis[hiredis] slowapi
```

## Step 2: Start Redis (Local Development)

### Option A: Using Docker (Recommended)

```bash
docker run -d \
  --name redis-rate-limit \
  -p 6379:6379 \
  redis:7-alpine
```

### Option B: Using Homebrew (macOS)

```bash
brew install redis
brew services start redis
```

### Option C: Using apt (Ubuntu/Debian)

```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

Verify Redis is running:

```bash
redis-cli ping
# Should return: PONG
```

## Step 3: Configure Environment

Create or update your `.env` file:

```bash
# Add these lines to .env
REDIS_URL=redis://localhost:6379/0
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT_TIER=free
```

## Step 4: Verify Installation

The rate limiting system is already integrated into your FastAPI app. Start your server:

```bash
# From the project root
python -m agent_service.main

# Or if using uvicorn directly
uvicorn agent_service.api.app:app --reload
```

Check the logs - you should see:

```
INFO: Redis connection established and healthy
INFO: Rate limiting enabled with default tier: free
```

## Step 5: Add Rate Limiting to Your Routes

### Example 1: Simple IP-based Rate Limit

Edit any route file (e.g., `src/agent_service/api/routes/agents.py`):

```python
from fastapi import APIRouter, Request
from agent_service.api.middleware.rate_limit import limiter

router = APIRouter()

@router.get("/agents")
@limiter.limit("100/hour")  # Add this decorator
async def list_agents(request: Request):  # Add request parameter
    return {"agents": []}
```

### Example 2: Tier-based Rate Limit

```python
from agent_service.api.middleware.rate_limit import rate_limit_by_tier

@router.post("/agents/execute")
@rate_limit_by_tier()
async def execute_agent(request: Request, data: dict):
    return {"status": "executed"}
```

## Step 6: Test Rate Limiting

### Manual Test with cURL

```bash
# Make multiple requests to test the limit
for i in {1..15}; do
  echo "Request $i:"
  curl -i http://localhost:8000/agents | grep -E "(HTTP|X-RateLimit)"
  sleep 1
done
```

Expected output:
- First 100 requests: `HTTP/1.1 200 OK` with `X-RateLimit-Remaining` decreasing
- Request 101: `HTTP/1.1 429 Too Many Requests`

### Test with Python

```python
import requests

url = "http://localhost:8000/agents"

for i in range(15):
    response = requests.get(url)
    print(f"Request {i+1}: {response.status_code}")
    print(f"  Remaining: {response.headers.get('X-RateLimit-Remaining')}")

    if response.status_code == 429:
        print(f"  Rate limited! Error: {response.json()}")
        break
```

## Common Rate Limit Patterns

### Pattern 1: Public Endpoint

```python
@router.get("/public/status")
@limiter.limit("10/minute")
async def public_status(request: Request):
    return {"status": "ok"}
```

### Pattern 2: Authenticated User Endpoint

```python
from agent_service.api.middleware.rate_limit import get_user_key

@router.get("/user/dashboard")
@limiter.limit("100/hour", key_func=get_user_key)
async def user_dashboard(request: Request):
    return {"data": {}}
```

### Pattern 3: API Key Endpoint

```python
from agent_service.api.middleware.rate_limit import get_api_key_key

@router.post("/api/process")
@limiter.limit("1000/hour", key_func=get_api_key_key)
async def process_api(request: Request, data: dict):
    return {"result": "processed"}
```

### Pattern 4: Multiple Limits

```python
@router.post("/api/expensive-operation")
@limiter.limit("5/minute")    # Short-term limit
@limiter.limit("100/hour")     # Long-term limit
async def expensive_operation(request: Request):
    return {"result": "completed"}
```

## Customizing Rate Limits

### Change Default Tiers

Edit `src/agent_service/api/middleware/rate_limit.py`:

```python
RATE_LIMIT_TIERS = {
    "free": "50/hour",        # Modified
    "pro": "500/hour",        # Modified
    "enterprise": "5000/hour",  # Modified
}
```

### Add Custom Tier

1. Add to `RATE_LIMIT_TIERS`:
```python
RATE_LIMIT_TIERS = {
    "free": "100/hour",
    "pro": "1000/hour",
    "enterprise": "10000/hour",
    "custom": "2500/hour",  # New tier
}
```

2. Set tier in user object:
```python
request.state.user = User(id="123", tier="custom")
```

## Troubleshooting

### Redis Connection Failed

**Error:** `Failed to connect to Redis`

**Solution:**
1. Check Redis is running: `redis-cli ping`
2. Verify REDIS_URL in `.env`
3. Check firewall/port 6379

### Rate Limiting Not Working

**Checklist:**
- [ ] `RATE_LIMIT_ENABLED=true` in `.env`
- [ ] Added `request: Request` parameter to route
- [ ] Added rate limit decorator to route
- [ ] Redis is running (or using in-memory fallback)

### No Rate Limit Headers

**Issue:** Response missing `X-RateLimit-*` headers

**Solution:** Ensure you're using the limiter decorators:
```python
@limiter.limit("100/hour")  # ✓ Correct
```

Not:
```python
@rate_limit("100/hour")  # ✗ Missing headers
```

## Production Checklist

Before deploying to production:

- [ ] Configure Redis with authentication
- [ ] Enable Redis persistence
- [ ] Use Redis Sentinel or Cluster for HA
- [ ] Enable TLS/SSL for Redis connections
- [ ] Set appropriate rate limits for each tier
- [ ] Monitor rate limit hits and adjust limits
- [ ] Set up alerts for Redis connection failures
- [ ] Document rate limits in API documentation
- [ ] Configure backup strategy for Redis data
- [ ] Test failover to in-memory storage

## Next Steps

1. **Review Examples:** Check `src/agent_service/api/middleware/rate_limit_examples.py`
2. **Read Full Documentation:** See `RATE_LIMITING.md`
3. **Customize Tiers:** Adjust limits based on your needs
4. **Add Monitoring:** Set up metrics for rate limit hits
5. **Update API Docs:** Document rate limits for API consumers

## Getting Help

- Check logs for error messages
- Review `RATE_LIMITING.md` for detailed documentation
- Test with example code in `rate_limit_examples.py`
- Run tests: `pytest src/agent_service/api/middleware/test_rate_limit.py`

## Summary

You now have:
- ✅ Redis-backed distributed rate limiting
- ✅ Tier-based rate limits (free, pro, enterprise)
- ✅ Multiple rate limiting strategies (IP, user, API key)
- ✅ Graceful fallback when Redis unavailable
- ✅ Standard X-RateLimit-* headers
- ✅ Configurable limits per endpoint

Start protecting your endpoints by adding rate limit decorators!
