"""
Examples of using the @agent decorator.

This module demonstrates various ways to create agents using decorators
instead of implementing the IAgent interface manually.
"""

from typing import AsyncGenerator

from agent_service.interfaces import AgentInput, AgentOutput, StreamChunk
from agent_service.agent.context import AgentContext
from agent_service.agent.decorators import agent, streaming_agent


# ============================================================================
# Example 1: Simple Agent
# ============================================================================


@agent(name="echo_agent", description="Echoes back the input message")
async def echo_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    """
    Simple agent that echoes back the input.

    This demonstrates the minimal agent implementation.
    """
    ctx.logger.info("echo_agent_called", message_length=len(input.message))

    return AgentOutput(
        content=f"You said: {input.message}",
        metadata={"length": len(input.message)},
    )


# ============================================================================
# Example 2: Agent Using Tools
# ============================================================================


@agent(name="search_agent", description="Searches the web and formats results")
async def search_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    """
    Agent that uses the web search tool.

    Demonstrates calling tools from an agent.
    """
    ctx.logger.info("search_agent_started", query=input.message)

    try:
        # Call the echo tool as an example (replace with actual web_search tool)
        result = await ctx.call_tool("echo", message=input.message)

        return AgentOutput(
            content=f"Search results: {result}",
            metadata={"query": input.message},
        )
    except Exception as e:
        ctx.logger.error("search_failed", error=str(e))
        return AgentOutput(
            content=f"Sorry, search failed: {str(e)}",
            metadata={"error": str(e)},
        )


# ============================================================================
# Example 3: Agent Using Cache
# ============================================================================


@agent(name="cached_agent", description="Uses caching to avoid redundant work")
async def cached_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    """
    Agent that uses caching to store and retrieve results.

    Demonstrates cache usage in agents.
    """
    cache_key = f"result:{input.message}"

    # Try to get from cache
    if ctx.cache:
        cached_result = await ctx.cache.get(cache_key)
        if cached_result:
            ctx.logger.info("cache_hit", key=cache_key)
            return AgentOutput(
                content=cached_result,
                metadata={"cached": True},
            )

    # Compute result
    ctx.logger.info("cache_miss", key=cache_key)
    result = f"Processed: {input.message}"

    # Store in cache for 5 minutes
    if ctx.cache:
        await ctx.cache.set(cache_key, result, ttl=300)

    return AgentOutput(
        content=result,
        metadata={"cached": False},
    )


# ============================================================================
# Example 4: Agent Using Database
# ============================================================================


@agent(name="db_agent", description="Queries the database")
async def db_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    """
    Agent that queries the database using the sql_query tool.

    Demonstrates database access in agents.
    """
    if not ctx.db:
        return AgentOutput(
            content="Database not available",
            metadata={"error": "no_database"},
        )

    try:
        # Use the SQL query tool
        result = await ctx.call_tool(
            "sql_query",
            query="SELECT COUNT(*) as count FROM users WHERE is_active = :active",
            params={"active": True},
        )

        count = result["rows"][0]["count"] if result["rows"] else 0

        return AgentOutput(
            content=f"Found {count} active users",
            metadata={"count": count},
        )
    except Exception as e:
        ctx.logger.error("db_query_failed", error=str(e))
        return AgentOutput(
            content=f"Database query failed: {str(e)}",
            metadata={"error": str(e)},
        )


# ============================================================================
# Example 5: Agent With User Context
# ============================================================================


@agent(name="user_aware_agent", description="Agent that uses user context")
async def user_aware_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    """
    Agent that accesses user information.

    Demonstrates user context and permissions.
    """
    if not ctx.user:
        return AgentOutput(
            content="Authentication required",
            metadata={"authenticated": False},
        )

    # Check permissions
    if not ctx.user.has_role("user"):
        return AgentOutput(
            content="Insufficient permissions",
            metadata={"authenticated": True, "authorized": False},
        )

    ctx.logger.info("processing_for_user", user=ctx.user.email)

    return AgentOutput(
        content=f"Hello {ctx.user.name}! You asked: {input.message}",
        metadata={
            "user_id": str(ctx.user.id),
            "user_email": ctx.user.email,
        },
    )


# ============================================================================
# Example 6: Streaming Agent
# ============================================================================


@streaming_agent(
    name="streaming_chat",
    description="Streams responses word by word"
)
async def streaming_chat(
    input: AgentInput,
    ctx: AgentContext
) -> AsyncGenerator[StreamChunk, None]:
    """
    Streaming agent that yields chunks.

    Demonstrates streaming output.
    """
    import asyncio

    ctx.logger.info("streaming_chat_started")

    # Simulate streaming response
    words = input.message.split()

    for i, word in enumerate(words):
        # Simulate processing time
        await asyncio.sleep(0.1)

        # Yield text chunk
        yield StreamChunk(
            type="text",
            content=f"{word} ",
            metadata={"word_index": i},
        )

    # Final chunk
    yield StreamChunk(
        type="text",
        content="\n[Done]",
        metadata={"final": True},
    )


