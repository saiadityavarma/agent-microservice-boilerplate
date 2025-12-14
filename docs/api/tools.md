# Tool System Reference

Complete guide to the tool system for agent function calling.

## Overview

Tools are functions that agents can call to perform specific tasks:
- Fetch external data (APIs, databases)
- Perform calculations
- Execute actions (send emails, create tickets)
- Interact with systems

## Tool Interface

All tools implement the `ITool` interface:

```python
from agent_service.interfaces import ITool, ToolSchema

class ITool(ABC):
    @property
    def schema(self) -> ToolSchema:
        """Return tool schema for LLM function calling"""

    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given arguments"""

    @property
    def requires_confirmation(self) -> bool:
        """Override to require human confirmation"""
        return False
```

## Creating a Tool

### Step 1: Create Tool File

```bash
touch src/agent_service/tools/custom/weather_tool.py
```

### Step 2: Implement the Tool

```python
# src/agent_service/tools/custom/weather_tool.py
"""Weather information tool."""
from typing import Any
from agent_service.interfaces import ITool, ToolSchema
import httpx


class WeatherTool(ITool):
    """Fetches weather information for a location."""

    @property
    def schema(self) -> ToolSchema:
        """Return JSON Schema for this tool."""
        return ToolSchema(
            name="get_weather",
            description="Get current weather information for a specific location",
            parameters={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name or coordinates (e.g., 'London' or '51.5074,-0.1278')"
                    },
                    "units": {
                        "type": "string",
                        "enum": ["metric", "imperial"],
                        "description": "Temperature units (metric=Celsius, imperial=Fahrenheit)",
                        "default": "metric"
                    }
                },
                "required": ["location"]
            }
        )

    async def execute(self, location: str, units: str = "metric", **kwargs) -> Any:
        """
        Execute weather lookup.

        Args:
            location: City name or coordinates
            units: Temperature units (metric or imperial)

        Returns:
            Weather data dictionary
        """
        # Use free weather API (wttr.in)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://wttr.in/{location}?format=j1",
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()

        # Parse response
        current = data.get("current_condition", [{}])[0]

        return {
            "location": location,
            "temperature": current.get("temp_C") if units == "metric" else current.get("temp_F"),
            "units": "°C" if units == "metric" else "°F",
            "condition": current.get("weatherDesc", [{}])[0].get("value", "Unknown"),
            "humidity": current.get("humidity"),
            "wind_speed": current.get("windspeedKmph"),
            "feels_like": current.get("FeelsLikeC") if units == "metric" else current.get("FeelsLikeF")
        }

    @property
    def requires_confirmation(self) -> bool:
        """Weather lookups don't need confirmation."""
        return False
```

### Step 3: Test the Tool

```python
# test_weather_tool.py
import asyncio
from src.agent_service.tools.custom.weather_tool import WeatherTool


async def test():
    tool = WeatherTool()

    # Test execution
    result = await tool.execute(location="London", units="metric")
    print(f"Weather: {result}")

    # Test schema
    schema = tool.schema
    print(f"Schema: {schema.model_dump()}")


if __name__ == "__main__":
    asyncio.run(test())
```

### Step 4: Use in Agent

Tools are automatically discovered from `src/agent_service/tools/custom/`:

```python
# src/agent_service/agent/custom/my_agent.py
from agent_service.tools.custom.weather_tool import WeatherTool

class MyAgent(IAgent):
    def __init__(self):
        self.weather_tool = WeatherTool()

    async def invoke(self, input: AgentInput) -> AgentOutput:
        # Use tool in LLM function calling
        tools = [self.weather_tool.schema.model_dump()]

        # ... rest of agent implementation
```

## Built-in Tools

### HTTP Request Tool

Make HTTP requests:

