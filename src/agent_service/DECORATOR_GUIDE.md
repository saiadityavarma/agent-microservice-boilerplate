# Agent and Tool Decorator Guide

This guide explains how to use the easy-to-use decorator system for creating agents and tools without implementing full interfaces.

## Table of Contents

1. [Agent Decorators](#agent-decorators)
2. [Tool Decorators](#tool-decorators)
3. [Agent Context](#agent-context)
4. [Built-in Tools](#built-in-tools)
5. [Complete Examples](#complete-examples)

---

## Agent Decorators

### Basic Agent

Create an agent by decorating an async function:

```python
from agent_service.interfaces import AgentInput, AgentOutput
from agent_service.agent.context import AgentContext
from agent_service.agent.decorators import agent

@agent(name="my_agent", description="Does something useful")
async def my_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    # Your agent logic here
    result = await ctx.call_tool("echo", message=input.message)
    return AgentOutput(content=str(result))
```

**Features:**
- Automatically registered with `agent_registry`
- Access to full context (tools, db, cache, logger, user)
- Automatic error handling and metrics
- Support for streaming

### Streaming Agent

For agents that stream responses:

```python
from typing import AsyncGenerator
from agent_service.interfaces import StreamChunk
from agent_service.agent.decorators import streaming_agent

@streaming_agent(name="chat", description="Streaming chat agent")
async def chat(
    input: AgentInput,
    ctx: AgentContext
) -> AsyncGenerator[StreamChunk, None]:
    for word in input.message.split():
        yield StreamChunk(type="text", content=f"{word} ")
        await asyncio.sleep(0.1)
```

### Decorator Parameters

- `name` (str, optional): Agent name (defaults to function name)
- `description` (str, optional): Description (defaults to docstring)
- `auto_register` (bool): Auto-register with registry (default: True)

### Manual Registration

If you set `auto_register=False`:

```python
@agent(name="my_agent", auto_register=False)
async def my_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    return AgentOutput(content="Hello")

# Manually register later
from agent_service.agent.registry import agent_registry
agent_registry.register(my_agent, default=True)
```

---

## Tool Decorators

### Basic Tool

Create a tool by decorating an async function:

```python
from agent_service.tools.decorators import tool

@tool(name="web_search", description="Search the web")
async def web_search(query: str, max_results: int = 10) -> list[dict]:
    # Your tool logic here
    return [{"title": "Result 1", "url": "http://..."}]
```

**Features:**
- Automatically registered with `tool_registry`
- Schema auto-generated from function signature
- Type validation from annotations
- Timeout handling

### Type Annotations

The decorator uses type annotations to generate the JSON schema:

```python
@tool(name="calculate", description="Perform calculations")
async def calculate(
    operation: Literal["add", "subtract", "multiply", "divide"],
    a: float,
    b: float,
) -> dict[str, Any]:
    # Schema automatically includes:
    # - operation: enum with 4 choices
    # - a: number (required)
    # - b: number (required)
    if operation == "add":
        return {"result": a + b}
    # ... etc
```

### Confirmed Tools

Tools that require user confirmation:

```python
from agent_service.tools.decorators import confirmed_tool

@confirmed_tool(name="delete_file", description="Delete a file")
async def delete_file(path: str) -> dict:
    # This will require user confirmation before execution
    os.remove(path)
    return {"deleted": path}
```

### Tool Parameters

- `name` (str, optional): Tool name (defaults to function name)
- `description` (str, optional): Description (defaults to docstring)
- `requires_confirmation` (bool): Require user confirmation (default: False)
- `timeout` (float, optional): Timeout in seconds (None = no timeout)
- `auto_register` (bool): Auto-register with registry (default: True)

### Timeout Example

```python
@tool(name="slow_task", description="Long running task", timeout=30.0)
async def slow_task(duration: float) -> str:
    await asyncio.sleep(duration)  # Will timeout after 30 seconds
    return "Done"
```

---

## Agent Context

The `AgentContext` provides access to all infrastructure:

### Properties

```python
@agent(name="example")
async def example(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    # Access tools
    tools = ctx.tools  # ToolRegistry

    # Access database session
    db = ctx.db  # AsyncSession | None

    # Access cache
    cache = ctx.cache  # ICache | None

    # Access logger
    logger = ctx.logger  # BoundLogger

    # Access user info
    user = ctx.user  # UserInfo | None

    # Access request ID
    request_id = ctx.request_id  # str | None

    # Access settings
    settings = ctx.settings  # Settings
```

### Methods

#### Call a Tool

```python
result = await ctx.call_tool("web_search", query="Python", max_results=5)
```

#### Get Secrets

```python
api_key = await ctx.get_secret("OPENAI_API_KEY")
db_config = await ctx.get_secret_json("DATABASE_CONFIG")
```

#### Check Permissions

```python
if ctx.has_permission("admin"):
    # Do admin stuff
    pass

# Or require permission (raises PermissionError)
ctx.require_permission("admin")
```

#### Bind Logger Context

```python
ctx.bind_logger(session_id="abc123", user_id=str(ctx.user.id))
ctx.logger.info("event")  # Will include session_id and user_id
```

### User Info

```python
if ctx.user:
    print(f"User: {ctx.user.name} ({ctx.user.email})")
    print(f"Roles: {ctx.user.roles}")
    print(f"Groups: {ctx.user.groups}")

    if ctx.user.has_role("admin"):
        # Admin actions
        pass

    if ctx.user.is_in_group("engineering"):
        # Engineering actions
        pass
```

---

## Built-in Tools

### HTTP Tools

```python
from agent_service.tools.builtin import (
    http_get,
    http_post,
    http_put,
    http_delete,
    http_request,
)

# Use in an agent
result = await ctx.call_tool(
    "http_get",
    url="https://api.example.com/data",
    headers={"Authorization": "Bearer token"},
    params={"page": "1"}
)
```

**Available HTTP tools:**
- `http_get` - GET requests
- `http_post` - POST requests (requires confirmation)
- `http_put` - PUT requests (requires confirmation)
- `http_delete` - DELETE requests (requires confirmation)
- `http_request` - Any HTTP method (requires confirmation)

### SQL Tools

```python
from agent_service.tools.builtin import (
    sql_query,
    sql_execute,
    sql_query_one,
    sql_query_scalar,
)

# Read-only query
result = await ctx.call_tool(
    "sql_query",
    query="SELECT * FROM users WHERE email = :email",
    params={"email": "john@example.com"},
    limit=10
)
# Returns: {"row_count": 1, "rows": [...], "columns": [...]}

# Single row
user = await ctx.call_tool(
    "sql_query_one",
    query="SELECT * FROM users WHERE id = :id",
    params={"id": 1}
)
# Returns: {"id": 1, "email": "...", "name": "..."}

# Scalar value
count = await ctx.call_tool(
    "sql_query_scalar",
    query="SELECT COUNT(*) FROM users WHERE is_active = :active",
    params={"active": True}
)
# Returns: 42

# Write operation (requires confirmation)
result = await ctx.call_tool(
    "sql_execute",
    query="UPDATE users SET name = :name WHERE id = :id",
    params={"name": "John Updated", "id": 1}
)
# Returns: {"rows_affected": 1, "success": True}
```

**Safety Features:**
- `sql_query` only allows SELECT statements
- Dangerous keywords (INSERT, UPDATE, DELETE, DROP, etc.) are blocked
- All queries use parameterized queries (prevents SQL injection)
- `sql_execute` requires user confirmation

---

## Complete Examples

### Example 1: Simple Echo Agent

```python
@agent(name="echo", description="Echoes the input")
async def echo(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    return AgentOutput(content=f"You said: {input.message}")
```

### Example 2: Agent with Cache

```python
@agent(name="cached_agent", description="Uses caching")
async def cached_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    cache_key = f"result:{input.message}"

    # Check cache
    if ctx.cache:
        cached = await ctx.cache.get(cache_key)
        if cached:
            return AgentOutput(content=cached, metadata={"cached": True})

    # Compute result
    result = f"Processed: {input.message}"

    # Store in cache
    if ctx.cache:
        await ctx.cache.set(cache_key, result, ttl=300)

    return AgentOutput(content=result, metadata={"cached": False})
```

### Example 3: Agent with Database

```python
@agent(name="user_count", description="Count active users")
async def user_count(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    count = await ctx.call_tool(
        "sql_query_scalar",
        query="SELECT COUNT(*) FROM users WHERE is_active = :active",
        params={"active": True}
    )

    return AgentOutput(content=f"Active users: {count}")
```

### Example 4: Agent with External API

```python
@agent(name="weather", description="Get weather information")
async def weather(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    # Get API key from secrets
    api_key = await ctx.get_secret("WEATHER_API_KEY")

    if not api_key:
        return AgentOutput(content="API key not configured")

    # Call external API
    result = await ctx.call_tool(
        "http_get",
        url=f"https://api.weather.com/location/{input.message}",
        headers={"Authorization": f"Bearer {api_key}"}
    )

    return AgentOutput(content=f"Weather: {result}")
```

### Example 5: Streaming Agent

```python
@streaming_agent(name="streamer", description="Streams responses")
async def streamer(
    input: AgentInput,
    ctx: AgentContext
) -> AsyncGenerator[StreamChunk, None]:
    words = input.message.split()

    for i, word in enumerate(words):
        yield StreamChunk(
            type="text",
            content=f"{word} ",
            metadata={"index": i}
        )
        await asyncio.sleep(0.1)

    yield StreamChunk(type="text", content="\n[Done]")
```

### Example 6: Custom Tool

```python
@tool(name="sentiment", description="Analyze sentiment of text")
async def sentiment(text: str) -> dict[str, Any]:
    # Simple sentiment analysis (placeholder)
    score = 0.5  # Would use actual ML model

    return {
        "text": text,
        "score": score,
        "sentiment": "positive" if score > 0.5 else "negative"
    }
```

### Example 7: Tool with Complex Types

```python
@tool(name="process_batch", description="Process batch of items")
async def process_batch(
    items: list[str],
    config: dict[str, Any] | None = None
) -> dict[str, Any]:
    config = config or {}
    uppercase = config.get("uppercase", False)

    processed = [item.upper() if uppercase else item for item in items]

    return {
        "original_count": len(items),
        "processed_count": len(processed),
        "items": processed
    }
```

---

## Best Practices

### 1. Use Type Annotations

Always use type annotations - they're used to generate tool schemas:

```python
@tool(name="example")
async def example(
    name: str,                          # Required string
    age: int = 0,                       # Optional int with default
    tags: list[str] | None = None,      # Optional list
    config: dict[str, Any] | None = None # Optional dict
) -> dict[str, Any]:                    # Return type
    pass
```

### 2. Log Appropriately

Use the context logger for structured logging:

```python
@agent(name="example")
async def example(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    ctx.logger.info("processing_started", message_length=len(input.message))

    try:
        result = await process(input.message)
        ctx.logger.info("processing_completed", success=True)
        return AgentOutput(content=result)
    except Exception as e:
        ctx.logger.error("processing_failed", error=str(e))
        raise
```

### 3. Handle Errors Gracefully

Always handle errors and return meaningful messages:

```python
@agent(name="example")
async def example(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    try:
        result = await ctx.call_tool("risky_tool", data=input.message)
        return AgentOutput(content=result)
    except Exception as e:
        return AgentOutput(
            content=f"Operation failed: {str(e)}",
            metadata={"error": str(e), "success": False}
        )
```

### 4. Use Caching for Expensive Operations

```python
@agent(name="expensive")
async def expensive(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    cache_key = f"expensive:{input.message}"

    if ctx.cache:
        cached = await ctx.cache.get(cache_key)
        if cached:
            return AgentOutput(content=cached, metadata={"cached": True})

    # Expensive operation
    result = await expensive_operation(input.message)

    if ctx.cache:
        await ctx.cache.set(cache_key, result, ttl=3600)

    return AgentOutput(content=result)
```

### 5. Validate Permissions

```python
@agent(name="admin_action")
async def admin_action(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    # Require admin role
    try:
        ctx.require_permission("admin")
    except PermissionError:
        return AgentOutput(content="Admin access required")

    # Perform admin action
    result = await do_admin_stuff()
    return AgentOutput(content=result)
```

---

## Registry Access

### Agent Registry

```python
from agent_service.agent.registry import agent_registry

# List all agents
agents = agent_registry.list_agents()
print(agents)  # ['echo', 'search', 'chat', ...]

# Get agent by name
agent = agent_registry.get("echo")

# Get default agent
default = agent_registry.get_default()

# Set default agent
agent_registry.set_default("chat")

# Unregister agent
agent_registry.unregister("old_agent")
```

### Tool Registry

```python
from agent_service.tools.registry import tool_registry

# List all tools
tools = tool_registry.list_tools()

# Get tool by name
tool = tool_registry.get("web_search")

# Execute tool directly
result = await tool_registry.execute("web_search", query="Python")

# Export for OpenAI
openai_tools = tool_registry.to_openai_format()

# Export for Anthropic
anthropic_tools = tool_registry.to_anthropic_format()

# Unregister tool
tool_registry.unregister("old_tool")
```

---

## Testing

### Testing Agents

```python
import pytest
from agent_service.interfaces import AgentInput
from agent_service.agent.context import AgentContext

@pytest.mark.asyncio
async def test_my_agent():
    # Create input
    input = AgentInput(message="test message")

    # Create context (mock if needed)
    ctx = create_test_context()

    # Call agent
    result = await my_agent(input, ctx)

    # Assert
    assert result.content == "expected output"
```

### Testing Tools

```python
@pytest.mark.asyncio
async def test_my_tool():
    result = await my_tool.execute(arg1="value1", arg2="value2")
    assert result["success"] == True
```

---

## Migration from Class-based Approach

### Old Way (Class-based)

```python
class MyAgent(IAgent):
    @property
    def name(self) -> str:
        return "my_agent"

    @property
    def description(self) -> str:
        return "My agent"

    async def invoke(self, input: AgentInput) -> AgentOutput:
        return AgentOutput(content=input.message)

    async def stream(self, input: AgentInput) -> AsyncGenerator[StreamChunk, None]:
        yield StreamChunk(type="text", content=input.message)

# Register
agent_registry.register(MyAgent())
```

### New Way (Decorator-based)

```python
@agent(name="my_agent", description="My agent")
async def my_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    return AgentOutput(content=input.message)

# Auto-registered!
```

**Benefits:**
- 70% less boilerplate
- Automatic context creation
- Built-in error handling and metrics
- Type safety
- Easier to test
