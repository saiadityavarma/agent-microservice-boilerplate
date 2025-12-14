# Tool-Using Agent

A comprehensive example of an agent that uses multiple tools to accomplish tasks.

## Overview

This example demonstrates how to build agents that:
- Dynamically select and use appropriate tools
- Chain multiple tools together
- Execute tools in parallel
- Handle tool errors gracefully
- Interpret and present tool results

## Features

- **Dynamic Tool Selection**: Agent chooses the right tool based on user intent
- **Tool Chaining**: Use output from one tool as input to another
- **Parallel Execution**: Run multiple tools simultaneously
- **Error Handling**: Graceful handling of tool failures
- **Result Interpretation**: Format tool outputs for users

## Available Tools

### Calculator Tools
- `calculate` - Mathematical expressions
- `convert_units` - Unit conversions (temperature, length, weight)

### Information Tools
- `web_search` - Search the web (simulated)
- `get_current_time` - Current date and time
- `format_date` - Format dates

### File Operations
- `read_file` - Read file contents
- `write_file` - Write to files (requires confirmation)

### Data Processing
- `parse_json` - Parse JSON strings
- `format_json` - Format data as JSON
- `extract_data` - Extract fields from nested data

### Network Tools
- `http_request` - Make HTTP requests

## Files

- `agent.py` - Tool-using agent implementations
- `tools.py` - Custom tool definitions
- `README.md` - This file
- `test_tool_use.py` - Tests

## Quick Start

### 1. Basic Tool Usage

```python
import asyncio
from agent_service.interfaces import AgentInput
from agent_service.agent import agent_registry

# Import to register agents and tools
from examples.tool_use import agent, tools

async def main():
    # Get the tool agent
    tool_agent = agent_registry.get("tool_agent")

    # Calculate something
    result = await tool_agent.invoke(AgentInput(
        message="Calculate 25 * 4 + 10"
    ))
    print(result.content)
    print(f"Tools used: {result.metadata['tools_used']}")

    # Search the web
    result = await tool_agent.invoke(AgentInput(
        message="Search for Python tutorials"
    ))
    print(result.content)

asyncio.run(main())
```

### 2. Tool Chaining

Chain multiple tools together:

```python
async def chaining_example():
    chain_agent = agent_registry.get("tool_chain_agent")

    result = await chain_agent.invoke(AgentInput(
        message="Search for Python and format the results as JSON"
    ))

    print(result.content)
    print(f"Chain length: {result.metadata['chain_length']}")
    print(f"Tools: {result.metadata['tools_used']}")

asyncio.run(chaining_example())
```

### 3. Parallel Tool Execution

Run multiple tools simultaneously:

```python
async def parallel_example():
    parallel_agent = agent_registry.get("parallel_tool_agent")

    result = await parallel_agent.invoke(AgentInput(
        message="Get the current time and search for Python"
    ))

    print(result.content)
    print(f"Parallel tasks: {result.metadata['parallel_count']}")

asyncio.run(parallel_example())
```

### 4. Direct Tool Usage

Use tools directly without an agent:

```python
from agent_service.tools import tool_registry

async def direct_tool_usage():
    # Get the calculator tool
    calc_tool = tool_registry.get("calculate")

    # Execute it directly
    result = await calc_tool.execute(expression="10 * 5 + 2")

    print(f"Result: {result['result']}")

asyncio.run(direct_tool_usage())
```

## Creating Custom Tools

### Simple Tool

```python
from agent_service.tools import tool

@tool(
    name="greet",
    description="Greet a user by name"
)
async def greet(name: str, greeting: str = "Hello") -> dict:
    """Greet a user."""
    return {
        "message": f"{greeting}, {name}!",
        "success": True
    }
```

### Tool with Timeout

```python
@tool(
    name="slow_operation",
    description="A slow operation",
    timeout=10.0  # 10 second timeout
)
async def slow_operation(duration: int) -> dict:
    """Simulate a slow operation."""
    import asyncio
    await asyncio.sleep(duration)
    return {"completed": True}
```

### Confirmed Tool

Tools that require user confirmation before execution:

```python
from agent_service.tools import confirmed_tool

@confirmed_tool(
    name="delete_file",
    description="Delete a file (DANGEROUS)"
)
async def delete_file(file_path: str) -> dict:
    """Delete a file - requires confirmation."""
    import os
    os.remove(file_path)
    return {
        "deleted": file_path,
        "success": True
    }
```