```python
from agent_service.tools.examples.http_request import HTTPRequestTool

tool = HTTPRequestTool()

# GET request
result = await tool.execute(
    url="https://api.example.com/data",
    method="GET",
    headers={"Authorization": "Bearer token"}
)

# POST request
result = await tool.execute(
    url="https://api.example.com/data",
    method="POST",
    headers={"Content-Type": "application/json"},
    body={"key": "value"}
)
```

### Echo Tool

Simple echo tool for testing:

```python
from agent_service.tools.examples.echo import EchoTool

tool = EchoTool()
result = await tool.execute(message="Hello, World!")
# Returns: {"echo": "Hello, World!"}
```

## Advanced Tool Patterns

### Tool with Confirmation

For destructive or sensitive operations:

```python
class DeleteUserTool(ITool):
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="delete_user",
            description="Delete a user account (requires confirmation)",
            parameters={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"}
                },
                "required": ["user_id"]
            }
        )

    async def execute(self, user_id: str, **kwargs) -> Any:
        # Check if confirmation was provided
        if not kwargs.get("confirmed", False):
            return {
                "status": "pending_confirmation",
                "message": f"Are you sure you want to delete user {user_id}?",
                "confirmation_required": True
            }

        # Execute deletion
        # ... deletion logic ...

        return {
            "status": "deleted",
            "user_id": user_id
        }

    @property
    def requires_confirmation(self) -> bool:
        return True
```

### Tool with Rate Limiting

```python
from agent_service.api.middleware.rate_limit import RateLimiter

class RateLimitedAPITool(ITool):
    def __init__(self):
        self.rate_limiter = RateLimiter(max_requests=10, window=60)

    async def execute(self, **kwargs) -> Any:
        # Check rate limit
        key = f"tool:api_call:{kwargs.get('endpoint')}"
        if not await self.rate_limiter.check(key):
            raise Exception("Rate limit exceeded for this API endpoint")

        # Execute tool
        # ...
```

### Tool with Caching

```python
from agent_service.infrastructure.cache import RedisCache

class CachedDataTool(ITool):
    def __init__(self):
        self.cache = RedisCache()

    async def execute(self, query: str, **kwargs) -> Any:
        # Check cache
        cache_key = f"tool:data:{query}"
        cached = await self.cache.get(cache_key)

        if cached:
            return {"data": cached, "cached": True}

        # Fetch data
        data = await self._fetch_data(query)

        # Cache result (5 minutes)
        await self.cache.set(cache_key, data, ttl=300)

        return {"data": data, "cached": False}

    async def _fetch_data(self, query: str) -> Any:
        # ... fetch logic ...
        pass
```

### Tool with Authentication

```python
class AuthenticatedAPITool(ITool):
    def __init__(self, api_key: str):
        self.api_key = api_key

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="fetch_user_data",
            description="Fetch user data from authenticated API",
            parameters={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"}
                },
                "required": ["user_id"]
            }
        )

    async def execute(self, user_id: str, **kwargs) -> Any:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.example.com/users/{user_id}",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            response.raise_for_status()
            return response.json()
```

### Database Query Tool

```python
from agent_service.infrastructure.database import get_db

class DatabaseQueryTool(ITool):
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="query_database",
            description="Execute a SQL query (read-only)",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL SELECT query"
                    }
                },
                "required": ["query"]
            }
        )

    async def execute(self, query: str, **kwargs) -> Any:
        # Validate query is SELECT only
        if not query.strip().upper().startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed")

        async with get_db() as db:
            result = await db.execute(query)
            rows = result.fetchall()

        return {
            "rows": [dict(row) for row in rows],
            "count": len(rows)
        }

    @property
    def requires_confirmation(self) -> bool:
        return True  # SQL queries should be confirmed
```

## Tool Registration

### Automatic Discovery

Tools in `src/agent_service/tools/custom/` are automatically discovered.

### Manual Registration

