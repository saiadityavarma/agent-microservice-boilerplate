"""
Agent decorator for easy agent creation.

Provides a decorator-based approach to creating agents without implementing
the full IAgent interface manually. Supports both sync and streaming agents.
"""

from __future__ import annotations
from typing import Callable, AsyncGenerator, Any, Awaitable
from functools import wraps
import asyncio
import time
import inspect

from agent_service.interfaces import IAgent, AgentInput, AgentOutput, StreamChunk
from agent_service.agent.context import AgentContext
from agent_service.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


class DecoratedAgent(IAgent):
    """
    IAgent implementation that wraps a decorated function.

    Automatically handles:
    - Context creation
    - Error handling
    - Metrics collection
    - Streaming support
    """

    def __init__(
        self,
        func: Callable[[AgentInput, AgentContext], Awaitable[AgentOutput | AsyncGenerator[StreamChunk, None]]],
        name: str,
        description: str,
        auto_register: bool = True,
    ):
        """
        Initialize a decorated agent.

        Args:
            func: The agent function to wrap
            name: Agent name
            description: Agent description
            auto_register: Whether to auto-register with the agent registry
        """
        self._func = func
        self._name = name
        self._description = description
        self._is_generator = inspect.isasyncgenfunction(func)

        # Auto-register if requested
        if auto_register:
            from agent_service.agent.registry import agent_registry

            agent_registry.register(self)
            logger.info("agent_registered", agent=name, description=description)

    @property
    def name(self) -> str:
        """Get agent name."""
        return self._name

    @property
    def description(self) -> str:
        """Get agent description."""
        return self._description

    async def _create_context(
        self,
        input: AgentInput,
    ) -> AgentContext:
        """
        Create an agent context for the execution.

        Args:
            input: Agent input

        Returns:
            AgentContext instance
        """
        from agent_service.tools.registry import tool_registry
        from agent_service.infrastructure.cache.cache import get_cache
        from agent_service.infrastructure.database.connection import db
        from agent_service.api.middleware.request_id import get_request_id

        # Create context with available resources
        cache = await get_cache(namespace=f"agent:{self._name}")

        # Get database session if available
        db_session = None
        if db.is_connected:
            # Note: We don't create a session here directly
            # Users should use async with ctx.db.session() if they need it
            pass

        # Get user info from input context if available
        user = None
        if input.context and "user" in input.context:
            from agent_service.agent.context import UserInfo

            user_data = input.context["user"]
            if isinstance(user_data, dict):
                user = UserInfo(**user_data)
            else:
                user = user_data

        # Get request ID
        request_id = get_request_id() or input.context.get("request_id") if input.context else None

        # Create logger with context
        agent_logger = logger.bind(
            agent=self._name,
            session_id=input.session_id,
            request_id=request_id,
        )

        return AgentContext(
            tools=tool_registry,
            db=db_session,
            cache=cache,
            logger=agent_logger,
            user=user,
            request_id=request_id,
        )

    async def invoke(self, input: AgentInput) -> AgentOutput:
        """
        Execute the agent function.

        Args:
            input: Agent input

        Returns:
            Agent output

        Raises:
            Exception: Any exception from the agent function
        """
        start_time = time.time()
        ctx = await self._create_context(input)

        ctx.logger.info(
            "agent_invocation_started",
            message_length=len(input.message),
            session_id=input.session_id,
        )

        try:
            # Call the wrapped function
            if self._is_generator:
                # If it's a generator, collect all chunks into a single output
                chunks = []
                async for chunk in self._func(input, ctx):
                    if chunk.type == "text":
                        chunks.append(chunk.content)

                content = "".join(chunks)
                result = AgentOutput(content=content)
            else:
                result = await self._func(input, ctx)

            # Validate result type
            if not isinstance(result, AgentOutput):
                raise TypeError(
                    f"Agent function must return AgentOutput, got {type(result)}"
                )

            duration = time.time() - start_time
            ctx.logger.info(
                "agent_invocation_completed",
                success=True,
                duration_seconds=duration,
                output_length=len(result.content),
            )

            return result

        except Exception as e:
            duration = time.time() - start_time
            ctx.logger.error(
                "agent_invocation_failed",
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=duration,
                exc_info=True,
            )
            raise

    async def stream(self, input: AgentInput) -> AsyncGenerator[StreamChunk, None]:
        """
        Execute the agent function with streaming output.

        Args:
            input: Agent input

        Yields:
            StreamChunk for each piece of output

        Raises:
            Exception: Any exception from the agent function
        """
        start_time = time.time()
        ctx = await self._create_context(input)

        ctx.logger.info(
            "agent_stream_started",
            message_length=len(input.message),
            session_id=input.session_id,
        )

        chunk_count = 0
        total_length = 0

        try:
            if self._is_generator:
                # Function is already a generator
                async for chunk in self._func(input, ctx):
                    chunk_count += 1
                    if chunk.type == "text":
                        total_length += len(chunk.content)
                    yield chunk
            else:
                # Function returns AgentOutput, convert to stream
                result = await self._func(input, ctx)
                chunk_count = 1
                total_length = len(result.content)
                yield StreamChunk(type="text", content=result.content)

            duration = time.time() - start_time
            ctx.logger.info(
                "agent_stream_completed",
                success=True,
                duration_seconds=duration,
                chunk_count=chunk_count,
                total_length=total_length,
            )

        except Exception as e:
            duration = time.time() - start_time
            ctx.logger.error(
                "agent_stream_failed",
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=duration,
                chunk_count=chunk_count,
                exc_info=True,
            )
            # Yield error chunk
            yield StreamChunk(
                type="error",
                content=str(e),
                metadata={"error_type": type(e).__name__},
            )


