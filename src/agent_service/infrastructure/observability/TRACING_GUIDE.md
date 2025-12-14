# OpenTelemetry Distributed Tracing Guide

This guide explains how to use the OpenTelemetry distributed tracing implementation in the Agent Service.

## Table of Contents

1. [Overview](#overview)
2. [Configuration](#configuration)
3. [Automatic Instrumentation](#automatic-instrumentation)
4. [Custom Instrumentation](#custom-instrumentation)
5. [Agent Tracing](#agent-tracing)
6. [Tool Tracing](#tool-tracing)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Overview

The agent service includes comprehensive OpenTelemetry distributed tracing support with:

- **Multiple Exporters**: OTLP, Jaeger, Console (dev), or None
- **W3C TraceContext Propagation**: Standard trace context across services
- **Automatic Instrumentation**: FastAPI, SQLAlchemy, Redis, httpx
- **Custom Decorators**: Easy tracing for custom functions
- **Agent-Specific Tracing**: Specialized decorators for AI agents
- **Configurable Sampling**: Control trace volume in production

## Configuration

Add the following environment variables to your `.env` file:

```bash
# Enable/disable tracing
TRACING_ENABLED=true

# Exporter type: otlp, jaeger, console, none
TRACING_EXPORTER=console

# OTLP endpoint (for otlp or jaeger exporters)
TRACING_ENDPOINT=http://localhost:4317

# Sample rate: 1.0 = trace everything, 0.1 = trace 10%
TRACING_SAMPLE_RATE=1.0
```

### Exporter Options

#### Console (Development)
Best for local development - prints traces to stdout:
```bash
TRACING_EXPORTER=console
```

#### OTLP (Production)
Works with Jaeger, Tempo, and other OTLP-compatible backends:
```bash
TRACING_EXPORTER=otlp
TRACING_ENDPOINT=http://localhost:4317
```

#### Jaeger (Legacy)
For legacy Jaeger deployments:
```bash
TRACING_EXPORTER=jaeger
TRACING_ENDPOINT=localhost:6831
```

#### None (Disabled)
Disable tracing completely:
```bash
TRACING_ENABLED=false
# OR
TRACING_EXPORTER=none
```

## Automatic Instrumentation

The following components are automatically instrumented when the application starts:

### FastAPI
All HTTP endpoints are automatically traced with:
- Request method, path, status code
- Request/response duration
- Client IP and user agent
- Exception tracking

No code changes required - this is set up in `api/app.py`.

### HTTP Client (httpx)
All outbound HTTP requests are traced with:
- Request URL, method, headers
- Response status code
- Request duration
- Trace context propagation to downstream services

### Database (SQLAlchemy)
To enable database tracing, add this to your database connection setup:

```python
from agent_service.infrastructure.observability.tracing_instrumentation import instrument_database

# After creating your engine
engine = create_async_engine(database_url)
instrument_database(engine)
```

### Redis
To enable Redis tracing, add this to your Redis connection setup:

```python
from agent_service.infrastructure.observability.tracing_instrumentation import instrument_redis

# After creating your Redis client
redis_client = Redis(host='localhost', port=6379)
instrument_redis(redis_client)
```

## Custom Instrumentation

### Using Decorators

#### Synchronous Functions

```python
from agent_service.infrastructure.observability.decorators import traced

@traced(name="process_user_input")
def process_input(user_id: str, message: str):
    # Your code here
    return processed_message
```

#### Asynchronous Functions

```python
from agent_service.infrastructure.observability.decorators import traced_async

@traced_async(name="call_external_api")
async def call_api(endpoint: str, data: dict):
    # Your async code here
    return response
```

#### Recording Function Arguments

```python
@traced_async(
    name="authenticate_user",
    record_args=True,
    exclude_args=["password", "token"]  # Don't record sensitive data
)
async def authenticate(username: str, password: str):
    # Function arguments are recorded as span attributes
    # except 'password' which is excluded
    return user
```

#### Adding Custom Attributes

```python
@traced_async(
    name="process_payment",
    attributes={
        "component": "payment",
        "payment.processor": "stripe"
    }
)
async def process_payment(amount: float):
    # Custom attributes are added to the span
    return payment_result
```

### Manual Instrumentation

For more control, use the tracer directly:

```python
from agent_service.infrastructure.observability.tracing import get_tracer
from agent_service.infrastructure.observability.tracing_instrumentation import (
    add_span_attributes,
    add_span_event,
    set_span_error
)

tracer = get_tracer(__name__)

async def complex_operation(data: dict):
    with tracer.start_as_current_span("complex_operation") as span:
        # Add attributes
        add_span_attributes(span, {
            "operation.type": "data_processing",
            "data.size": len(data)
        })

        # Add events
        add_span_event(span, "validation_started")

        try:
            # Your code here
            result = await process(data)

            add_span_event(span, "processing_completed", {
                "result.size": len(result)
            })

            return result

        except Exception as e:
            # Record the error
            set_span_error(span, e)
            raise
```

## Agent Tracing

Use the specialized `@trace_agent_invocation` decorator for agent methods:

```python
from agent_service.infrastructure.observability.decorators import trace_agent_invocation

class MyAgent(IAgent):
    @trace_agent_invocation(
        agent_name="my_agent",
        attributes={
            "agent.model": "gpt-4",
            "agent.temperature": 0.7
        }
    )
    async def invoke(self, input: AgentInput) -> AgentOutput:
        # Agent logic here
        result = await self.llm.generate(input.message)

        return AgentOutput(
            content=result,
            metadata={
                "token_count": 150,  # Automatically recorded
                "model": "gpt-4"     # Automatically recorded
            }
        )
```

The decorator automatically records:
- Agent name and attributes
- Input/output lengths
- Session ID and user ID (if present)
- Token counts and model info (from metadata)
- Execution duration
- Exceptions

### Streaming Operations

For streaming agents, use manual instrumentation:

```python
from agent_service.infrastructure.observability.tracing import get_tracer
from agent_service.infrastructure.observability.tracing_instrumentation import add_span_event

async def stream(self, input: AgentInput) -> AsyncGenerator[StreamChunk, None]:
    tracer = get_tracer(__name__)

    with tracer.start_as_current_span("agent.stream.my_agent") as span:
        span.set_attribute("agent.name", self.name)
        span.set_attribute("agent.input.length", len(input.message))

        chunk_count = 0
        async for chunk in self.llm.stream(input.message):
            chunk_count += 1

            # Record each chunk as an event
            add_span_event(span, "chunk_generated", {
                "chunk.index": chunk_count
            })

            yield StreamChunk(type="text", content=chunk)

        span.set_attribute("agent.chunk_count", chunk_count)
```

## Tool Tracing

Use the `@trace_tool_execution` decorator for agent tools:

```python
from agent_service.infrastructure.observability.decorators import trace_tool_execution

@trace_tool_execution(
    tool_name="web_search",
    attributes={"tool.category": "search"}
)
async def search_web(query: str) -> dict:
    # Tool logic here
    results = await search_api.search(query)
    return results
```

## Best Practices

### 1. Span Naming

Use hierarchical, low-cardinality names:

```python
# Good - low cardinality
"agent.invoke.assistant"
"database.query.users"
"tool.execute.search"

# Bad - high cardinality (includes unique IDs)
"agent.invoke.session_12345"
"database.query.user_abc123"
```

### 2. Attributes vs Events

Use **attributes** for:
- Metadata about the entire operation
- Filterable/searchable values
- Resource identifiers

Use **events** for:
- Points in time during the operation
- Streaming chunks
- Intermediate results

### 3. Sensitive Data

Never record sensitive data in spans:

```python
@traced_async(
    record_args=True,
    exclude_args=["password", "token", "api_key", "secret"]
)
async def authenticate(username: str, password: str):
    pass
```

### 4. Sampling in Production

Use sampling to reduce trace volume in production:

```bash
# Trace 10% of requests
TRACING_SAMPLE_RATE=0.1
```

### 5. Structured Attributes

Use consistent attribute naming:

```python
# Good - follows semantic conventions
{
    "agent.name": "assistant",
    "agent.model": "gpt-4",
    "agent.input.length": 150,
    "agent.output.length": 200
}

# Avoid - inconsistent naming
{
    "agentName": "assistant",
    "llm_model": "gpt-4",
    "inputLen": 150
}
```

## Troubleshooting

### Traces Not Appearing

1. **Check if tracing is enabled:**
   ```bash
   TRACING_ENABLED=true
   ```

2. **Verify exporter configuration:**
   ```bash
   # For console output (dev)
   TRACING_EXPORTER=console

   # For OTLP (production)
   TRACING_EXPORTER=otlp
   TRACING_ENDPOINT=http://your-collector:4317
   ```

3. **Check application logs:**
   Look for "Tracing initialized" message on startup.

### Console Exporter Not Showing Output

The console exporter prints to stdout. If using structured logging, traces appear as JSON.

### OTLP Connection Refused

1. Verify the collector is running:
   ```bash
   curl http://localhost:4317
   ```

2. Check endpoint configuration:
   ```bash
   TRACING_ENDPOINT=http://localhost:4317
   ```

3. Check firewall/network settings

### High Cardinality Warning

If you see warnings about high cardinality:
- Remove unique IDs from span names
- Move unique values to attributes instead
- Use structured attribute naming

### Performance Impact

If tracing impacts performance:
1. Reduce sampling rate:
   ```bash
   TRACING_SAMPLE_RATE=0.1  # 10%
   ```

2. Disable tracing for specific operations:
   ```python
   # Don't use @traced decorator on hot paths
   ```

3. Use async batch processing (already enabled by default)

## Running with Jaeger (Local Development)

1. **Start Jaeger (all-in-one):**
   ```bash
   docker run -d --name jaeger \
     -e COLLECTOR_OTLP_ENABLED=true \
     -p 16686:16686 \
     -p 4317:4317 \
     jaegertracing/all-in-one:latest
   ```

2. **Configure the agent service:**
   ```bash
   TRACING_ENABLED=true
   TRACING_EXPORTER=otlp
   TRACING_ENDPOINT=http://localhost:4317
   ```

3. **Access Jaeger UI:**
   Open http://localhost:16686

4. **Make requests to your agent service:**
   ```bash
   curl http://localhost:8000/api/v1/agents/invoke
   ```

5. **View traces in Jaeger UI**

## Dependencies

Install the required OpenTelemetry packages:

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