```python
# src/agent_service/tools/registry.py
from agent_service.tools.custom.my_tool import MyTool

class ToolRegistry:
    def __init__(self):
        self._tools = {}
        self._register_tools()

    def _register_tools(self):
        # Manual registration
        self.register(MyTool())

    def register(self, tool: ITool):
        self._tools[tool.schema.name] = tool

    def get(self, name: str) -> ITool:
        return self._tools.get(name)

    def list_all(self) -> list[ITool]:
        return list(self._tools.values())
```

## Tool Testing

### Unit Tests

```python
# tests/unit/tools/test_weather_tool.py
import pytest
from unittest.mock import AsyncMock, patch
from agent_service.tools.custom.weather_tool import WeatherTool


@pytest.fixture
def weather_tool():
    return WeatherTool()


@pytest.mark.asyncio
async def test_weather_tool_schema(weather_tool):
    """Test tool schema is valid."""
    schema = weather_tool.schema

    assert schema.name == "get_weather"
    assert "location" in schema.parameters["properties"]
    assert "location" in schema.parameters["required"]


@pytest.mark.asyncio
async def test_weather_tool_execute(weather_tool):
    """Test tool execution."""
    with patch('httpx.AsyncClient.get') as mock_get:
        # Mock API response
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "current_condition": [{
                "temp_C": "15",
                "temp_F": "59",
                "weatherDesc": [{"value": "Partly cloudy"}],
                "humidity": "65",
                "windspeedKmph": "10"
            }]
        }
        mock_get.return_value = mock_response

        # Execute tool
        result = await weather_tool.execute(location="London")

        assert result["location"] == "London"
        assert result["temperature"] == "15"
        assert result["condition"] == "Partly cloudy"


@pytest.mark.asyncio
async def test_weather_tool_error_handling(weather_tool):
    """Test tool error handling."""
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.side_effect = httpx.HTTPError("API error")

        with pytest.raises(httpx.HTTPError):
            await weather_tool.execute(location="InvalidCity")
```

### Integration Tests

```python
# tests/integration/tools/test_weather_tool_integration.py
import pytest
from agent_service.tools.custom.weather_tool import WeatherTool


@pytest.mark.asyncio
@pytest.mark.integration
async def test_weather_tool_real_api():
    """Test with real API (requires internet)."""
    tool = WeatherTool()

    result = await tool.execute(location="London", units="metric")

    assert "temperature" in result
    assert "condition" in result
    assert result["units"] == "°C"
```

## Tool Security

### Input Validation

```python
class SecureFileTool(ITool):
    ALLOWED_PATHS = ["/safe/path1", "/safe/path2"]

    async def execute(self, filepath: str, **kwargs) -> Any:
        # Validate path
        import os
        abs_path = os.path.abspath(filepath)

        if not any(abs_path.startswith(allowed) for allowed in self.ALLOWED_PATHS):
            raise ValueError(f"Access to path {filepath} is not allowed")

        # Path traversal protection
        if ".." in filepath or filepath.startswith("/"):
            raise ValueError("Invalid file path")

        # Proceed with execution
        # ...
```

### Sanitization

```python
from agent_service.api.validators.sanitizers import sanitize_sql, sanitize_path

class SecureDatabaseTool(ITool):
    async def execute(self, table: str, **kwargs) -> Any:
        # Sanitize table name
        table = sanitize_sql(table)

        # Use parameterized query
        query = "SELECT * FROM ? WHERE active = ?"
        # ...
```

### Rate Limiting

```python
class RateLimitedTool(ITool):
    MAX_CALLS_PER_MINUTE = 10

    def __init__(self):
        self._calls = {}

    async def execute(self, **kwargs) -> Any:
        # Implement rate limiting
        import time
        current_minute = int(time.time() / 60)
        key = f"{current_minute}"

        if self._calls.get(key, 0) >= self.MAX_CALLS_PER_MINUTE:
            raise Exception("Rate limit exceeded")

        self._calls[key] = self._calls.get(key, 0) + 1

        # Execute tool
        # ...
```

## Error Handling

### Standard Error Handling

