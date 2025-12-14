# Rate Limiting System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Request                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                         │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Middleware Stack (Ordered)                     │ │
│  │                                                              │ │
│  │  1. CORS Middleware                                         │ │
│  │  2. Security Headers Middleware                             │ │
│  │  3. Request Logging Middleware                              │ │
│  │  4. [Rate Limit integrated via decorators]                  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                             │                                     │
│                             ▼                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Route Handler                            │ │
│  │                                                              │ │
│  │  @limiter.limit("100/hour", key_func=get_user_key)         │ │
│  │  async def endpoint(request: Request):                      │ │
│  │      # Rate limiting happens here via decorator             │ │
│  │      return {"data": "response"}                            │ │
│  └────────────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   Rate Limit Middleware (slowapi)     │
        │                                        │
        │  1. Extract rate limit key             │
        │  2. Check current count in storage     │
        │  3. Increment counter                  │
        │  4. Add X-RateLimit-* headers          │
        │  5. Return 429 if exceeded             │
        └───────────┬────────────┬───────────────┘
                    │            │
         ┌──────────┘            └────────────┐
         │                                    │
         ▼                                    ▼
┌─────────────────┐                  ┌────────────────┐
│  Redis Storage  │                  │ In-Memory      │
│  (Primary)      │                  │ Storage        │
│                 │                  │ (Fallback)     │
│  - Distributed  │                  │                │
│  - Persistent   │                  │ - Local only   │
│  - Shared       │                  │ - Volatile     │
└─────────────────┘                  └────────────────┘
```

## Component Flow

### 1. Request Processing Flow

```
Client Request
     │
     ▼
[Parse Request Headers]
     │
     ├─ Authorization: Bearer <token>
     ├─ X-API-Key: <key>
     └─ Client IP: <ip>
     │
     ▼
[Determine Rate Limit Key]
     │
     ├─ User authenticated? → user:<user_id>
     ├─ API key present? → api_key:<key_prefix>
     └─ Fallback → ip:<ip_address>
     │
     ▼
[Get User/API Key Tier]
     │
     ├─ free → 100/hour
     ├─ pro → 1000/hour
     └─ enterprise → 10000/hour
     │
     ▼
[Check Rate Limit]
     │
     ├─ Query Redis: GET rate_limit:<key>
     ├─ Current count < limit? → Allow
     └─ Current count >= limit? → Block (429)
     │
     ▼
[Update Counter]
     │
     └─ Redis: INCR rate_limit:<key>
     └─ Redis: EXPIRE rate_limit:<key> <window>
     │
     ▼
[Add Response Headers]
     │
     ├─ X-RateLimit-Limit
     ├─ X-RateLimit-Remaining
     └─ X-RateLimit-Reset
     │
     ▼
[Return Response]
```

### 2. Key Generation Flow

```
Request Object
     │
     ▼
┌─────────────────────┐
│ get_user_key()      │
├─────────────────────┤
│ 1. Check request.state.user
│ 2. If exists: return "user:{user.id}"
│ 3. Else: fallback to get_ip_key()
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ get_api_key_key()   │
├─────────────────────┤
│ 1. Check Authorization header
│ 2. Check X-API-Key header
│ 3. If exists: return "api_key:{key[:16]}"
│ 4. Else: fallback to get_ip_key()
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ get_ip_key()        │
├─────────────────────┤
│ 1. Extract client IP
│ 2. Return "ip:{ip_address}"
└─────────────────────┘
```

### 3. Tier Extraction Flow

```
Request Object
     │
     ▼
┌─────────────────────────────┐
│ get_tier_from_request()      │
├─────────────────────────────┤
│ 1. Check request.state.user.tier
│    ├─ Found? → Return user tier
│    └─ Not found? → Continue
│                                │
│ 2. Check request.state.api_key_meta.tier
│    ├─ Found? → Return API key tier
│    └─ Not found? → Continue
│                                │
│ 3. Return default tier (from settings)
└────────────┬────────────────┘
             │
             ▼
      ┌──────────────┐
      │ Tier String  │
      │              │
      │ - free       │
      │ - pro        │
      │ - enterprise │
      └──────────────┘
```

## Redis Data Structure

### Rate Limit Keys

```
Key Pattern: rate_limit:{strategy}:{identifier}:{window}

Examples:
- rate_limit:ip:192.168.1.1:minute
- rate_limit:user:user_123:hour
- rate_limit:api_key:sk_live_abc123:hour
- rate_limit:org:org_456:day
```

### Redis Operations

```python
# Increment counter
INCR rate_limit:user:123:hour
# Returns: 1, 2, 3, ... (current count)

# Set expiration (on first increment)
EXPIRE rate_limit:user:123:hour 3600
# TTL set to window duration (3600 seconds = 1 hour)

# Check current count
GET rate_limit:user:123:hour
# Returns: current count

# Get TTL (for Reset header)
TTL rate_limit:user:123:hour
# Returns: seconds until expiration
```

## Class Hierarchy

```
┌─────────────────────────┐
│    RedisManager         │
├─────────────────────────┤
│ - _pool: ConnectionPool │
│ - _client: Redis        │
│ - _is_available: bool   │
├─────────────────────────┤
│ + initialize()          │
│ + close()               │
│ + health_check()        │
│ + get_client()          │
│ + is_available          │
└─────────────────────────┘
           │
           │ creates
           ▼
┌─────────────────────────┐
│   Redis Client          │
├─────────────────────────┤
│ + get()                 │
│ + set()                 │
│ + incr()                │
│ + expire()              │
│ + ttl()                 │
│ + ping()                │
└─────────────────────────┘

