"""
Examples of using OpenTelemetry distributed tracing in the agent service.

This module contains practical examples demonstrating various tracing patterns.
Use these as reference implementations for instrumenting your own code.
"""
from typing import AsyncGenerator, Dict, Any
import httpx

from agent_service.infrastructure.observability import (
    traced,
    traced_async,
    trace_agent_invocation,
    trace_tool_execution,
    get_tracer,
    add_span_attributes,
    add_span_event,
    set_span_error,
)
from agent_service.interfaces import IAgent, AgentInput, AgentOutput, StreamChunk


# ============================================================================
# Example 1: Simple Synchronous Function Tracing
# ============================================================================

@traced(name="data.process")
def process_data(data: dict) -> dict:
    """
    Simple synchronous function with automatic tracing.
    """
    # Your processing logic here
    processed = {k: v.upper() if isinstance(v, str) else v for k, v in data.items()}
    return processed


# ============================================================================
# Example 2: Async Function with Custom Attributes
# ============================================================================

@traced_async(
    name="database.query_user",
    attributes={
        "database.system": "postgresql",
        "database.operation": "select"
    }
)
async def query_user(user_id: str) -> dict:
    """
    Async function with custom attributes for better observability.
    """
    # Simulate database query
    user = {"id": user_id, "name": "John Doe", "email": "john@example.com"}
    return user


# ============================================================================
# Example 3: Recording Function Arguments (excluding sensitive data)
# ============================================================================

@traced_async(
    name="auth.authenticate",
    record_args=True,
    exclude_args=["password", "token"]  # Never log sensitive data
)
async def authenticate(username: str, password: str, remember_me: bool = False) -> dict:
    """
    Authentication function that records arguments (except password).

    The span will have attributes like:
    - function.arg.username: "john"
    - function.arg.remember_me: True
    """
    # Authentication logic here
    return {"user_id": "123", "authenticated": True}


# ============================================================================
# Example 4: Manual Instrumentation for Fine-Grained Control
# ============================================================================

async def complex_multi_step_operation(data: dict) -> dict:
    """
    Example showing manual instrumentation for operations with multiple steps.
    """
    tracer = get_tracer(__name__)

    with tracer.start_as_current_span("operation.complex") as span:
        # Add initial attributes
        add_span_attributes(span, {
            "operation.type": "multi_step",
            "input.size": len(data)
        })

        # Step 1: Validation
        add_span_event(span, "validation_started")
        validated_data = await validate_data(data)
        add_span_event(span, "validation_completed")

        # Step 2: Processing
        add_span_event(span, "processing_started")
        processed_data = await process_complex_data(validated_data)
        add_span_event(span, "processing_completed", {
            "output.size": len(processed_data)
        })

        # Step 3: Persistence
        add_span_event(span, "persistence_started")
        await save_data(processed_data)
        add_span_event(span, "persistence_completed")

        # Add final statistics
        span.set_attribute("operation.steps_completed", 3)

        return processed_data


# ============================================================================
# Example 5: Agent Invocation Tracing
# ============================================================================

class ExampleAgent(IAgent):
    """
    Example agent demonstrating proper instrumentation.
    """

    @property
    def name(self) -> str:
        return "example_agent"

    @property
    def description(self) -> str:
        return "Example agent with tracing"

    @trace_agent_invocation(
        agent_name="example_agent",
        attributes={
            "agent.model": "gpt-4",
            "agent.temperature": 0.7,
            "agent.max_tokens": 2000
        }
    )
    async def invoke(self, input: AgentInput) -> AgentOutput:
        """
        Agent invocation with automatic tracing of:
        - Input/output lengths
        - Session and user IDs
        - Token counts from metadata
        """
        # Simulate LLM call
        response = await self._call_llm(input.message)

        return AgentOutput(
            content=response,
            metadata={
                "token_count": 150,  # Automatically captured
                "model": "gpt-4",    # Automatically captured
                "session_id": input.session_id
            }
        )

    async def stream(self, input: AgentInput) -> AsyncGenerator[StreamChunk, None]:
        """
        Streaming implementation with event tracking.
        """
        tracer = get_tracer(__name__)

        with tracer.start_as_current_span("agent.stream.example_agent") as span:
            # Add span attributes
            span.set_attribute("agent.name", self.name)
            span.set_attribute("agent.input.length", len(input.message))

            if input.session_id:
                span.set_attribute("agent.session_id", input.session_id)

            # Simulate streaming
            chunks = ["This ", "is ", "a ", "streamed ", "response."]
            chunk_count = 0

            for chunk_text in chunks:
                chunk_count += 1

                # Record each chunk as an event
                add_span_event(span, "chunk_generated", {
                    "chunk.index": chunk_count,
                    "chunk.length": len(chunk_text)
                })

                yield StreamChunk(type="text", content=chunk_text)

            # Record final statistics
            span.set_attribute("agent.chunk_count", chunk_count)
            span.set_attribute("agent.output.length", sum(len(c) for c in chunks))

    async def _call_llm(self, prompt: str) -> str:
        """Simulate LLM call."""
        return f"Response to: {prompt}"