### Tool with Complex Types

```python
from typing import List, Dict, Any

@tool(
    name="process_batch",
    description="Process a batch of items"
)
async def process_batch(
    items: List[str],
    options: Dict[str, Any],
    max_workers: int = 4
) -> dict:
    """Process multiple items."""
    results = []
    for item in items:
        # Process each item
        results.append(f"Processed: {item}")

    return {
        "results": results,
        "count": len(results),
        "success": True
    }
```

## Tool Patterns

### Pattern 1: Sequential Tool Chain

```python
async def sequential_chain(ctx: AgentContext):
    """Execute tools in sequence, passing data forward."""
    # Step 1: Search
    search_result = await ctx.call_tool(
        "web_search",
        query="Python tutorials"
    )

    # Step 2: Format as JSON
    formatted = await ctx.call_tool(
        "format_json",
        data=search_result
    )

    # Step 3: Save to file (if confirmed)
    # await ctx.call_tool("write_file", ...)

    return formatted
```

### Pattern 2: Parallel Execution

```python
import asyncio

async def parallel_tools(ctx: AgentContext):
    """Execute multiple tools in parallel."""
    # Create tasks
    tasks = [
        ctx.call_tool("get_current_time"),
        ctx.call_tool("web_search", query="Python"),
        ctx.call_tool("calculate", expression="10 + 20")
    ]

    # Execute in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return results
```

### Pattern 3: Conditional Tool Selection

```python
async def conditional_tools(query: str, ctx: AgentContext):
    """Select tool based on condition."""
    if "calculate" in query.lower():
        return await ctx.call_tool("calculate", expression="...")

    elif "search" in query.lower():
        return await ctx.call_tool("web_search", query="...")

    else:
        return {"message": "No matching tool found"}
```

### Pattern 4: Retry on Failure

```python
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
async def resilient_tool_call(ctx: AgentContext):
    """Tool call with automatic retry."""
    return await ctx.call_tool("web_search", query="...")
```

### Pattern 5: Tool Result Validation

```python
async def validated_tool_call(ctx: AgentContext):
    """Call tool and validate result."""
    result = await ctx.call_tool("calculate", expression="10 / 2")

    # Validate result
    if not result.get("success"):
        raise ValueError(f"Tool failed: {result.get('error')}")

    if result["result"] <= 0:
        raise ValueError("Result must be positive")

    return result
```

## Advanced Examples

### Custom Tool-Using Agent

Create your own tool-using agent with custom logic:

```python
from agent_service.agent import agent, AgentContext
from agent_service.interfaces import AgentInput, AgentOutput

@agent(name="smart_assistant")
async def smart_assistant(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    """Smart assistant that intelligently uses tools."""
    query = input.message

    # Use NLP or LLM to understand intent
    intent = analyze_intent(query)  # Your intent detection

    # Route to appropriate tools
    if intent == "calculation":
        result = await ctx.call_tool("calculate", expression=extract_math(query))
    elif intent == "information":
        result = await ctx.call_tool("web_search", query=query)
    else:
        result = {"message": "I'm not sure how to help with that"}

    return AgentOutput(content=format_result(result))
```

### Tool with External API

Integrate with real external APIs:

```python
import httpx
from agent_service.tools import tool

@tool(name="github_repo_info", timeout=10.0)
async def github_repo_info(repo: str) -> dict:
    """Get GitHub repository information.

    Args:
        repo: Repository in format "owner/repo"

    Returns:
        Repository information
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/repos/{repo}",
            headers={"Accept": "application/vnd.github.v3+json"}
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "name": data["name"],
                "description": data["description"],
                "stars": data["stargazers_count"],
                "forks": data["forks_count"],
                "language": data["language"],
                "success": True
            }
        else:
            return {
                "error": f"API returned {response.status_code}",
                "success": False
            }
```

### Tool with Database Access

Tools can access the database through context:

```python
@tool(name="get_user_data")
async def get_user_data(user_id: int, ctx: AgentContext) -> dict:
    """Get user data from database."""
    # Access database through context
    if ctx.db:
        async with ctx.db.session() as session:
            user = await session.get(User, user_id)
            if user:
                return {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "success": True
                }

    return {"error": "User not found", "success": False}
```

### Tool with Caching

