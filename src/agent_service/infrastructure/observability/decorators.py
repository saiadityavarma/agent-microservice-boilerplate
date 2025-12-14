"""
Decorators for adding OpenTelemetry tracing to functions and methods.

This module provides convenient decorators for instrumenting custom code with
distributed tracing. The decorators automatically:
- Create spans for function execution
- Capture function arguments as span attributes
- Record exceptions and errors
- Support both synchronous and asynchronous functions

Usage:
    @traced(name="process_user_input")
    def process_input(user_id: str, message: str):
        # Your code here
        pass

    @traced_async(name="call_llm")
    async def call_llm(prompt: str):
        # Your async code here
        pass
"""
import functools
import inspect
import logging
from typing import Any, Callable, Dict, Optional, TypeVar, cast

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from agent_service.infrastructure.observability.tracing import get_tracer, is_tracing_enabled
from agent_service.infrastructure.observability.tracing_instrumentation import (
    add_span_attributes,
    set_span_error,
)

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def traced(
    name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
    record_args: bool = False,
    exclude_args: Optional[list[str]] = None,
) -> Callable[[F], F]:
    """
    Decorator to trace synchronous function execution.

    Creates a span for the duration of the function call and automatically
    records exceptions if they occur.

    Args:
        name: Optional span name. If not provided, uses function name.
        attributes: Optional dict of attributes to add to the span.
        record_args: If True, records function arguments as span attributes.
        exclude_args: List of argument names to exclude from recording (e.g., passwords).

    Returns:
        Decorated function

    Example:
        >>> @traced(name="database.query_user", record_args=True, exclude_args=["password"])
        ... def get_user(user_id: str, password: str):
        ...     return database.query(user_id, password)

        >>> @traced(attributes={"component": "auth"})
        ... def authenticate(token: str):
        ...     return verify_token(token)
    """

    def decorator(func: F) -> F:
        # If tracing is disabled, return the original function
        if not is_tracing_enabled():
            return func

        span_name = name or f"{func.__module__}.{func.__name__}"
        tracer = get_tracer(func.__module__)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span(span_name) as span:
                try:
                    # Add custom attributes
                    if attributes:
                        add_span_attributes(span, attributes)

                    # Record function arguments if requested
                    if record_args and span.is_recording():
                        _record_function_args(
                            span, func, args, kwargs, exclude_args or []
                        )

                    # Execute the function
                    result = func(*args, **kwargs)

                    # Mark span as successful
                    span.set_status(Status(StatusCode.OK))

                    return result

                except Exception as e:
                    # Record the exception
                    set_span_error(span, e)
                    raise

        return cast(F, wrapper)

    return decorator


def traced_async(
    name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
    record_args: bool = False,
    exclude_args: Optional[list[str]] = None,
) -> Callable[[F], F]:
    """
    Decorator to trace asynchronous function execution.

    Creates a span for the duration of the async function call and automatically
    records exceptions if they occur.

    Args:
        name: Optional span name. If not provided, uses function name.
        attributes: Optional dict of attributes to add to the span.
        record_args: If True, records function arguments as span attributes.
        exclude_args: List of argument names to exclude from recording (e.g., passwords).

    Returns:
        Decorated async function

    Example:
        >>> @traced_async(name="llm.generate", record_args=True)
        ... async def generate_response(prompt: str, model: str):
        ...     return await llm_client.generate(prompt, model)

        >>> @traced_async(attributes={"service": "agent"})
        ... async def invoke_agent(input: str):
        ...     return await agent.invoke(input)
    """

    def decorator(func: F) -> F:
        # If tracing is disabled, return the original function
        if not is_tracing_enabled():
            return func

        span_name = name or f"{func.__module__}.{func.__name__}"
        tracer = get_tracer(func.__module__)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span(span_name) as span:
                try:
                    # Add custom attributes
                    if attributes:
                        add_span_attributes(span, attributes)

                    # Record function arguments if requested
                    if record_args and span.is_recording():
                        _record_function_args(
                            span, func, args, kwargs, exclude_args or []
                        )

                    # Execute the async function
                    result = await func(*args, **kwargs)

                    # Mark span as successful
                    span.set_status(Status(StatusCode.OK))

                    return result

                except Exception as e:
                    # Record the exception
                    set_span_error(span, e)
                    raise

        return cast(F, wrapper)

    return decorator


