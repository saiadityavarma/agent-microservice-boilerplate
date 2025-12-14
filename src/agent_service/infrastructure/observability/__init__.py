"""
Observability infrastructure for the agent service.

This package provides:
- Distributed tracing with OpenTelemetry
- Structured logging
- Metrics collection
- Audit logging
- Request context management
- Error tracking with Sentry
"""

from agent_service.infrastructure.observability.tracing import (
    init_tracing,
    get_tracer,
    shutdown_tracing,
    is_tracing_enabled,
)
from agent_service.infrastructure.observability.tracing_instrumentation import (
    instrument_fastapi,
    instrument_database,
    instrument_redis,
    instrument_http_client,
    add_span_attributes,
    add_span_event,
    set_span_error,
    create_span_name,
)
from agent_service.infrastructure.observability.decorators import (
    traced,
    traced_async,
    trace_agent_invocation,
    trace_tool_execution,
)
from agent_service.infrastructure.observability.error_tracking import (
    init_sentry,
    set_user_context,
    set_request_context,
    capture_exception,
    capture_message,
    clear_user_context,
    add_breadcrumb,
    set_tag,
    set_context,
    flush,
)

__all__ = [
    # Core tracing
    "init_tracing",
    "get_tracer",
    "shutdown_tracing",
    "is_tracing_enabled",
    # Instrumentation
    "instrument_fastapi",
    "instrument_database",
    "instrument_redis",
    "instrument_http_client",
    "add_span_attributes",
    "add_span_event",
    "set_span_error",
    "create_span_name",
    # Decorators
    "traced",
    "traced_async",
    "trace_agent_invocation",
    "trace_tool_execution",
    # Error tracking
    "init_sentry",
    "set_user_context",
    "set_request_context",
    "capture_exception",
    "capture_message",
    "clear_user_context",
    "add_breadcrumb",
    "set_tag",
    "set_context",
    "flush",
]
