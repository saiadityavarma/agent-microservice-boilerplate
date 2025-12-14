# Migration Guide - Enhanced Prometheus Metrics

Step-by-step guide to integrate the enhanced metrics into your existing application.

## Prerequisites

- FastAPI application already running
- Prometheus client library installed (`prometheus-client`)
- Existing `/metrics` endpoint (already present in `/api/routes/health.py`)

## Migration Steps

### Step 1: Update Application Startup

Choose one of the following approaches:

#### Option A: Using Lifespan Context Manager (Recommended)

Update `/src/agent_service/api/app.py`:

```python
from contextlib import asynccontextmanager
from agent_service.infrastructure.observability.metrics_collectors import (
    metrics_collector_lifespan
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    settings = get_settings()

    # Initialize Redis
    redis_manager = await get_redis_manager()
    # ... existing Redis initialization ...

    # ADD THIS: Start metrics collector
    async with metrics_collector_lifespan(collection_interval=30):
        yield  # Application is running

    # Shutdown
    await close_redis()

# Update create_app() to use the lifespan
def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.debug else None,
        lifespan=lifespan,  # ADD THIS LINE
    )
    # ... rest of your app configuration ...
```

#### Option B: Using Event Handlers (If not using lifespan)

Update `/src/agent_service/api/app.py`:

```python
from agent_service.infrastructure.observability.metrics_collectors import (
    start_metrics_collector,
    stop_metrics_collector
)

def create_app() -> FastAPI:
    # ... existing app creation ...

    @app.on_event("startup")
    async def startup():
        # ... existing startup code ...

        # ADD THIS: Start metrics collector
        await start_metrics_collector(collection_interval=30)

    @app.on_event("shutdown")
    async def shutdown():
        # ... existing shutdown code ...

        # ADD THIS: Stop metrics collector
        await stop_metrics_collector()

    return app
```

### Step 2: Add Metrics Middleware (Optional)

If you want detailed request metrics with auth info, add the MetricsMiddleware:

Update `/src/agent_service/api/app.py`:

```python
from agent_service.api.middleware.metrics import MetricsMiddleware

def create_app() -> FastAPI:
    # ... existing code ...

    # ADD THIS: Metrics middleware
    # Add it early in the middleware stack
    app.add_middleware(MetricsMiddleware)

    # Existing middleware
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    # ... etc ...
```

### Step 3: Update Database Schema (If Needed)

The metrics collector queries these tables for business metrics:

```sql
-- Ensure these tables exist (or adjust queries in metrics_collectors.py)

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    -- other columns ...
);

-- API Keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY,
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP,
    -- other columns ...
);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY,
    expires_at TIMESTAMP,
    -- other columns ...
);
```

**Note:** If your schema is different, update the SQL queries in:
`/src/agent_service/infrastructure/observability/metrics_collectors.py`

### Step 4: Instrument Your Code

Add metrics to your existing code:

#### In Authentication Code

```python
from agent_service.infrastructure.observability.metrics import (
    AUTH_LOGIN_TOTAL,
    AUTH_TOKEN_REFRESH_TOTAL,
    AUTH_FAILED_ATTEMPTS_TOTAL,
)

# In your login endpoint
async def login(credentials):
    try:
        user = await authenticate(credentials)
        AUTH_LOGIN_TOTAL.labels(provider="azure_ad", success="true").inc()
        return user
    except InvalidCredentialsError:
        AUTH_LOGIN_TOTAL.labels(provider="azure_ad", success="false").inc()
        AUTH_FAILED_ATTEMPTS_TOTAL.labels(reason="invalid_credentials").inc()
        raise
    except TokenExpiredError:
        AUTH_FAILED_ATTEMPTS_TOTAL.labels(reason="expired_token").inc()
        raise
```

#### In Agent Execution Code

```python
from agent_service.infrastructure.observability.metrics import (
    AGENT_INVOCATIONS,
    AGENT_EXECUTION_DURATION_SECONDS,
    AGENT_TOKENS_USED_TOTAL,
)
import time

async def execute_agent(agent_name: str, task: str):
    start = time.perf_counter()

    try:
        result = await agent.execute(task)

        # Track success
        AGENT_INVOCATIONS.labels(agent_name=agent_name, status="success").inc()

        # Track token usage if available
        if hasattr(result, 'usage'):
            AGENT_TOKENS_USED_TOTAL.labels(
                agent_name=agent_name,
                token_type="input"
            ).inc(result.usage.input_tokens)

            AGENT_TOKENS_USED_TOTAL.labels(
                agent_name=agent_name,
                token_type="output"
            ).inc(result.usage.output_tokens)

        return result

    except Exception as e:
        # Track error
        AGENT_INVOCATIONS.labels(agent_name=agent_name, status="error").inc()
        raise

    finally:
        # Track duration
        duration = time.perf_counter() - start
        AGENT_EXECUTION_DURATION_SECONDS.labels(agent_name=agent_name).observe(duration)
```

#### In Database Code

```python
from agent_service.infrastructure.observability.metrics import DB_QUERY_DURATION_SECONDS
import time

async def query_database(query_type: str, query):
    start = time.perf_counter()

    try:
        result = await session.execute(query)
        return result
    finally:
        duration = time.perf_counter() - start
        DB_QUERY_DURATION_SECONDS.labels(query_type=query_type).observe(duration)
```

#### In Redis Code

