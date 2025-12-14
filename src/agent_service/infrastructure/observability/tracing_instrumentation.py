"""
OpenTelemetry automatic instrumentation for common libraries and frameworks.

This module provides instrumentation helpers for:
- FastAPI applications
- SQLAlchemy database connections
- Redis cache operations
- HTTP clients (httpx)
- Custom span attributes

Each instrumentation function can be called independently, allowing selective
instrumentation based on what components are actually used in the application.
"""
import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.trace import Span, Status, StatusCode

logger = logging.getLogger(__name__)


def instrument_fastapi(app: FastAPI) -> None:
    """
    Instrument FastAPI application with automatic tracing.

    This adds automatic span creation for all HTTP requests, including:
    - Request/response metadata
    - HTTP method, path, status code
    - Request duration
    - Exception tracking

    Args:
        app: FastAPI application instance to instrument

    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> instrument_fastapi(app)
    """
    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumentation enabled")
    except Exception as e:
        logger.error(f"Failed to instrument FastAPI: {e}", exc_info=True)


def instrument_database(engine: Any) -> None:
    """
    Instrument SQLAlchemy database engine with tracing.

    This adds automatic span creation for all database queries, including:
    - SQL statements (sanitized)
    - Database name and operation
    - Query duration
    - Connection pool metrics

    Args:
        engine: SQLAlchemy engine instance to instrument

    Example:
        >>> from sqlalchemy import create_engine
        >>> engine = create_engine("postgresql://...")
        >>> instrument_database(engine)
    """
    try:
        SQLAlchemyInstrumentor().instrument(
            engine=engine,
            enable_commenter=True,  # Add trace context as SQL comments
        )
        logger.info("SQLAlchemy instrumentation enabled")
    except Exception as e:
        logger.error(f"Failed to instrument SQLAlchemy: {e}", exc_info=True)


def instrument_redis(client: Optional[Any] = None) -> None:
    """
    Instrument Redis client with tracing.

    This adds automatic span creation for all Redis operations, including:
    - Redis commands (GET, SET, etc.)
    - Key names (sanitized)
    - Operation duration
    - Connection details

    Args:
        client: Optional Redis client instance. If None, instruments all Redis clients.

    Example:
        >>> from redis import Redis
        >>> redis_client = Redis(host='localhost', port=6379)
        >>> instrument_redis(redis_client)
    """
    try:
        if client:
            RedisInstrumentor().instrument_connection(client)
        else:
            # Instrument all Redis connections
            RedisInstrumentor().instrument()
        logger.info("Redis instrumentation enabled")
    except Exception as e:
        logger.error(f"Failed to instrument Redis: {e}", exc_info=True)


def instrument_http_client() -> None:
    """
    Instrument httpx HTTP client library with tracing.

    This adds automatic span creation for all outbound HTTP requests, including:
    - Request URL, method, headers
    - Response status code
    - Request/response duration
    - Distributed trace context propagation

    Example:
        >>> instrument_http_client()
        >>> import httpx
        >>> async with httpx.AsyncClient() as client:
        ...     response = await client.get("https://api.example.com")
    """
    try:
        HTTPXClientInstrumentor().instrument()
        logger.info("HTTPX instrumentation enabled")
    except Exception as e:
        logger.error(f"Failed to instrument HTTPX: {e}", exc_info=True)