┌─────────────────────────┐
│    Limiter (slowapi)    │
├─────────────────────────┤
│ - key_func: Callable    │
│ - storage_uri: str      │
│ - strategy: str         │
│ - headers_enabled: bool │
├─────────────────────────┤
│ + limit()               │
│ + reset()               │
└─────────────────────────┘
```

## Decorator Pattern

```python
# Route without rate limiting
async def endpoint(request: Request):
    return {"data": "response"}

# Becomes...

# Route with rate limiting
@limiter.limit("100/hour", key_func=get_user_key)
async def endpoint(request: Request):
    # Decorator wraps function:
    # 1. Extract key using key_func(request)
    # 2. Check rate limit in storage
    # 3. If exceeded: raise RateLimitExceeded
    # 4. If allowed: increment counter
    # 5. Add headers to response
    # 6. Call original function
    return {"data": "response"}
```

## Graceful Degradation

```
Application Startup
     │
     ▼
[Attempt Redis Connection]
     │
     ├─ Success ───────────┐
     │                      │
     └─ Failure            │
          │                │
          ▼                ▼
    [Use In-Memory]  [Use Redis]
          │                │
          │                │
          ├─ Single instance only
          ├─ Not persistent
          └─ Lost on restart
                           │
                           ├─ Distributed
                           ├─ Persistent
                           └─ Shared across instances
```

## Error Handling Flow

```
Rate Limit Check
     │
     ▼
[Counter > Limit?]
     │
     ├─ No → Continue
     │        │
     │        ▼
     │   [Process Request]
     │        │
     │        ▼
     │   [Add Headers]
     │        │
     │        └─ X-RateLimit-Limit: 100
     │        └─ X-RateLimit-Remaining: 47
     │        └─ X-RateLimit-Reset: 1702483200
     │        │
     │        ▼
     │   [Return 200 OK]
     │
     └─ Yes → [Raise RateLimitExceeded]
               │
               ▼
          [Exception Handler]
               │
               ▼
          [Build Error Response]
               │
               ├─ error: "rate_limit_exceeded"
               ├─ message: "Too many requests..."
               └─ detail: "100 per 1 hour"
               │
               ▼
          [Add Headers]
               │
               ├─ X-RateLimit-Limit: 100
               ├─ X-RateLimit-Remaining: 0
               ├─ X-RateLimit-Reset: 1702483200
               └─ Retry-After: 3456
               │
               ▼
          [Return 429 Too Many Requests]
```

## Configuration Flow

```
Environment Variables (.env)
     │
     ├─ REDIS_URL
     ├─ RATE_LIMIT_ENABLED
     └─ RATE_LIMIT_DEFAULT_TIER
     │
     ▼
Settings Class (settings.py)
     │
     ├─ redis_url: SecretStr
     ├─ rate_limit_enabled: bool
     └─ rate_limit_default_tier: str
     │
     ▼
Application Initialization (app.py)
     │
     ├─ Initialize Redis Manager
     ├─ Setup Rate Limiting
     └─ Register Error Handlers
     │
     ▼
Rate Limiter Configuration
     │
     ├─ Storage: Redis or In-Memory
     ├─ Strategy: Fixed Window
     └─ Headers: Enabled
```

## Multi-Instance Deployment

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Instance 1  │     │  Instance 2  │     │  Instance 3  │
│              │     │              │     │              │
│  FastAPI App │     │  FastAPI App │     │  FastAPI App │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       │                    │                    │
       └────────────┬───────┴────────────────────┘
                    │
                    ▼
           ┌─────────────────┐
           │  Redis Cluster  │
           │                 │
           │  Shared state   │
           │  across all     │
           │  instances      │
           └─────────────────┘

- All instances share the same Redis
- Rate limits enforced globally
- User hitting different instances still rate limited
```

## Performance Characteristics

```
┌────────────────────┬──────────────┬──────────────┐
│ Operation          │ Redis        │ In-Memory    │
├────────────────────┼──────────────┼──────────────┤
│ Latency            │ 1-2ms        │ <0.1ms       │
│ Throughput         │ 100k+ req/s  │ 1M+ req/s    │
│ Persistence        │ Yes          │ No           │
│ Shared State       │ Yes          │ No           │
│ Memory Usage       │ ~100 bytes   │ ~100 bytes   │
│ Scalability        │ Horizontal   │ Vertical     │
└────────────────────┴──────────────┴──────────────┘
```

## Security Model

```
Rate Limiting Security Layers:

1. IP-based Rate Limiting
   └─ Prevents DoS attacks from single source

2. User-based Rate Limiting
   └─ Prevents account abuse
   └─ Fair usage per user

3. API Key-based Rate Limiting
   └─ Prevents API key abuse
   └─ Monetization tiers

4. Tier-based Limits
   └─ free: Basic protection
   └─ pro: Higher limits for paying customers
   └─ enterprise: Custom limits

5. Multiple Rate Limits
   └─ Short-term (per minute)
   └─ Long-term (per hour/day)
```

## Monitoring Points

```
Application Metrics:
├─ Rate limit hits (429 responses)
├─ Rate limit hits by endpoint
├─ Rate limit hits by tier
├─ Rate limit hits by strategy
├─ Average remaining quota
└─ Rate limit reset frequency

Redis Metrics:
├─ Connection pool utilization
├─ Redis command latency
├─ Redis connection failures
├─ Fallback to in-memory events
├─ Redis memory usage
└─ Redis CPU usage

Business Metrics:
├─ Users hitting limits
├─ API keys hitting limits
├─ Tier upgrade candidates
├─ Abuse patterns
└─ Cost per request
```

This architecture provides a robust, scalable, and production-ready rate limiting system.