Cache expensive tool results:

```python
@tool(name="expensive_computation", timeout=60.0)
async def expensive_computation(input_data: str, ctx: AgentContext) -> dict:
    """Expensive computation with caching."""
    # Check cache
    cache_key = f"computation:{hash(input_data)}"

    if ctx.cache:
        cached = await ctx.cache.get(cache_key)
        if cached:
            return {
                "result": cached,
                "cached": True,
                "success": True
            }

    # Perform expensive computation
    import asyncio
    await asyncio.sleep(5)  # Simulate work
    result = f"Processed: {input_data}"

    # Cache result
    if ctx.cache:
        await ctx.cache.set(cache_key, result, ttl=3600)

    return {
        "result": result,
        "cached": False,
        "success": True
    }
```

## Testing

Run the test suite:

```bash
pytest examples/tool-use/test_tool_use.py -v
```

Test specific functionality:

```bash
# Test tools only
pytest examples/tool-use/test_tool_use.py::TestTools -v

# Test agents only
pytest examples/tool-use/test_tool_use.py::TestToolAgents -v
```

## Production Considerations

### 1. Security

- **Input Validation**: Always validate tool inputs
- **Path Sanitization**: For file operations, sanitize paths
- **API Key Management**: Store API keys in secrets, not code
- **Rate Limiting**: Add rate limits to prevent abuse
- **Confirmation Required**: Use `@confirmed_tool` for dangerous operations

```python
@confirmed_tool(name="execute_command")
async def execute_command(command: str) -> dict:
    """Execute system command - requires confirmation."""
    # Whitelist allowed commands
    allowed = ["ls", "pwd", "whoami"]
    cmd = command.split()[0]

    if cmd not in allowed:
        return {"error": "Command not allowed", "success": False}

    # Execute safely
    import subprocess
    result = subprocess.run(command, shell=True, capture_output=True)
    return {"output": result.stdout.decode(), "success": True}
```

### 2. Error Handling

```python
@tool(name="resilient_api_call")
async def resilient_api_call(url: str) -> dict:
    """API call with comprehensive error handling."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            return {"data": response.json(), "success": True}

    except httpx.TimeoutError:
        return {"error": "Request timed out", "success": False}

    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP {e.response.status_code}", "success": False}

    except Exception as e:
        return {"error": str(e), "success": False}
```

### 3. Monitoring

Track tool usage and performance:

```python
@tool(name="monitored_tool")
async def monitored_tool(data: str, ctx: AgentContext) -> dict:
    """Tool with comprehensive monitoring."""
    import time

    start = time.time()
    ctx.logger.info("tool_started", tool="monitored_tool")

    try:
        # Tool logic
        result = process_data(data)

        duration = time.time() - start
        ctx.logger.info(
            "tool_completed",
            tool="monitored_tool",
            duration=duration,
            success=True
        )

        return {"result": result, "success": True}

    except Exception as e:
        duration = time.time() - start
        ctx.logger.error(
            "tool_failed",
            tool="monitored_tool",
            duration=duration,
            error=str(e)
        )
        raise
```

### 4. Cost Management

For paid API tools, track and limit costs:

```python
@tool(name="paid_api_call")
async def paid_api_call(query: str, ctx: AgentContext) -> dict:
    """Tool that calls paid API with cost tracking."""
    # Check budget
    if ctx.cache:
        spent = await ctx.cache.get("api_cost_today") or 0
        budget = 10.00  # $10 daily budget

        if spent >= budget:
            return {
                "error": "Daily budget exceeded",
                "success": False,
                "cost": spent
            }

    # Make API call
    result = await call_paid_api(query)
    cost = estimate_cost(result)

    # Update spent amount
    if ctx.cache:
        new_spent = spent + cost
        await ctx.cache.set("api_cost_today", new_spent, ttl=86400)

    return {
        "result": result,
        "cost": cost,
        "total_spent": spent + cost,
        "success": True
    }
```

## Next Steps

- Add more specialized tools for your domain
- Integrate with real external APIs
- Implement tool versioning
- Build tool marketplace/registry
- Add tool usage analytics
- Implement tool recommendations based on context

## Related Examples

- `chatbot/` - Add tools to chatbot for enhanced capabilities
- `rag-agent/` - Combine RAG with tool usage
- `multi-agent/` - Use tools in multi-agent systems