def add_span_attributes(span: Span, attributes: Dict[str, Any]) -> None:
    """
    Add custom attributes to a span with type coercion and validation.

    Attributes are key-value pairs that provide additional context to spans.
    Common attributes for agent services include:
    - user_id: Identifier of the user making the request
    - agent_name: Name of the agent being invoked
    - tool_name: Name of the tool being used
    - session_id: Session identifier for multi-turn conversations
    - model_name: LLM model being used
    - token_count: Number of tokens consumed
    - input_length: Length of input text
    - output_length: Length of output text

    Args:
        span: The span to add attributes to
        attributes: Dictionary of attribute key-value pairs

    Example:
        >>> from opentelemetry import trace
        >>> tracer = trace.get_tracer(__name__)
        >>> with tracer.start_as_current_span("operation") as span:
        ...     add_span_attributes(span, {
        ...         "user_id": "user123",
        ...         "agent_name": "assistant",
        ...         "token_count": 150
        ...     })
    """
    if not span or not span.is_recording():
        return

    for key, value in attributes.items():
        try:
            # OpenTelemetry supports: str, bool, int, float, list of primitives
            if value is None:
                continue

            # Convert non-supported types to strings
            if isinstance(value, (str, bool, int, float)):
                span.set_attribute(key, value)
            elif isinstance(value, (list, tuple)):
                # Ensure all list elements are primitives
                if all(isinstance(v, (str, bool, int, float)) for v in value):
                    span.set_attribute(key, list(value))
                else:
                    span.set_attribute(key, str(value))
            else:
                # Convert complex types to string representation
                span.set_attribute(key, str(value))

        except Exception as e:
            logger.warning(f"Failed to set span attribute {key}: {e}")


def add_span_event(
    span: Span,
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Add an event to a span with optional attributes.

    Events represent a point in time during a span's lifetime and are useful for:
    - Logging streaming chunks in agent responses
    - Recording tool invocations
    - Capturing intermediate results
    - Marking important milestones

    Args:
        span: The span to add the event to
        name: Name of the event
        attributes: Optional dictionary of event attributes

    Example:
        >>> from opentelemetry import trace
        >>> tracer = trace.get_tracer(__name__)
        >>> with tracer.start_as_current_span("agent_stream") as span:
        ...     add_span_event(span, "chunk_received", {
        ...         "chunk_index": 0,
        ...         "chunk_text": "Hello"
        ...     })
    """
    if not span or not span.is_recording():
        return

    try:
        if attributes:
            # Clean attributes to ensure they're OTel-compatible
            clean_attrs = {}
            for key, value in attributes.items():
                if isinstance(value, (str, bool, int, float)):
                    clean_attrs[key] = value
                elif value is not None:
                    clean_attrs[key] = str(value)

            span.add_event(name, attributes=clean_attrs)
        else:
            span.add_event(name)

    except Exception as e:
        logger.warning(f"Failed to add span event {name}: {e}")


def set_span_error(span: Span, exception: Exception) -> None:
    """
    Mark a span as errored and record exception details.

    This sets the span status to ERROR and records exception information
    as span attributes, following OpenTelemetry semantic conventions.

    Args:
        span: The span to mark as errored
        exception: The exception that occurred

    Example:
        >>> from opentelemetry import trace
        >>> tracer = trace.get_tracer(__name__)
        >>> with tracer.start_as_current_span("operation") as span:
        ...     try:
        ...         risky_operation()
        ...     except Exception as e:
        ...         set_span_error(span, e)
        ...         raise
    """
    if not span or not span.is_recording():
        return

    try:
        # Set span status to ERROR
        span.set_status(Status(StatusCode.ERROR, str(exception)))

        # Record exception details following semantic conventions
        span.set_attribute("exception.type", type(exception).__name__)
        span.set_attribute("exception.message", str(exception))

        # Record the exception as an event
        span.record_exception(exception)

    except Exception as e:
        logger.warning(f"Failed to set span error: {e}")


def create_span_name(
    component: str,
    operation: str,
    resource: Optional[str] = None,
) -> str:
    """
    Create a standardized span name following naming conventions.

    Span names should be:
    - Low cardinality (not include unique IDs)
    - Descriptive and hierarchical
    - Follow pattern: component.operation or component.operation.resource

    Args:
        component: Component or service name (e.g., "agent", "database", "cache")
        operation: Operation being performed (e.g., "invoke", "query", "get")
        resource: Optional resource type (e.g., "user", "session")

    Returns:
        Formatted span name

    Example:
        >>> create_span_name("agent", "invoke", "assistant")
        'agent.invoke.assistant'
        >>> create_span_name("database", "query")
        'database.query'
    """
    parts = [component, operation]
    if resource:
        parts.append(resource)
    return ".".join(parts)
