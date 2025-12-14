"""
OpenTelemetry distributed tracing setup.

This module provides complete OpenTelemetry instrumentation with support for:
- OTLP (OpenTelemetry Protocol) exporter
- Jaeger exporter
- Console exporter (for development)
- W3C TraceContext propagation
- Configurable sampling rates

Install dependencies:
    uv add opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi \
           opentelemetry-exporter-otlp opentelemetry-exporter-jaeger \
           opentelemetry-instrumentation-sqlalchemy opentelemetry-instrumentation-redis \
           opentelemetry-instrumentation-httpx
"""
import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, Tracer
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SpanExporter,
)
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION, DEPLOYMENT_ENVIRONMENT
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.propagate import set_global_textmap

from agent_service.config.settings import get_settings

logger = logging.getLogger(__name__)

_tracer_provider: Optional[TracerProvider] = None
_is_initialized: bool = False


def init_tracing(service_name: str, environment: str) -> None:
    """
    Initialize OpenTelemetry tracing with configured exporters.

    This function sets up the TracerProvider with appropriate exporters based on
    configuration, configures trace context propagation, and sets sampling rates.

    Args:
        service_name: Name of the service for trace identification
        environment: Environment name (local, dev, staging, prod)

    Returns:
        None

    Example:
        >>> init_tracing("agent-service", "production")
    """
    global _tracer_provider, _is_initialized

    if _is_initialized:
        logger.warning("Tracing already initialized, skipping re-initialization")
        return

    settings = get_settings()

    if not settings.tracing_enabled:
        logger.info("Tracing is disabled by configuration")
        return

    try:
        # Create resource with service information
        resource = Resource.create(
            {
                SERVICE_NAME: service_name,
                SERVICE_VERSION: settings.app_version,
                DEPLOYMENT_ENVIRONMENT: environment,
            }
        )

        # Configure sampling based on sample rate
        sampler = TraceIdRatioBased(settings.tracing_sample_rate)

        # Create tracer provider
        _tracer_provider = TracerProvider(
            resource=resource,
            sampler=sampler,
        )

        # Configure exporter based on settings
        exporter = _create_exporter(settings.tracing_exporter, settings.tracing_endpoint)

        if exporter:
            # Add span processor with exporter
            span_processor = BatchSpanProcessor(exporter)
            _tracer_provider.add_span_processor(span_processor)
            logger.info(
                f"Tracing initialized with {settings.tracing_exporter} exporter, "
                f"sample_rate={settings.tracing_sample_rate}"
            )
        else:
            logger.warning("No exporter configured, tracing will be disabled")
            return

        # Set global tracer provider
        trace.set_tracer_provider(_tracer_provider)

        # Configure W3C TraceContext propagation
        set_global_textmap(TraceContextTextMapPropagator())

        _is_initialized = True

    except Exception as e:
        logger.error(f"Failed to initialize tracing: {e}", exc_info=True)
        # Don't raise - allow application to continue without tracing


def _create_exporter(exporter_type: str, endpoint: str) -> Optional[SpanExporter]:
    """
    Create the appropriate span exporter based on configuration.

    Args:
        exporter_type: Type of exporter (otlp, jaeger, console, none)
        endpoint: Endpoint URL for the exporter

    Returns:
        SpanExporter instance or None if exporter_type is 'none'
    """
    if exporter_type == "none":
        return None

    try:
        if exporter_type == "otlp":
            # OTLP exporter (works with Jaeger, Tempo, etc.)
            return OTLPSpanExporter(
                endpoint=endpoint,
                insecure=True,  # Use insecure for local development
            )

        elif exporter_type == "jaeger":
            # Legacy Jaeger exporter
            # Parse endpoint for Jaeger (expects host:port format)
            if "://" in endpoint:
                # Remove protocol if present
                endpoint = endpoint.split("://", 1)[1]
            host, port = endpoint.rsplit(":", 1) if ":" in endpoint else (endpoint, "6831")

            return JaegerExporter(
                agent_host_name=host,
                agent_port=int(port),
            )

        elif exporter_type == "console":
            # Console exporter for development
            return ConsoleSpanExporter()

        else:
            logger.error(f"Unknown exporter type: {exporter_type}")
            return None

    except Exception as e:
        logger.error(f"Failed to create {exporter_type} exporter: {e}", exc_info=True)
        return None


def get_tracer(name: str) -> Tracer:
    """
    Get a tracer instance for manual instrumentation.

    Args:
        name: Name for the tracer, typically __name__ of the calling module

    Returns:
        Tracer instance for creating spans

    Example:
        >>> tracer = get_tracer(__name__)
        >>> with tracer.start_as_current_span("operation_name"):
        ...     # Your code here
        ...     pass
    """
    return trace.get_tracer(name)


def is_tracing_enabled() -> bool:
    """
    Check if tracing has been initialized and is enabled.

    Returns:
        True if tracing is initialized, False otherwise
    """
    return _is_initialized


def shutdown_tracing() -> None:
    """
    Shutdown tracing and flush any pending spans.

    This should be called during application shutdown to ensure all spans
    are exported before the application terminates.
    """
    global _tracer_provider, _is_initialized

    if _tracer_provider:
        try:
            _tracer_provider.shutdown()
            logger.info("Tracing shutdown successfully")
        except Exception as e:
            logger.error(f"Error shutting down tracing: {e}", exc_info=True)
        finally:
            _tracer_provider = None
            _is_initialized = False