# ============================================================================
# Example 7: Agent Using Secrets
# ============================================================================


@agent(name="api_agent", description="Calls external APIs with secrets")
async def api_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    """
    Agent that uses secrets to call external APIs.

    Demonstrates secrets management in agents.
    """
    # Get API key from secrets
    api_key = await ctx.get_secret("EXTERNAL_API_KEY")

    if not api_key:
        return AgentOutput(
            content="API key not configured",
            metadata={"error": "missing_api_key"},
        )

    ctx.logger.info("calling_external_api")

    try:
        # Call HTTP tool with API key
        result = await ctx.call_tool(
            "http_get",
            url="https://api.example.com/data",
            headers={"Authorization": f"Bearer {api_key}"},
        )

        return AgentOutput(
            content=f"API response: {result}",
            metadata={"status_code": result.get("status_code")},
        )
    except Exception as e:
        ctx.logger.error("api_call_failed", error=str(e))
        return AgentOutput(
            content=f"API call failed: {str(e)}",
            metadata={"error": str(e)},
        )


# ============================================================================
# Example 8: Complex Agent with Multiple Operations
# ============================================================================


@agent(
    name="complex_agent",
    description="Performs multiple operations with error handling"
)
async def complex_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    """
    Complex agent that demonstrates multiple features.

    Demonstrates:
    - Tool calling
    - Cache usage
    - Error handling
    - Context logging
    - Conditional logic
    """
    # Bind additional context to logger
    ctx.bind_logger(operation="complex_agent")

    results = []

    # Step 1: Check cache
    cache_key = f"complex:{input.message}"
    if ctx.cache:
        cached = await ctx.cache.get(cache_key)
        if cached:
            ctx.logger.info("returning_cached_result")
            return AgentOutput(content=cached, metadata={"cached": True})

    # Step 2: Call multiple tools
    try:
        # Echo the input
        echo_result = await ctx.call_tool("echo", message=input.message)
        results.append(f"Echo: {echo_result}")

        # Get HTTP data (example)
        try:
            http_result = await ctx.call_tool(
                "http_get",
                url="https://api.example.com/status"
            )
            results.append(f"API Status: {http_result.get('status_code')}")
        except Exception as e:
            ctx.logger.warning("http_call_failed", error=str(e))
            results.append(f"API call failed: {str(e)}")

        # Combine results
        final_result = "\n".join(results)

        # Step 3: Cache the result
        if ctx.cache:
            await ctx.cache.set(cache_key, final_result, ttl=60)

        return AgentOutput(
            content=final_result,
            metadata={
                "cached": False,
                "steps_completed": len(results),
            },
        )

    except Exception as e:
        ctx.logger.error("complex_agent_failed", error=str(e), exc_info=True)
        return AgentOutput(
            content=f"Agent execution failed: {str(e)}",
            metadata={"error": str(e)},
        )


# ============================================================================
# Example 9: Agent Without Auto-Registration
# ============================================================================


@agent(
    name="manual_agent",
    description="Agent that is not auto-registered",
    auto_register=False,
)
async def manual_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    """
    Agent that is not automatically registered.

    Use this when you want to manually control registration:
        >>> from agent_service.agent.registry import agent_registry
        >>> agent_registry.register(manual_agent)
    """
    return AgentOutput(content=f"Manual agent processed: {input.message}")


# ============================================================================
# Example 10: Agent with Session Context
# ============================================================================


@agent(
    name="session_agent",
    description="Agent that maintains session state"
)
async def session_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    """
    Agent that uses session_id to maintain conversation state.

    Demonstrates session management.
    """
    if not input.session_id:
        return AgentOutput(
            content="No session ID provided",
            metadata={"error": "no_session"},
        )

    # Use cache to store session state
    session_key = f"session:{input.session_id}:messages"

    messages = []
    if ctx.cache:
        cached_messages = await ctx.cache.get(session_key)
        if cached_messages:
            messages = cached_messages

    # Add current message
    messages.append(input.message)

    # Store updated messages (keep last 10)
    if ctx.cache:
        await ctx.cache.set(
            session_key,
            messages[-10:],
            ttl=3600  # 1 hour session
        )

    return AgentOutput(
        content=f"Message {len(messages)} in this session: {input.message}",
        metadata={
            "session_id": input.session_id,
            "message_count": len(messages),
        },
    )
