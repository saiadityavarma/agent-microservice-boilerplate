# Prometheus Metrics - Quick Reference

Quick reference for using enhanced Prometheus metrics in the agent service.

## Import Metrics

```python
from agent_service.infrastructure.observability.metrics import (
    # Auth
    AUTH_LOGIN_TOTAL,
    AUTH_TOKEN_REFRESH_TOTAL,
    AUTH_FAILED_ATTEMPTS_TOTAL,

    # Database
    DB_POOL_SIZE,
    DB_POOL_CHECKED_OUT,
    DB_QUERY_DURATION_SECONDS,

    # Redis
    REDIS_CONNECTIONS_ACTIVE,
    REDIS_OPERATIONS_TOTAL,

    # Agent
    AGENT_INVOCATIONS,
    AGENT_EXECUTION_DURATION_SECONDS,
    AGENT_TOKENS_USED_TOTAL,

    # Tool
    TOOL_EXECUTIONS,
    TOOL_EXECUTION_DURATION_SECONDS,

    # Business
    USERS_TOTAL,
    API_KEYS_ACTIVE,
    SESSIONS_ACTIVE,
)
```

## Common Patterns

### Track Agent Execution

```python
import time

start = time.perf_counter()
try:
    result = await agent.execute(task)
    AGENT_INVOCATIONS.labels(agent_name="my_agent", status="success").inc()

    # Track tokens
    AGENT_TOKENS_USED_TOTAL.labels(agent_name="my_agent", token_type="input").inc(100)
    AGENT_TOKENS_USED_TOTAL.labels(agent_name="my_agent", token_type="output").inc(50)

except Exception:
    AGENT_INVOCATIONS.labels(agent_name="my_agent", status="error").inc()
    raise
finally:
    duration = time.perf_counter() - start
    AGENT_EXECUTION_DURATION_SECONDS.labels(agent_name="my_agent").observe(duration)
```

### Track Database Query

```python
start = time.perf_counter()
result = await session.execute(query)
duration = time.perf_counter() - start
DB_QUERY_DURATION_SECONDS.labels(query_type="select").observe(duration)
```

### Track Redis Operation

```python
await redis.set("key", "value")
REDIS_OPERATIONS_TOTAL.labels(operation="set").inc()

value = await redis.get("key")
REDIS_OPERATIONS_TOTAL.labels(operation="get").inc()
```

### Track Authentication

```python
# Successful login
AUTH_LOGIN_TOTAL.labels(provider="azure_ad", success="true").inc()

# Failed login
AUTH_LOGIN_TOTAL.labels(provider="azure_ad", success="false").inc()
AUTH_FAILED_ATTEMPTS_TOTAL.labels(reason="invalid_credentials").inc()
```

### Track Tool Execution

```python
start = time.perf_counter()
try:
    result = await tool.execute()
    TOOL_EXECUTIONS.labels(tool_name="code_search", status="success").inc()
except Exception:
    TOOL_EXECUTIONS.labels(tool_name="code_search", status="error").inc()
    raise
finally:
    duration = time.perf_counter() - start
    TOOL_EXECUTION_DURATION_SECONDS.labels(tool_name="code_search").observe(duration)
```

## Helper Context Manager

```python
from contextlib import contextmanager
import time

@contextmanager
def track_operation(metric_histogram, metric_counter, operation_name: str):
    """Generic operation tracker."""
    start = time.perf_counter()
    success = False
    try:
        yield
        success = True
    finally:
        duration = time.perf_counter() - start
        metric_histogram.labels(name=operation_name).observe(duration)
        metric_counter.labels(name=operation_name, status="success" if success else "error").inc()

# Usage
with track_operation(AGENT_EXECUTION_DURATION_SECONDS, AGENT_INVOCATIONS, "my_agent"):
    await agent.execute(task)
```

## Metric Types Quick Guide

### Counter
Monotonically increasing value.

```python
COUNTER.labels(label1="value1").inc()      # Increment by 1
COUNTER.labels(label1="value1").inc(5)     # Increment by 5
```

### Gauge
Value that can go up or down.

```python
GAUGE.set(42)          # Set to specific value
GAUGE.inc()            # Increment by 1
GAUGE.dec()            # Decrement by 1
GAUGE.inc(5)           # Increment by 5
GAUGE.set_to_current_time()  # Set to current Unix timestamp
```

### Histogram
Observations of values (automatically creates buckets).

```python
HISTOGRAM.labels(label1="value1").observe(0.5)   # Observe a value
```

## Common PromQL Queries

### Request Rate
```promql
rate(agent_requests_total[5m])
```

### Error Rate
```promql
sum(rate(agent_requests_total{status=~"5.."}[5m])) / sum(rate(agent_requests_total[5m]))
```

### P95 Latency
```promql
histogram_quantile(0.95, sum(rate(agent_request_latency_seconds_bucket[5m])) by (le))
```

### Database Pool Utilization
```promql
db_pool_checked_out / db_pool_size
```

### Agent Success Rate
```promql
sum(rate(agent_invocations_total{status="success"}[5m])) / sum(rate(agent_invocations_total[5m]))
```

### Token Usage Rate
```promql
sum(rate(agent_tokens_used_total[5m])) by (agent_name, token_type)
```

## Label Best Practices

**DO:**
- Use descriptive label names
- Keep cardinality low (< 1000 unique values)
- Hash high-cardinality values (user IDs)
- Use consistent label values

**DON'T:**
- Use user emails as labels
- Use timestamps as labels
- Use unique IDs without hashing
- Create unbounded label values

## Quick Setup Checklist

- [ ] Import metrics from `infrastructure/observability/metrics.py`
- [ ] Add metrics collector to app startup
- [ ] Add MetricsMiddleware to app
- [ ] Instrument code with metrics
- [ ] Test at `/metrics` endpoint
- [ ] Configure Prometheus scraping
- [ ] Create Grafana dashboards
- [ ] Set up alerts

## Debugging

### Check if metric exists
```bash
curl http://localhost:8000/metrics | grep my_metric_name
```

### View all metrics
```bash
curl http://localhost:8000/metrics
```

### Check metric value
```bash
curl http://localhost:8000/metrics | grep -A 2 "my_metric_name"
```

### Common Issues

**Metric not appearing:**
- Check spelling
- Verify metric is imported
- Ensure .inc()/.observe()/.set() is called
- Check middleware is added

**Wrong values:**
- Verify labels are correct
- Check if counter vs gauge
- Ensure timing code is correct

**High cardinality warning:**
- Review label values
- Hash unique identifiers
- Limit distinct label values
