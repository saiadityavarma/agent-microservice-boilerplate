# Prometheus Metrics Usage Guide

This guide explains how to use the enhanced Prometheus metrics in the agent service.

## Available Metrics

### Authentication Metrics

#### `auth_login_total`
Counter for total authentication login attempts.

**Labels:**
- `provider`: Authentication provider (e.g., "azure_ad", "cognito", "custom")
- `success`: "true" or "false"

**Usage:**
```python
from agent_service.infrastructure.observability.metrics import AUTH_LOGIN_TOTAL

# Successful login
AUTH_LOGIN_TOTAL.labels(provider="azure_ad", success="true").inc()

# Failed login
AUTH_LOGIN_TOTAL.labels(provider="azure_ad", success="false").inc()
```

#### `auth_token_refresh_total`
Counter for total token refresh attempts.

**Labels:**
- `provider`: Authentication provider
- `success`: "true" or "false"

**Usage:**
```python
from agent_service.infrastructure.observability.metrics import AUTH_TOKEN_REFRESH_TOTAL

# Successful token refresh
AUTH_TOKEN_REFRESH_TOTAL.labels(provider="cognito", success="true").inc()

# Failed token refresh
AUTH_TOKEN_REFRESH_TOTAL.labels(provider="cognito", success="false").inc()
```

#### `auth_failed_attempts_total`
Counter for total failed authentication attempts.

**Labels:**
- `reason`: Failure reason (e.g., "invalid_token", "expired_token", "invalid_credentials")

**Usage:**
```python
from agent_service.infrastructure.observability.metrics import AUTH_FAILED_ATTEMPTS_TOTAL

# Track specific failure reasons
AUTH_FAILED_ATTEMPTS_TOTAL.labels(reason="invalid_token").inc()
AUTH_FAILED_ATTEMPTS_TOTAL.labels(reason="expired_token").inc()
AUTH_FAILED_ATTEMPTS_TOTAL.labels(reason="invalid_credentials").inc()
```

### Database Metrics

#### `db_pool_size` (Gauge)
Current database connection pool size.

**Auto-collected by:** `MetricsCollector` in `metrics_collectors.py`

**Manual Usage:**
```python
from agent_service.infrastructure.observability.metrics import DB_POOL_SIZE

DB_POOL_SIZE.set(10)
```

#### `db_pool_checked_out` (Gauge)
Number of database connections currently checked out.

**Auto-collected by:** `MetricsCollector` in `metrics_collectors.py`

#### `db_query_duration_seconds`
Histogram for database query duration.

**Labels:**
- `query_type`: Type of query (e.g., "select", "insert", "update", "delete")

**Usage:**
```python
import time
from agent_service.infrastructure.observability.metrics import DB_QUERY_DURATION_SECONDS

start = time.perf_counter()
# Execute query
result = await session.execute(query)
duration = time.perf_counter() - start

DB_QUERY_DURATION_SECONDS.labels(query_type="select").observe(duration)
```

**Better with context manager:**
```python
from contextlib import contextmanager
import time

@contextmanager
def track_query_time(query_type: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start
        DB_QUERY_DURATION_SECONDS.labels(query_type=query_type).observe(duration)

# Usage
with track_query_time("select"):
    result = await session.execute(select(User))
```

### Redis Metrics

#### `redis_connections_active` (Gauge)
Number of active Redis connections.

**Auto-collected by:** `MetricsCollector` in `metrics_collectors.py`

#### `redis_operations_total`
Counter for total Redis operations.

**Labels:**
- `operation`: Type of operation (e.g., "get", "set", "delete", "expire")

**Usage:**
```python
from agent_service.infrastructure.observability.metrics import REDIS_OPERATIONS_TOTAL

# Track Redis operations
REDIS_OPERATIONS_TOTAL.labels(operation="get").inc()
REDIS_OPERATIONS_TOTAL.labels(operation="set").inc()
REDIS_OPERATIONS_TOTAL.labels(operation="delete").inc()
```

**With wrapper:**
```python
from functools import wraps

def track_redis_operation(operation: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            REDIS_OPERATIONS_TOTAL.labels(operation=operation).inc()
            return result
        return wrapper
    return decorator

# Usage
@track_redis_operation("get")
async def get_cache(key: str):
    redis = await get_redis()
    return await redis.get(key)
```

### Agent Metrics

#### `agent_invocations_total`
Counter for total agent invocations (already exists, enhanced with new metrics).

**Labels:**
- `agent_name`: Name of the agent
- `status`: "success" or "error"

#### `agent_execution_duration_seconds`
Histogram for agent execution duration.

**Labels:**
- `agent_name`: Name of the agent

**Usage:**
```python
import time
from agent_service.infrastructure.observability.metrics import (
    AGENT_INVOCATIONS,
    AGENT_EXECUTION_DURATION_SECONDS,
)

start = time.perf_counter()
try:
    result = await agent.execute(task)
    AGENT_INVOCATIONS.labels(agent_name="code_analyzer", status="success").inc()
except Exception as e:
    AGENT_INVOCATIONS.labels(agent_name="code_analyzer", status="error").inc()
    raise
finally:
    duration = time.perf_counter() - start
    AGENT_EXECUTION_DURATION_SECONDS.labels(agent_name="code_analyzer").observe(duration)
```

#### `agent_tokens_used_total`
Counter for total tokens used by agents.

**Labels:**
- `agent_name`: Name of the agent
- `token_type`: "input" or "output"

**Usage:**
```python
from agent_service.infrastructure.observability.metrics import AGENT_TOKENS_USED_TOTAL

# After agent execution
AGENT_TOKENS_USED_TOTAL.labels(
    agent_name="code_analyzer",
    token_type="input"
).inc(response.usage.input_tokens)

AGENT_TOKENS_USED_TOTAL.labels(
    agent_name="code_analyzer",
    token_type="output"
).inc(response.usage.output_tokens)
```

