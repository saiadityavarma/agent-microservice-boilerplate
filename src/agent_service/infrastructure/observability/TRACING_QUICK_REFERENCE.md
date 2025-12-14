# OpenTelemetry Tracing - Quick Reference

A quick reference guide for using distributed tracing in the Agent Service.

## Configuration

```bash
# .env file
TRACING_ENABLED=true
TRACING_EXPORTER=console  # Options: otlp, jaeger, console, none
TRACING_ENDPOINT=http://localhost:4317
TRACING_SAMPLE_RATE=1.0   # 0.0 to 1.0
```

## Import Statements

```python
# Decorators
from agent_service.infrastructure.observability import (
    traced,
    traced_async,
    trace_agent_invocation,
    trace_tool_execution,
)

# Manual instrumentation
from agent_service.infrastructure.observability import (
    get_tracer,
    add_span_attributes,
    add_span_event,
    set_span_error,
)

# Instrumentation helpers
from agent_service.infrastructure.observability import (
    instrument_fastapi,
    instrument_database,
    instrument_redis,
    instrument_http_client,
)
```

## Common Patterns

### 1. Trace a Synchronous Function

```python
@traced(name="process_data")
def process_data(data: dict) -> dict:
    return processed_data
```

### 2. Trace an Async Function

```python
@traced_async(name="fetch_user")
async def fetch_user(user_id: str) -> dict:
    return user_data
```

### 3. Record Function Arguments (Exclude Sensitive Data)

```python
@traced_async(
    name="authenticate",
    record_args=True,
    exclude_args=["password", "token", "api_key"]
)
async def authenticate(username: str, password: str):
    return auth_result
```

### 4. Add Custom Attributes

```python
@traced_async(
    name="payment.process",
    attributes={
        "payment.processor": "stripe",
        "payment.currency": "USD"
    }
)
async def process_payment(amount: float):
    return payment_result
```

### 5. Trace Agent Invocation

```python
@trace_agent_invocation(
    agent_name="assistant",
    attributes={"model": "gpt-4", "temperature": 0.7}
)
async def invoke(self, input: AgentInput) -> AgentOutput:
    result = await self.llm.generate(input.message)
    return AgentOutput(
        content=result,
        metadata={
            "token_count": 150,  # Auto-captured
            "model": "gpt-4"     # Auto-captured
        }
    )
```

### 6. Trace Tool Execution

```python
@trace_tool_execution(
    tool_name="web_search",
    attributes={"provider": "google"}
)
async def search_web(query: str) -> list:
    return search_results
```

### 7. Manual Span Creation

```python
from opentelemetry import trace

tracer = get_tracer(__name__)

with tracer.start_as_current_span("operation_name") as span:
    # Add attributes
    span.set_attribute("key", "value")

    # Your code here
    result = await do_work()

    # Add events
    add_span_event(span, "milestone_reached")

    return result
```

### 8. Streaming with Events

```python
async def stream(self, input: AgentInput):
    tracer = get_tracer(__name__)

    with tracer.start_as_current_span("agent.stream") as span:
        span.set_attribute("agent.name", self.name)

        chunk_count = 0
        async for chunk in self.llm.stream(input.message):
            chunk_count += 1

            add_span_event(span, "chunk_generated", {
                "chunk.index": chunk_count
            })

            yield chunk

        span.set_attribute("chunk_count", chunk_count)
```

### 9. Error Handling

```python
tracer = get_tracer(__name__)

with tracer.start_as_current_span("risky_operation") as span:
    try:
        result = await risky_function()
        return result
    except Exception as e:
        set_span_error(span, e)
        raise
```

### 10. Nested Spans

```python
tracer = get_tracer(__name__)

with tracer.start_as_current_span("parent_operation") as parent:
    parent.set_attribute("operation.type", "complex")

    # Child span 1
    with tracer.start_as_current_span("step_1") as child1:
        await step_1()

    # Child span 2
    with tracer.start_as_current_span("step_2") as child2:
        await step_2()

    parent.set_attribute("steps_completed", 2)
```

## Automatic Instrumentation

Already enabled automatically:

- **FastAPI**: All HTTP endpoints
- **httpx**: All outbound HTTP requests

### Enable Database Tracing

```python
from agent_service.infrastructure.observability import instrument_database

engine = create_async_engine(database_url)
instrument_database(engine)
```

### Enable Redis Tracing

```python
from agent_service.infrastructure.observability import instrument_redis

redis_client = Redis(host='localhost', port=6379)
instrument_redis(redis_client)
```

## Span Attributes Best Practices

### Good Attribute Names (Low Cardinality)