def agent(
    name: str | None = None,
    description: str | None = None,
    auto_register: bool = True,
) -> Callable:
    """
    Decorator to create an agent from a simple function.

    The decorated function should accept (AgentInput, AgentContext) and return
    either AgentOutput or AsyncGenerator[StreamChunk, None] for streaming.

    Args:
        name: Agent name (defaults to function name)
        description: Agent description (defaults to function docstring)
        auto_register: Whether to auto-register with the agent registry (default: True)

    Returns:
        Decorated agent

    Example (non-streaming):
        >>> @agent(name="my_agent", description="Does something useful")
        >>> async def my_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
        ...     result = await ctx.call_tool("web_search", query=input.message)
        ...     return AgentOutput(content=str(result))

    Example (streaming):
        >>> @agent(name="streaming_agent", description="Streams responses")
        >>> async def streaming_agent(
        ...     input: AgentInput,
        ...     ctx: AgentContext
        ... ) -> AsyncGenerator[StreamChunk, None]:
        ...     for i in range(5):
        ...         yield StreamChunk(type="text", content=f"Chunk {i}\\n")
        ...         await asyncio.sleep(0.1)

    Example (with context usage):
        >>> @agent(name="context_agent", description="Uses context features")
        >>> async def context_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
        ...     # Access user
        ...     if ctx.user:
        ...         ctx.logger.info("processing_for_user", user=ctx.user.email)
        ...
        ...     # Use cache
        ...     cached = await ctx.cache.get("key")
        ...     if not cached:
        ...         cached = "computed_value"
        ...         await ctx.cache.set("key", cached, ttl=300)
        ...
        ...     # Call tools
        ...     result = await ctx.call_tool("echo", message=input.message)
        ...
        ...     # Get secrets
        ...     api_key = await ctx.get_secret("API_KEY")
        ...
        ...     return AgentOutput(content=f"Result: {result}")
    """

    def decorator(
        func: Callable[[AgentInput, AgentContext], Awaitable[AgentOutput | AsyncGenerator[StreamChunk, None]]]
    ) -> DecoratedAgent:
        # Determine name and description
        agent_name = name or func.__name__
        agent_description = description or func.__doc__ or f"Agent: {agent_name}"

        # Validate function signature
        sig = inspect.signature(func)
        params = list(sig.parameters.values())

        if len(params) != 2:
            raise TypeError(
                f"Agent function must accept exactly 2 parameters (input, ctx), got {len(params)}"
            )

        # Create the decorated agent
        decorated = DecoratedAgent(
            func=func,
            name=agent_name,
            description=agent_description,
            auto_register=auto_register,
        )

        return decorated

    return decorator


def streaming_agent(
    name: str | None = None,
    description: str | None = None,
    auto_register: bool = True,
) -> Callable:
    """
    Decorator specifically for streaming agents.

    This is an alias for @agent but makes it clear the agent is streaming.
    The decorated function must be an async generator that yields StreamChunk.

    Args:
        name: Agent name (defaults to function name)
        description: Agent description (defaults to function docstring)
        auto_register: Whether to auto-register with the agent registry (default: True)

    Returns:
        Decorated streaming agent

    Example:
        >>> @streaming_agent(name="chat", description="Streaming chat agent")
        >>> async def chat(
        ...     input: AgentInput,
        ...     ctx: AgentContext
        ... ) -> AsyncGenerator[StreamChunk, None]:
        ...     # Simulate streaming response
        ...     for word in input.message.split():
        ...         yield StreamChunk(type="text", content=f"{word} ")
        ...         await asyncio.sleep(0.1)
    """
    return agent(name=name, description=description, auto_register=auto_register)