### Tool Metrics

#### `tool_executions_total`
Counter for total tool executions (already exists).

**Labels:**
- `tool_name`: Name of the tool
- `status`: "success" or "error"

#### `tool_execution_duration_seconds`
Histogram for tool execution duration.

**Labels:**
- `tool_name`: Name of the tool

**Usage:**
```python
import time
from agent_service.infrastructure.observability.metrics import (
    TOOL_EXECUTIONS,
    TOOL_EXECUTION_DURATION_SECONDS,
)

start = time.perf_counter()
try:
    result = await tool.execute(input_data)
    TOOL_EXECUTIONS.labels(tool_name="code_search", status="success").inc()
except Exception as e:
    TOOL_EXECUTIONS.labels(tool_name="code_search", status="error").inc()
    raise
finally:
    duration = time.perf_counter() - start
    TOOL_EXECUTION_DURATION_SECONDS.labels(tool_name="code_search").observe(duration)
```

### Business Metrics

#### `users_total` (Gauge)
Total number of users in the system.

**Auto-collected by:** `MetricsCollector` in `metrics_collectors.py`

#### `api_keys_active` (Gauge)
Number of active API keys.

**Auto-collected by:** `MetricsCollector` in `metrics_collectors.py`

#### `sessions_active` (Gauge)
Number of active user sessions.

**Auto-collected by:** `MetricsCollector` in `metrics_collectors.py`

## Setting Up Metrics Collection

### 1. Start the Metrics Collector

Add to your application startup in `api/app.py`:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from agent_service.infrastructure.observability.metrics_collectors import (
    metrics_collector_lifespan
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start metrics collector (collects every 30 seconds)
    async with metrics_collector_lifespan(collection_interval=30):
        # Your other startup code
        yield
        # Your shutdown code

app = FastAPI(lifespan=lifespan)
```

Or manually:

```python
from agent_service.infrastructure.observability.metrics_collectors import (
    start_metrics_collector,
    stop_metrics_collector
)

@app.on_event("startup")
async def startup():
    await start_metrics_collector(collection_interval=30)

@app.on_event("shutdown")
async def shutdown():
    await stop_metrics_collector()
```

### 2. Add Metrics Middleware

The `MetricsMiddleware` is already available. To use it, add to your app:

```python
from agent_service.api.middleware.metrics import MetricsMiddleware

app.add_middleware(MetricsMiddleware)
```

This middleware:
- Tracks request count and latency
- Extracts authentication information (user_id, api_key_id, auth_type)
- Hashes IDs for cardinality control

### 3. Store User Info in Request State

For the middleware to extract auth info, store the UserInfo in request state:

```python
from fastapi import Request, Depends
from agent_service.auth.dependencies import get_current_user
from agent_service.auth.schemas import UserInfo

async def store_user_in_state(
    request: Request,
    user: UserInfo = Depends(get_current_user)
):
    request.state.user = user
    return user

# Use in routes
@router.get("/protected")
async def protected_route(user: UserInfo = Depends(store_user_in_state)):
    return {"user_id": user.id}
```

## Accessing Metrics

### Prometheus Endpoint

Metrics are exposed at `/metrics`:

```bash
curl http://localhost:8000/metrics
```

### Grafana Dashboard Queries

Example PromQL queries for Grafana:

**Request Rate by Status:**
```promql
sum(rate(agent_requests_total[5m])) by (status)
```

**P95 Request Latency:**
```promql
histogram_quantile(0.95, sum(rate(agent_request_latency_seconds_bucket[5m])) by (le, endpoint))
```

**Agent Success Rate:**
```promql
sum(rate(agent_invocations_total{status="success"}[5m])) / sum(rate(agent_invocations_total[5m]))
```

**Database Pool Utilization:**
```promql
db_pool_checked_out / db_pool_size
```

**Redis Connection Usage:**
```promql
redis_connections_active
```

**Authentication Failure Rate:**
```promql
sum(rate(auth_failed_attempts_total[5m])) by (reason)
```

**Token Usage by Agent:**
```promql
sum(rate(agent_tokens_used_total[5m])) by (agent_name, token_type)
```

## Best Practices

### 1. Label Cardinality

Keep label cardinality low to avoid performance issues:

- **Good:** `agent_name="code_analyzer"` (low cardinality)
- **Bad:** `user_email="user@example.com"` (high cardinality)

The middleware automatically hashes user IDs and API key IDs to control cardinality.

### 2. Histogram Buckets

Choose appropriate buckets for your use case:

```python
# Database queries (milliseconds)
buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0]

# Agent execution (seconds)
buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0]
```

### 3. Error Tracking

Always track both success and error cases:

```python
try:
    result = await operation()
    METRIC.labels(status="success").inc()
except Exception:
    METRIC.labels(status="error").inc()
    raise
```

### 4. Use Context Managers

Create reusable context managers for common patterns:

```python
@contextmanager
def track_execution(metric: Histogram, **labels):
    start = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start
        metric.labels(**labels).observe(duration)
```

## Troubleshooting

### Metrics Not Appearing

1. Check that the metrics collector is started
2. Verify database tables exist (users, api_keys, sessions)
3. Check logs for collection errors
4. Ensure `/metrics` endpoint is accessible

### High Cardinality Warning

If Prometheus shows cardinality warnings:

1. Check label usage - avoid unique identifiers
2. Use hashing for user/API key IDs (already done in middleware)
3. Limit the number of distinct values per label

### Metrics Not Updating

1. Verify the collection interval is appropriate
2. Check for errors in the metrics collector logs
3. Ensure database connection is healthy
4. Verify Redis connection for Redis metrics
