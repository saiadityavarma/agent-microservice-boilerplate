"""
Placeholder agent that echoes input.

Claude Code: Replace this with actual agent framework implementation.
See examples below for different frameworks.

This example demonstrates how to instrument an agent with distributed tracing.
"""
from typing import AsyncGenerator

from agent_service.interfaces import IAgent, AgentInput, AgentOutput, StreamChunk
from agent_service.infrastructure.observability.decorators import trace_agent_invocation
from agent_service.infrastructure.observability.tracing import get_tracer
from agent_service.infrastructure.observability.tracing_instrumentation import add_span_event


class PlaceholderAgent(IAgent):
    """
    Simple echo agent for testing the pipeline.

    Replace with actual implementation:
    - LangGraph: see agent/examples/langgraph_agent.py
    - AutoGen: see agent/examples/autogen_agent.py
    - Custom: implement IAgent directly
    """

    @property
    def name(self) -> str:
        return "placeholder"

    @property
    def description(self) -> str:
        return "Echo agent for testing"

    @trace_agent_invocation(
        agent_name="placeholder",
        attributes={"agent.type": "echo", "agent.version": "1.0"}
    )
    async def invoke(self, input: AgentInput) -> AgentOutput:
        """
        Echo the input back.

        This method is instrumented with distributed tracing using the
        @trace_agent_invocation decorator, which automatically:
        - Creates a span for the agent invocation
        - Records input/output lengths
        - Tracks session and user IDs
        - Handles exceptions
        """
        # The decorator automatically creates a span and records attributes
        # You can also manually add custom events or attributes within the function

        result_content = f"Echo: {input.message}"

        return AgentOutput(
            content=result_content,
            metadata={
                "session_id": input.session_id,
                "agent_name": self.name,
                "input_length": len(input.message),
                "output_length": len(result_content),
            },
        )

    async def stream(self, input: AgentInput) -> AsyncGenerator[StreamChunk, None]:
        """
        Stream the echo response word by word.

        This method demonstrates how to add tracing events for streaming operations.
        Each chunk is recorded as a span event for observability.
        """
        # Get the tracer for manual instrumentation
        tracer = get_tracer(__name__)

        # Create a span for the streaming operation
        with tracer.start_as_current_span("agent.stream.placeholder") as span:
            # Add span attributes
            span.set_attribute("agent.name", self.name)
            span.set_attribute("agent.input.length", len(input.message))
            if input.session_id:
                span.set_attribute("agent.session_id", input.session_id)
            if input.user_id:
                span.set_attribute("agent.user_id", input.user_id)

            # Stream the response
            words = f"Echo: {input.message}".split()
            chunk_count = 0

            for word in words:
                chunk_count += 1

                # Record each chunk as a span event
                add_span_event(
                    span,
                    "chunk_generated",
                    attributes={
                        "chunk.index": chunk_count,
                        "chunk.length": len(word),
                    }
                )

                yield StreamChunk(type="text", content=word + " ")

            # Record final statistics
            span.set_attribute("agent.chunk_count", chunk_count)
            span.set_attribute("agent.output.length", len(input.message) + 6)  # "Echo: " prefix
