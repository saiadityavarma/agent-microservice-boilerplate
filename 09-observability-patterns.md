# Task 09: Observability Patterns

## Objective
Establish logging, metrics, and tracing patterns. Claude Code follows these for consistent observability.

## Deliverables

### Structured Logging
```python
# src/agent_service/infrastructure/observability/logging.py
"""
Structured logging configuration.

Claude Code: Use `logger` from this module, not print() or logging.getLogger().
"""
import structlog
from agent_service.config.settings import get_settings


def configure_logging() -> None:
    """Configure structured logging."""
    settings = get_settings()
    
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            # JSON in production, pretty print in dev
            structlog.processors.JSONRenderer() 
            if settings.is_production 
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(settings.log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """
    Get a logger instance.
    
    Usage:
        logger = get_logger(__name__)
        logger.info("something happened", key="value")
    """
    return structlog.get_logger(name)


# Convenience export
logger = get_logger()
```

### Logging Usage Patterns
```python
# Pattern: Contextual logging in request handlers

from agent_service.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

async def my_handler(request_id: str, user_id: str):
    # Bind context for all subsequent logs
    log = logger.bind(request_id=request_id, user_id=user_id)
    
    log.info("handler_started")
    
    try:
        result = await do_something()
        log.info("handler_completed", result_size=len(result))
        return result
    except Exception as e:
        log.error("handler_failed", error=str(e))
        raise
```

### Metrics
```python
# src/agent_service/infrastructure/observability/metrics.py
"""
Prometheus metrics.

Claude Code: Add new metrics following this pattern.
"""
from prometheus_client import Counter, Histogram, Gauge, REGISTRY


# Request metrics
REQUEST_COUNT = Counter(
    "agent_requests_total",
    "Total requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "agent_request_latency_seconds",
    "Request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
)

# Agent metrics
AGENT_INVOCATIONS = Counter(
    "agent_invocations_total",
    "Total agent invocations",
    ["agent_name", "status"],
)

AGENT_LATENCY = Histogram(
    "agent_latency_seconds",
    "Agent invocation latency",
    ["agent_name"],
)

# Tool metrics
TOOL_EXECUTIONS = Counter(
    "tool_executions_total",
    "Total tool executions",
    ["tool_name", "status"],
)

# Active connections
ACTIVE_STREAMS = Gauge(
    "active_streams",
    "Number of active streaming connections",
)


# ──────────────────────────────────────────────
# Claude Code: Add new metrics here
# ──────────────────────────────────────────────
```

### Metrics Middleware
```python
# src/agent_service/api/middleware/metrics.py
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from agent_service.infrastructure.observability.metrics import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record request metrics."""
    
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        
        response = await call_next(request)
        
        duration = time.perf_counter() - start
        
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
        ).inc()
        
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(duration)
        
        return response
```

### Metrics Endpoint
```python
# src/agent_service/api/routes/health.py
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

router = APIRouter()


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus metrics endpoint."""
    return PlainTextResponse(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
```

### Tracing (Optional)
```python
# src/agent_service/infrastructure/observability/tracing.py
"""
OpenTelemetry tracing setup (optional).

Install: uv add opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi
"""
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from agent_service.config.settings import get_settings


def configure_tracing(app) -> None:
    """Configure OpenTelemetry tracing."""
    settings = get_settings()
    
    if not settings.otel_exporter_endpoint:
        return  # Tracing not configured
    
    # Set up tracer provider
    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    
    # Add exporter (configure based on your backend)
    # processor = BatchSpanProcessor(OTLPSpanExporter())
    # provider.add_span_processor(processor)
    
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)


def get_tracer(name: str):
    """Get a tracer for manual instrumentation."""
    return trace.get_tracer(name)
```

## Pattern for Claude Code

When adding observability:
```python
# 1. Logging - always use structured logger
from agent_service.infrastructure.observability.logging import get_logger
logger = get_logger(__name__)
logger.info("event_name", key1="value1", key2=123)

# 2. Metrics - add to metrics.py, use in code
MY_COUNTER = Counter("my_counter", "Description", ["label1"])
MY_COUNTER.labels(label1="value").inc()

# 3. Tracing - use for distributed systems
tracer = get_tracer(__name__)
with tracer.start_as_current_span("operation_name"):
    # do work
```

## Acceptance Criteria
- [ ] Structured logging configured
- [ ] Prometheus metrics exposed at /metrics
- [ ] Request metrics recorded via middleware
- [ ] Logger usable from any module
- [ ] Patterns documented for Claude Code
