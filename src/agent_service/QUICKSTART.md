# Quick Start Guide - Agent & Tool Decorators

Get started with the decorator system in 5 minutes!

## Installation

No additional installation needed. The decorator system is part of the core framework.

## Your First Agent

Create a simple agent in just a few lines:

```python
# my_agents.py
from agent_service.interfaces import AgentInput, AgentOutput
from agent_service.agent import agent, AgentContext

@agent(name="greeter", description="Greets the user")
async def greeter(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    return AgentOutput(content=f"Hello! You said: {input.message}")
```

That's it! The agent is automatically registered and ready to use.

## Your First Tool

Create a tool in just a few lines:

```python
# my_tools.py
from agent_service.tools import tool

@tool(name="reverse", description="Reverse a string")
async def reverse(text: str) -> str:
    return text[::-1]
```

Done! The tool is automatically registered.

## Using Tools in Agents

```python
from agent_service.agent import agent, AgentContext
from agent_service.interfaces import AgentInput, AgentOutput

@agent(name="reverser", description="Reverses user input")
async def reverser(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    # Call the tool
    result = await ctx.call_tool("reverse", text=input.message)
    return AgentOutput(content=f"Reversed: {result}")
```

## Using Built-in Tools

The framework includes built-in HTTP and SQL tools:

```python
@agent(name="api_caller", description="Calls external APIs")
async def api_caller(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    # HTTP GET request
    result = await ctx.call_tool(
        "http_get",
        url="https://api.example.com/data"
    )

    # SQL query (read-only)
    users = await ctx.call_tool(
        "sql_query",
        query="SELECT * FROM users WHERE is_active = :active",
        params={"active": True}
    )

    return AgentOutput(content=f"Got {len(users['rows'])} users")
```

## Using Cache

Store and retrieve data with the built-in cache:

```python
@agent(name="cached_agent", description="Uses caching")
async def cached_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    cache_key = f"result:{input.message}"

    # Try to get from cache
    if ctx.cache:
        cached = await ctx.cache.get(cache_key)
        if cached:
            return AgentOutput(content=cached)

    # Compute result
    result = f"Processed: {input.message}"

    # Store in cache (5 minutes)
    if ctx.cache:
        await ctx.cache.set(cache_key, result, ttl=300)

    return AgentOutput(content=result)
```

## Using Secrets

Access secrets securely:

```python
@agent(name="api_agent", description="Uses API keys")
async def api_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    # Get API key from secrets manager
    api_key = await ctx.get_secret("OPENAI_API_KEY")

    if not api_key:
        return AgentOutput(content="API key not configured")

    # Use the API key
    result = await ctx.call_tool(
        "http_get",
        url="https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {api_key}"}
    )

    return AgentOutput(content=str(result))
```

## Streaming Responses

Create streaming agents:

```python
from typing import AsyncGenerator
from agent_service.interfaces import StreamChunk
from agent_service.agent import streaming_agent, AgentContext

@streaming_agent(name="streamer", description="Streams responses")
async def streamer(
    input: AgentInput,
    ctx: AgentContext
) -> AsyncGenerator[StreamChunk, None]:
    for word in input.message.split():
        yield StreamChunk(type="text", content=f"{word} ")
        await asyncio.sleep(0.1)
```

## Tool with Type Validation

Types are automatically validated:

```python
from typing import Literal
from agent_service.tools import tool

@tool(name="calculate", description="Perform calculations")
async def calculate(
    operation: Literal["add", "subtract", "multiply", "divide"],
    a: float,
    b: float
) -> dict:
    if operation == "add":
        return {"result": a + b}
    elif operation == "subtract":
        return {"result": a - b}
    elif operation == "multiply":
        return {"result": a * b}
    else:  # divide
        return {"result": a / b}
```

## Confirmed Tools

Tools that require user confirmation:

```python
from agent_service.tools import confirmed_tool

@confirmed_tool(name="delete", description="Delete something")
async def delete(item_id: str) -> dict:
    # User will be prompted to confirm before this runs
    return {"deleted": item_id}
```

## Using the Logger

Structured logging is built-in:

```python
@agent(name="logger_example", description="Uses logging")
async def logger_example(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    ctx.logger.info("processing_started", message_length=len(input.message))

    try:
        result = process(input.message)
        ctx.logger.info("processing_completed", success=True)
        return AgentOutput(content=result)
    except Exception as e:
        ctx.logger.error("processing_failed", error=str(e))
        raise
```

## Accessing User Information

Work with authenticated users:

```python
@agent(name="user_agent", description="User-aware agent")
async def user_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    if not ctx.user:
        return AgentOutput(content="Please log in")

    # Check roles
    if ctx.user.has_role("admin"):
        return AgentOutput(content=f"Admin user: {ctx.user.name}")

    # Check groups
    if ctx.user.is_in_group("engineering"):
        return AgentOutput(content="Engineering user")

    return AgentOutput(content=f"Hello {ctx.user.name}")
```

## Running Your Agent

### From Code

```python
from agent_service.interfaces import AgentInput
from agent_service.agent import agent_registry

# Get your agent
my_agent = agent_registry.get("greeter")

# Create input
input = AgentInput(message="Hello world")

# Run it
result = await my_agent.invoke(input)
print(result.content)
```

### Via API

The agents are automatically available via the API:

```bash
curl -X POST http://localhost:8000/agents/greeter/invoke \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello world"}'
```

## File Organization

Recommended structure:

```
my_project/
├── agents/
│   ├── __init__.py
│   ├── greeter.py      # Your agents
│   └── processor.py
├── tools/
│   ├── __init__.py
│   ├── utils.py        # Your tools
│   └── apis.py
└── main.py             # Import agents & tools here
```

In `main.py`:

```python
# Import to register agents and tools
from agents import greeter, processor
from tools import utils, apis

# Now they're registered and ready to use!
```

## Testing

Test your agents and tools:

```python
import pytest
from agent_service.interfaces import AgentInput
from my_agents import greeter

@pytest.mark.asyncio
async def test_greeter():
    # Create mock context
    from agent_service.agent import AgentContext
    from agent_service.tools import tool_registry

    ctx = AgentContext(tools=tool_registry)

    # Test agent
    input = AgentInput(message="test")
    result = await greeter(input, ctx)

    assert "test" in result.content
```

## Next Steps

1. Read the [Decorator Guide](./DECORATOR_GUIDE.md) for comprehensive documentation
2. Check [Agent Examples](./agent/examples/decorator_examples.py) for more patterns
3. Check [Tool Examples](./tools/examples/decorator_examples.py) for more patterns
4. Explore [Built-in Tools](./tools/builtin/) for HTTP and SQL tools

## Common Patterns

### Error Handling

```python
@agent(name="safe_agent", description="Handles errors gracefully")
async def safe_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    try:
        result = await risky_operation(input.message)
        return AgentOutput(content=result)
    except Exception as e:
        ctx.logger.error("operation_failed", error=str(e))
        return AgentOutput(
            content=f"Sorry, an error occurred: {str(e)}",
            metadata={"error": str(e)}
        )
```

### Retry Logic

```python
@tool(name="retry_tool", description="Retries on failure")
async def retry_tool(url: str, max_retries: int = 3) -> dict:
    for attempt in range(max_retries):
        try:
            return await fetch_data(url)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(1 * (attempt + 1))
```

### Timeouts

```python
@tool(name="slow_tool", description="Has timeout", timeout=10.0)
async def slow_tool(duration: float) -> str:
    await asyncio.sleep(duration)  # Will timeout after 10 seconds
    return "Done"
```

That's it! You're ready to build powerful agents and tools with minimal boilerplate.