```python
from agent_service.domain.exceptions import ToolExecutionError

class MyTool(ITool):
    async def execute(self, **kwargs) -> Any:
        try:
            # Tool logic
            result = await self._do_work(**kwargs)
            return result

        except httpx.HTTPError as e:
            raise ToolExecutionError(f"API request failed: {str(e)}")

        except ValueError as e:
            raise ToolExecutionError(f"Invalid input: {str(e)}")

        except Exception as e:
            # Log unexpected errors
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Tool execution failed: {str(e)}", exc_info=True)

            raise ToolExecutionError(f"Tool execution failed: {str(e)}")
```

### Graceful Degradation

```python
class ResilientTool(ITool):
    async def execute(self, **kwargs) -> Any:
        try:
            # Try primary source
            return await self._fetch_from_primary(**kwargs)

        except Exception as e:
            # Log error
            logger.warning(f"Primary source failed: {e}")

            try:
                # Fallback to secondary source
                return await self._fetch_from_fallback(**kwargs)

            except Exception as fallback_error:
                # Return error response instead of raising
                return {
                    "error": "Service temporarily unavailable",
                    "details": str(fallback_error),
                    "fallback_attempted": True
                }
```

## Tool Observability

### Logging

```python
from agent_service.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

class ObservableTool(ITool):
    async def execute(self, **kwargs) -> Any:
        logger.info(f"Executing tool {self.schema.name}", extra={
            "tool": self.schema.name,
            "args": kwargs
        })

        try:
            result = await self._do_work(**kwargs)

            logger.info(f"Tool execution successful", extra={
                "tool": self.schema.name,
                "result_size": len(str(result))
            })

            return result

        except Exception as e:
            logger.error(f"Tool execution failed", extra={
                "tool": self.schema.name,
                "error": str(e)
            }, exc_info=True)
            raise
```

### Tracing

```python
from agent_service.infrastructure.observability.tracing import trace_async

class TracedTool(ITool):
    @trace_async(span_name="weather_tool.execute")
    async def execute(self, location: str, **kwargs) -> Any:
        # Execution is automatically traced
        result = await self._fetch_weather(location)
        return result
```

### Metrics

```python
from agent_service.infrastructure.observability.metrics import metrics

class MeteredTool(ITool):
    async def execute(self, **kwargs) -> Any:
        # Increment invocation counter
        metrics.increment("tool.invocations", tags={
            "tool": self.schema.name
        })

        import time
        start = time.time()

        try:
            result = await self._do_work(**kwargs)

            # Record success
            metrics.increment("tool.success", tags={
                "tool": self.schema.name
            })

            return result

        except Exception as e:
            # Record failure
            metrics.increment("tool.errors", tags={
                "tool": self.schema.name,
                "error_type": type(e).__name__
            })
            raise

        finally:
            # Record duration
            duration = time.time() - start
            metrics.histogram("tool.duration", duration, tags={
                "tool": self.schema.name
            })
```

## Best Practices

1. **Clear Descriptions**: Make tool descriptions clear for LLM understanding
2. **Type Validation**: Use Pydantic for parameter validation
3. **Error Handling**: Always handle and log errors gracefully
4. **Idempotency**: Make tools idempotent when possible
5. **Rate Limiting**: Protect external APIs with rate limiting
6. **Caching**: Cache responses when appropriate
7. **Timeouts**: Set reasonable timeouts for external calls
8. **Security**: Validate and sanitize all inputs
9. **Observability**: Add logging, tracing, and metrics
10. **Testing**: Write comprehensive unit and integration tests

## Examples

See `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/examples/tools/` for complete examples:

- `weather_tool.py` - Weather API integration
- `database_tool.py` - Database queries
- `email_tool.py` - Email sending
- `slack_tool.py` - Slack integration
- `github_tool.py` - GitHub API integration

## Next Steps

- [Protocol Guide](./protocols.md) - Implement MCP, A2A, AG-UI
- [Agent API](./agents.md) - Use tools in agents
- [Authentication](./authentication.md) - Secure tool access