# ============================================================================
# Example 6: Tool Execution Tracing
# ============================================================================

@trace_tool_execution(
    tool_name="web_search",
    attributes={
        "tool.category": "search",
        "tool.provider": "google"
    }
)
async def search_web(query: str, max_results: int = 10) -> list[dict]:
    """
    Tool execution with automatic tracing.
    """
    tracer = get_tracer(__name__)

    # Get the current span to add more attributes
    from opentelemetry import trace
    current_span = trace.get_current_span()

    if current_span:
        current_span.set_attribute("search.query", query)
        current_span.set_attribute("search.max_results", max_results)

    # Simulate web search
    results = [
        {"title": f"Result {i}", "url": f"https://example.com/{i}"}
        for i in range(max_results)
    ]

    if current_span:
        current_span.set_attribute("search.results_found", len(results))

    return results


# ============================================================================
# Example 7: Error Handling and Span Status
# ============================================================================

@traced_async(name="risky.operation")
async def risky_operation(data: dict) -> dict:
    """
    Example showing proper error handling with tracing.
    """
    tracer = get_tracer(__name__)

    with tracer.start_as_current_span("risky.operation.internal") as span:
        try:
            # Add attributes
            add_span_attributes(span, {
                "operation.type": "risky",
                "input.size": len(data)
            })

            # Simulate a risky operation
            if "error" in data:
                raise ValueError("Invalid data received")

            # Process data
            result = await process_risky_data(data)

            # Success
            span.set_attribute("operation.success", True)
            return result

        except Exception as e:
            # Record the error in the span
            set_span_error(span, e)
            span.set_attribute("operation.success", False)
            # Re-raise the exception
            raise


# ============================================================================
# Example 8: Nested Spans for Complex Operations
# ============================================================================

async def orchestrate_agent_workflow(user_input: str) -> dict:
    """
    Example of nested spans for a complex workflow.
    """
    tracer = get_tracer(__name__)

    with tracer.start_as_current_span("workflow.orchestrate") as parent_span:
        parent_span.set_attribute("workflow.type", "agent_pipeline")

        # Step 1: Input validation (child span)
        with tracer.start_as_current_span("workflow.validate_input") as validation_span:
            validation_span.set_attribute("input.length", len(user_input))
            validated_input = await validate_user_input(user_input)
            add_span_event(validation_span, "validation_passed")

        # Step 2: Agent invocation (child span)
        with tracer.start_as_current_span("workflow.invoke_agent") as agent_span:
            agent_span.set_attribute("agent.name", "main_agent")
            agent_response = await call_agent(validated_input)
            agent_span.set_attribute("response.length", len(agent_response))

        # Step 3: Post-processing (child span)
        with tracer.start_as_current_span("workflow.post_process") as post_span:
            result = await post_process_response(agent_response)
            post_span.set_attribute("result.type", type(result).__name__)

        # Add final workflow statistics
        parent_span.set_attribute("workflow.steps_completed", 3)
        parent_span.set_attribute("workflow.success", True)

        return result


# ============================================================================
# Example 9: HTTP Client Instrumentation
# ============================================================================

@traced_async(name="external.api_call")
async def call_external_api(endpoint: str, data: dict) -> dict:
    """
    Example showing HTTP client tracing (httpx is auto-instrumented).
    """
    tracer = get_tracer(__name__)

    with tracer.start_as_current_span("external.api.prepare") as span:
        span.set_attribute("http.endpoint", endpoint)
        span.set_attribute("http.method", "POST")

        # httpx client is automatically instrumented
        async with httpx.AsyncClient() as client:
            # This HTTP request will automatically create a child span
            # with trace context propagation
            response = await client.post(endpoint, json=data)

            span.set_attribute("http.status_code", response.status_code)

            return response.json()


# ============================================================================
# Example 10: Conditional Tracing
# ============================================================================

async def conditionally_traced_operation(data: dict, trace: bool = True) -> dict:
    """
    Example showing how to conditionally enable tracing.
    """
    from agent_service.infrastructure.observability import is_tracing_enabled

    if trace and is_tracing_enabled():
        # Tracing is enabled - create span
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("operation.conditional") as span:
            span.set_attribute("tracing.conditional", True)
            return await process_data_internal(data)
    else:
        # Tracing is disabled - skip span creation
        return await process_data_internal(data)


# ============================================================================
# Helper functions for examples
# ============================================================================

async def validate_data(data: dict) -> dict:
    """Helper: validate data."""
    return data

async def process_complex_data(data: dict) -> dict:
    """Helper: process data."""
    return data

async def save_data(data: dict) -> None:
    """Helper: save data."""
    pass

async def validate_user_input(user_input: str) -> str:
    """Helper: validate user input."""
    return user_input

async def call_agent(input_data: str) -> str:
    """Helper: call agent."""
    return f"Agent response to: {input_data}"

async def post_process_response(response: str) -> dict:
    """Helper: post-process response."""
    return {"response": response}

async def process_risky_data(data: dict) -> dict:
    """Helper: process risky data."""
    return data

async def process_data_internal(data: dict) -> dict:
    """Helper: process data internally."""
    return data