```python
span.set_attribute("agent.name", "assistant")
span.set_attribute("agent.model", "gpt-4")
span.set_attribute("http.method", "POST")
span.set_attribute("http.status_code", 200)
```

### Avoid High Cardinality

```python
# Bad - includes unique IDs
span.set_attribute("user.id", "12345")  # Too many unique values

# Good - use semantic categories
span.set_attribute("user.tier", "premium")
```

## Common Attribute Patterns

### Agent Attributes
```python
{
    "agent.name": "assistant",
    "agent.model": "gpt-4",
    "agent.input.length": 150,
    "agent.output.length": 200,
    "agent.token_count": 350,
    "agent.session_id": "session_123",
    "agent.temperature": 0.7
}
```

### HTTP Attributes
```python
{
    "http.method": "POST",
    "http.status_code": 200,
    "http.url": "/api/v1/agents/invoke",
    "http.duration_ms": 1234
}
```

### Database Attributes
```python
{
    "db.system": "postgresql",
    "db.operation": "select",
    "db.table": "users",
    "db.duration_ms": 45
}
```

### Tool Attributes
```python
{
    "tool.name": "web_search",
    "tool.category": "search",
    "tool.provider": "google",
    "tool.query": "python tutorials",
    "tool.results_count": 10
}
```

## Span Events

Use events for point-in-time occurrences:

```python
# Simple event
add_span_event(span, "validation_started")

# Event with attributes
add_span_event(span, "chunk_received", {
    "chunk.index": 1,
    "chunk.size": 256
})

# Common event patterns
add_span_event(span, "cache_hit")
add_span_event(span, "cache_miss")
add_span_event(span, "retry_attempt", {"attempt": 2})
add_span_event(span, "request_queued")
add_span_event(span, "processing_started")
add_span_event(span, "processing_completed")
```

## Sampling

### Development (Trace Everything)
```bash
TRACING_SAMPLE_RATE=1.0
```

### Production (Sample 10%)
```bash
TRACING_SAMPLE_RATE=0.1
```

### High-Traffic (Sample 1%)
```bash
TRACING_SAMPLE_RATE=0.01
```

## Running with Jaeger

### Start Jaeger

```bash
docker run -d --name jaeger \
  -e COLLECTOR_OTLP_ENABLED=true \
  -p 16686:16686 \
  -p 4317:4317 \
  jaegertracing/all-in-one:latest
```

### Configure App

```bash
TRACING_ENABLED=true
TRACING_EXPORTER=otlp
TRACING_ENDPOINT=http://localhost:4317
```

### Access Jaeger UI

Open: http://localhost:16686

## Troubleshooting

### No Traces Appearing

1. Check tracing is enabled: `TRACING_ENABLED=true`
2. Verify exporter: `TRACING_EXPORTER=console` for dev
3. Check logs for "Tracing initialized" message
4. Make sure collector is running (for OTLP/Jaeger)

### Console Output Not Showing

- Console exporter prints to stdout
- Check your logging configuration
- Try with `TRACING_EXPORTER=console` explicitly

### High Memory Usage

- Reduce sampling: `TRACING_SAMPLE_RATE=0.1`
- Check for high-cardinality attributes
- Verify spans are being flushed (shutdown_tracing called)

## Performance Tips

1. **Use appropriate sampling** in production (0.01 - 0.1)
2. **Avoid high-cardinality attributes** (no unique IDs in attribute keys)
3. **Don't trace hot loops** - use decorators selectively
4. **Use async batch processing** (already enabled by default)
5. **Exclude sensitive data** from span attributes

## Security

### Never Record Sensitive Data

```python
@traced_async(
    record_args=True,
    exclude_args=[
        "password",
        "token",
        "api_key",
        "secret",
        "credit_card",
        "ssn"
    ]
)
async def process_sensitive_data(username: str, password: str):
    pass
```

### Sanitize User Input

```python
# Don't include raw user input in attributes
span.set_attribute("query", user_query)  # Bad

# Use length or category instead
span.set_attribute("query.length", len(user_query))  # Good
span.set_attribute("query.type", "search")  # Good
```

## Dependencies

```bash
uv add opentelemetry-api \
       opentelemetry-sdk \
       opentelemetry-instrumentation-fastapi \
       opentelemetry-exporter-otlp \
       opentelemetry-exporter-jaeger \
       opentelemetry-instrumentation-sqlalchemy \
       opentelemetry-instrumentation-redis \
       opentelemetry-instrumentation-httpx
```

## Further Reading

- **Comprehensive Guide**: `TRACING_GUIDE.md`
- **Examples**: `tracing_examples.py`
- **Implementation Summary**: `../../TRACING_IMPLEMENTATION_SUMMARY.md`