```python
from agent_service.infrastructure.observability.metrics import REDIS_OPERATIONS_TOTAL

async def get_from_cache(key: str):
    redis = await get_redis()
    value = await redis.get(key)
    REDIS_OPERATIONS_TOTAL.labels(operation="get").inc()
    return value

async def set_in_cache(key: str, value: str):
    redis = await get_redis()
    await redis.set(key, value)
    REDIS_OPERATIONS_TOTAL.labels(operation="set").inc()
```

### Step 5: Verify Metrics

1. **Start your application:**
   ```bash
   uvicorn agent_service.main:app --reload
   ```

2. **Check metrics endpoint:**
   ```bash
   curl http://localhost:8000/metrics
   ```

3. **Verify new metrics appear:**
   ```bash
   curl http://localhost:8000/metrics | grep -E "auth_|db_|redis_|agent_|tool_|users_|api_keys_|sessions_"
   ```

4. **Check logs for metrics collector:**
   ```
   Look for: "Metrics collector started"
   ```

### Step 6: Configure Prometheus

Update your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'agent-service'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Step 7: Create Grafana Dashboards

Import the following panels:

1. **Request Rate:**
   ```promql
   sum(rate(agent_requests_total[5m])) by (endpoint)
   ```

2. **Agent Performance:**
   ```promql
   histogram_quantile(0.95, sum(rate(agent_execution_duration_seconds_bucket[5m])) by (le, agent_name))
   ```

3. **Database Pool:**
   ```promql
   db_pool_checked_out / db_pool_size
   ```

4. **Business Metrics:**
   ```promql
   users_total
   api_keys_active
   sessions_active
   ```

### Step 8: Set Up Alerts (Optional)

Example alert rules:

```yaml
groups:
  - name: agent_service
    rules:
      - alert: HighErrorRate
        expr: sum(rate(agent_requests_total{status=~"5.."}[5m])) / sum(rate(agent_requests_total[5m])) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"

      - alert: DatabasePoolExhaustion
        expr: db_pool_checked_out / db_pool_size > 0.9
        for: 2m
        annotations:
          summary: "Database pool nearly exhausted"

      - alert: AgentExecutionSlow
        expr: histogram_quantile(0.95, sum(rate(agent_execution_duration_seconds_bucket[5m])) by (le)) > 60
        for: 5m
        annotations:
          summary: "Agent execution is slow"
```

## Troubleshooting

### Issue: Metrics collector not starting

**Symptoms:** No gauge metrics appearing, no startup log

**Solution:**
1. Check lifespan/startup event is being called
2. Verify no exceptions in startup
3. Check logs for errors
4. Ensure asyncio event loop is running

### Issue: Business metrics showing 0

**Symptoms:** users_total, api_keys_active, sessions_active are all 0

**Solution:**
1. Check database tables exist
2. Verify database connection is working
3. Update SQL queries in `metrics_collectors.py` to match your schema
4. Check logs for database errors

### Issue: Redis metrics not working

**Symptoms:** redis_connections_active always 0

**Solution:**
1. Verify Redis is connected
2. Check Redis pool implementation matches expected interface
3. Review `collect_redis_metrics()` in `metrics_collectors.py`

### Issue: High cardinality warning

**Symptoms:** Prometheus complaining about too many metrics

**Solution:**
1. Check for unbounded label values
2. Ensure user IDs are hashed (middleware does this)
3. Limit distinct values in custom labels
4. Review label usage in instrumentation

## Rollback Plan

If you need to rollback:

1. **Remove metrics collector from startup:**
   ```python
   # Comment out or remove:
   # async with metrics_collector_lifespan(collection_interval=30):
   ```

2. **Remove metrics middleware:**
   ```python
   # Comment out or remove:
   # app.add_middleware(MetricsMiddleware)
   ```

3. **Remove metric instrumentation from code:**
   - Comment out or remove metric calls
   - Keep imports commented for easy re-enable

4. **The `/metrics` endpoint will still work** with basic metrics

## Testing Checklist

Before deploying to production:

- [ ] Metrics collector starts successfully
- [ ] All gauge metrics appear in /metrics
- [ ] Request metrics include proper labels
- [ ] Agent execution metrics are recorded
- [ ] Database query metrics are tracked
- [ ] Redis operation metrics are tracked
- [ ] Business metrics show correct values
- [ ] Prometheus successfully scrapes metrics
- [ ] Grafana dashboards display data
- [ ] No performance degradation
- [ ] No excessive database load
- [ ] Cardinality is within limits

## Performance Impact

Expected performance impact:

- **Middleware:** ~1-2ms per request
- **Metrics Collector:** One DB query per metric type every 30s
- **Memory:** ~100KB for metric storage
- **CPU:** Negligible (<1%)

## Support

For issues or questions:

1. Check the documentation:
   - `METRICS_USAGE.md` - Detailed usage guide
   - `INTEGRATION_EXAMPLE.py` - Complete examples
   - `METRICS_QUICK_REFERENCE.md` - Quick reference

2. Review logs for errors
3. Test metrics endpoint: `curl http://localhost:8000/metrics`
4. Verify Prometheus configuration

## Next Steps

After successful migration:

1. Monitor metrics for a few days
2. Create custom Grafana dashboards
3. Set up alerts for your SLOs
4. Fine-tune collection intervals if needed
5. Add custom metrics for your specific use cases