def _record_function_args(
    span: Any,
    func: Callable,
    args: tuple,
    kwargs: dict,
    exclude_args: list[str],
) -> None:
    """
    Record function arguments as span attributes.

    Args:
        span: The span to add attributes to
        func: The function being traced
        args: Positional arguments
        kwargs: Keyword arguments
        exclude_args: List of argument names to exclude
    """
    try:
        # Get function signature
        sig = inspect.signature(func)
        bound_args = sig.bind_partial(*args, **kwargs)
        bound_args.apply_defaults()

        # Record each argument
        for param_name, param_value in bound_args.arguments.items():
            # Skip excluded arguments
            if param_name in exclude_args:
                continue

            # Skip 'self' and 'cls' for methods
            if param_name in ("self", "cls"):
                continue

            # Create attribute key
            attr_key = f"function.arg.{param_name}"

            # Record the value (convert to string for complex types)
            if isinstance(param_value, (str, int, float, bool)):
                span.set_attribute(attr_key, param_value)
            elif param_value is None:
                span.set_attribute(attr_key, "None")
            else:
                # For complex types, record the type name
                span.set_attribute(attr_key, type(param_value).__name__)

    except Exception as e:
        logger.warning(f"Failed to record function arguments: {e}")


def trace_agent_invocation(
    agent_name: str,
    attributes: Optional[Dict[str, Any]] = None,
) -> Callable[[F], F]:
    """
    Specialized decorator for tracing agent invocations.

    This decorator adds agent-specific attributes and follows best practices
    for tracing AI agent operations, including:
    - Agent name and version
    - Input/output lengths
    - Token counts (if available)
    - Model information

    Args:
        agent_name: Name of the agent being invoked
        attributes: Optional additional attributes

    Returns:
        Decorated function

    Example:
        >>> @trace_agent_invocation(agent_name="assistant", attributes={"model": "gpt-4"})
        ... async def invoke_assistant(input: AgentInput) -> AgentOutput:
        ...     return await assistant.invoke(input)
    """

    def decorator(func: F) -> F:
        if not is_tracing_enabled():
            return func

        tracer = get_tracer(func.__module__)
        span_name = f"agent.invoke.{agent_name}"

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span(span_name) as span:
                try:
                    # Add agent-specific attributes
                    span.set_attribute("agent.name", agent_name)

                    if attributes:
                        add_span_attributes(span, attributes)

                    # Try to extract input information if first arg is AgentInput
                    if args and hasattr(args[0], "message"):
                        input_obj = args[0]
                        span.set_attribute("agent.input.length", len(input_obj.message))
                        if hasattr(input_obj, "session_id") and input_obj.session_id:
                            span.set_attribute("agent.session_id", input_obj.session_id)
                        if hasattr(input_obj, "user_id") and input_obj.user_id:
                            span.set_attribute("agent.user_id", input_obj.user_id)

                    # Execute the function
                    result = await func(*args, **kwargs)

                    # Try to extract output information
                    if hasattr(result, "content"):
                        span.set_attribute("agent.output.length", len(result.content))
                    if hasattr(result, "metadata") and isinstance(result.metadata, dict):
                        # Extract token count if available
                        if "token_count" in result.metadata:
                            span.set_attribute("agent.token_count", result.metadata["token_count"])
                        if "model" in result.metadata:
                            span.set_attribute("agent.model", result.metadata["model"])

                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    set_span_error(span, e)
                    raise

        return cast(F, wrapper)

    return decorator


def trace_tool_execution(
    tool_name: str,
    attributes: Optional[Dict[str, Any]] = None,
) -> Callable[[F], F]:
    """
    Specialized decorator for tracing tool executions.

    This decorator adds tool-specific attributes and follows best practices
    for tracing agent tool operations.

    Args:
        tool_name: Name of the tool being executed
        attributes: Optional additional attributes

    Returns:
        Decorated function

    Example:
        >>> @trace_tool_execution(tool_name="web_search")
        ... async def search_web(query: str) -> dict:
        ...     return await search_api.search(query)
    """

    def decorator(func: F) -> F:
        if not is_tracing_enabled():
            return func

        tracer = get_tracer(func.__module__)
        span_name = f"tool.execute.{tool_name}"

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span(span_name) as span:
                try:
                    # Add tool-specific attributes
                    span.set_attribute("tool.name", tool_name)

                    if attributes:
                        add_span_attributes(span, attributes)

                    # Execute the function
                    result = await func(*args, **kwargs)

                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    set_span_error(span, e)
                    raise

        return cast(F, wrapper)

    return decorator
