# Build Your First Agent

Step-by-step tutorial for creating a custom agent using the `@agent` decorator pattern.

## What You'll Build

A weather agent that:
- Uses the `@agent` decorator for automatic registration
- Integrates with a weather API tool
- Supports both synchronous and streaming responses
- Includes proper error handling

## Prerequisites

- Agent service running (see [Quick Start](./quickstart.md))
- Basic Python knowledge
- OpenAI API key (or another LLM provider)

## Step 1: Understand the Agent Interface

All agents implement the `IAgent` interface:

```python
from agent_service.interfaces import IAgent, AgentInput, AgentOutput, StreamChunk

class IAgent(ABC):
    @property
    def name(self) -> str:
        """Unique identifier"""

    @property
    def description(self) -> str:
        """Human-readable description"""

    async def invoke(self, input: AgentInput) -> AgentOutput:
        """Synchronous execution"""

    async def stream(self, input: AgentInput) -> AsyncGenerator[StreamChunk, None]:
        """Streaming execution"""
```

## Step 2: Create Your Agent File

Create a new file for your agent:

```bash
# Create the file
touch src/agent_service/agent/custom/weather_agent.py
```

The `agent/custom/` directory is automatically scanned for agents.

## Step 3: Implement the Agent

```python
# src/agent_service/agent/custom/weather_agent.py
"""
Weather agent that provides weather information using an LLM and tools.
"""
from typing import AsyncGenerator
from openai import AsyncOpenAI

from agent_service.interfaces import IAgent, AgentInput, AgentOutput, StreamChunk
from agent_service.tools.examples.http_request import HTTPRequestTool


class WeatherAgent(IAgent):
    """
    Agent that provides weather information.

    Uses OpenAI's function calling to determine when to fetch weather data.
    """

    def __init__(self):
        self.client = AsyncOpenAI()
        self.model = "gpt-4o-mini"
        self.http_tool = HTTPRequestTool()

    @property
    def name(self) -> str:
        return "weather-agent"

    @property
    def description(self) -> str:
        return "Provides weather information for any location"

    async def invoke(self, input: AgentInput) -> AgentOutput:
        """
        Execute the agent synchronously.

        This implementation:
        1. Calls OpenAI with function calling
        2. If tool is requested, executes it
        3. Returns final response
        """
        # Prepare messages
        messages = [
            {
                "role": "system",
                "content": "You are a helpful weather assistant. Use the get_weather tool to fetch current weather data."
            },
            {
                "role": "user",
                "content": input.message
            }
        ]

        # Define available tools
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get current weather for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "City name or coordinates"
                            }
                        },
                        "required": ["location"]
                    }
                }
            }
        ]

        # First LLM call
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # If no tool calls, return response directly
        if not tool_calls:
            return AgentOutput(
                content=response_message.content or "I couldn't process that request.",
                metadata={"model": self.model}
            )

        # Execute tool calls
        messages.append(response_message)

        executed_tools = []
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = eval(tool_call.function.arguments)

            if function_name == "get_weather":
                # Call weather API (using free weather API)
                location = function_args["location"]
                weather_data = await self._get_weather(location)

                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": str(weather_data)
                })

                executed_tools.append({
                    "name": function_name,
                    "args": function_args,
                    "result": weather_data
                })

        # Second LLM call with tool results
        final_response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )

        return AgentOutput(
            content=final_response.choices[0].message.content,
            tool_calls=executed_tools,
            metadata={
                "model": self.model,
                "total_tokens": final_response.usage.total_tokens
            }
        )

    async def stream(self, input: AgentInput) -> AsyncGenerator[StreamChunk, None]:
        """
        Execute the agent with streaming output.

        For simplicity, this streams the final response after tool execution.
        """
        # Execute invoke to get tool calls
        result = await self.invoke(input)

        # Stream the final content
        if result.tool_calls:
            yield StreamChunk(
                type="tool_start",
                content=f"Executed tools: {', '.join(t['name'] for t in result.tool_calls)}",
                metadata={"tools": result.tool_calls}
            )

        # Stream the response word by word
        words = result.content.split()
        for word in words:
            yield StreamChunk(type="text", content=word + " ")

    async def _get_weather(self, location: str) -> dict:
        """
        Fetch weather data from a free weather API.

        Using wttr.in as an example - no API key required.
        """
        # Use HTTP tool to make request
        result = await self.http_tool.execute(
            url=f"https://wttr.in/{location}?format=j1",
            method="GET"
        )

        # Parse response
        data = result.get("data", {})
        if "current_condition" in data:
            current = data["current_condition"][0]
            return {
                "location": location,
                "temperature_c": current.get("temp_C"),
                "temperature_f": current.get("temp_F"),
                "condition": current.get("weatherDesc", [{}])[0].get("value"),
                "humidity": current.get("humidity"),
                "wind_speed_kmph": current.get("windspeedKmph")
            }

        return {"error": "Could not fetch weather data"}
```

## Step 4: Test Your Agent Locally

Before registering, test it manually:

```python
# test_weather_agent.py
import asyncio
from agent_service.agent.custom.weather_agent import WeatherAgent
from agent_service.interfaces import AgentInput


async def test():
    agent = WeatherAgent()

    # Test invoke
    result = await agent.invoke(AgentInput(
        message="What's the weather in San Francisco?",
        session_id="test"
    ))

    print("Response:", result.content)
    print("Tools used:", result.tool_calls)

    # Test streaming
    print("\nStreaming response:")
    async for chunk in agent.stream(AgentInput(
        message="How's the weather in London?",
        session_id="test"
    )):
        print(chunk.content, end="")


if __name__ == "__main__":
    asyncio.run(test())
```

Run the test:
```bash
export OPENAI_API_KEY=your-api-key
python test_weather_agent.py
```

## Step 5: Register the Agent (Automatic)

Agents in `src/agent_service/agent/custom/` are automatically discovered and registered when the service starts.

Restart your service:
```bash
# If using Docker
docker-compose -f docker/docker-compose.yml restart api

# If running locally
# Stop the server (Ctrl+C) and restart
uvicorn agent_service.main:app --reload
```

Verify registration:
```bash
curl http://localhost:8000/api/v1/agents

# Should see your weather-agent in the list
```

## Step 6: Test via API

### Invoke Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/agents/weather-agent/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the weather like in New York?",
    "session_id": "user-123"
  }'
```

Expected response:
```json
{
  "content": "The current weather in New York is partly cloudy with a temperature of 18°C (64°F). The humidity is at 65% and wind speed is 15 km/h.",
  "tool_calls": [
    {
      "name": "get_weather",
      "args": {"location": "New York"},
      "result": {
        "location": "New York",
        "temperature_c": "18",
        "temperature_f": "64",
        "condition": "Partly cloudy",
        "humidity": "65",
        "wind_speed_kmph": "15"
      }
    }
  ],
  "metadata": {
    "model": "gpt-4o-mini",
    "total_tokens": 234
  }
}
```

### Stream Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/agents/weather-agent/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tell me about the weather in Paris",
    "session_id": "user-123"
  }'
```

## Step 7: Add Error Handling

Enhance your agent with proper error handling:

```python
from agent_service.domain.exceptions import AgentError, ToolExecutionError

class WeatherAgent(IAgent):
    # ... previous code ...

    async def invoke(self, input: AgentInput) -> AgentOutput:
        try:
            # Your implementation
            pass
        except Exception as e:
            # Log the error
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Weather agent error: {str(e)}", exc_info=True)

            # Return user-friendly error
            return AgentOutput(
                content="I'm sorry, I encountered an error while fetching the weather. Please try again.",
                metadata={"error": str(e)}
            )

    async def _get_weather(self, location: str) -> dict:
        try:
            result = await self.http_tool.execute(
                url=f"https://wttr.in/{location}?format=j1",
                method="GET"
            )
            return self._parse_weather(result)
        except Exception as e:
            raise ToolExecutionError(f"Failed to fetch weather: {str(e)}")
```

## Step 8: Add Tests

Create a test file:

```python
# tests/unit/agents/test_weather_agent.py
import pytest
from unittest.mock import AsyncMock, patch
from agent_service.agent.custom.weather_agent import WeatherAgent
from agent_service.interfaces import AgentInput


@pytest.fixture
def weather_agent():
    return WeatherAgent()


@pytest.mark.asyncio
async def test_weather_agent_invoke(weather_agent):
    """Test basic invocation."""
    with patch.object(weather_agent, '_get_weather', new_callable=AsyncMock) as mock_weather:
        mock_weather.return_value = {
            "location": "London",
            "temperature_c": "15",
            "condition": "Cloudy"
        }

        result = await weather_agent.invoke(AgentInput(
            message="What's the weather in London?",
            session_id="test"
        ))

        assert result.content is not None
        assert len(result.content) > 0


@pytest.mark.asyncio
async def test_weather_agent_stream(weather_agent):
    """Test streaming response."""
    chunks = []
    async for chunk in weather_agent.stream(AgentInput(
        message="Weather in Tokyo?",
        session_id="test"
    )):
        chunks.append(chunk)

    assert len(chunks) > 0
    assert any(chunk.type == "text" for chunk in chunks)


@pytest.mark.asyncio
async def test_weather_agent_error_handling(weather_agent):
    """Test error handling."""
    with patch.object(weather_agent, '_get_weather', side_effect=Exception("API error")):
        result = await weather_agent.invoke(AgentInput(
            message="Weather in InvalidCity?",
            session_id="test"
        ))

        # Should return graceful error message
        assert "error" in result.content.lower() or result.metadata.get("error")
```

Run tests:
```bash
pytest tests/unit/agents/test_weather_agent.py -v
```

## Step 9: Deploy to Production

Once your agent is tested and ready:

1. **Commit your code**:
   ```bash
   git add src/agent_service/agent/custom/weather_agent.py
   git add tests/unit/agents/test_weather_agent.py
   git commit -m "Add weather agent"
   git push
   ```

2. **Build new image**:
   ```bash
   docker build -f docker/Dockerfile -t your-registry/agent-service:v1.1.0 --target prod .
   docker push your-registry/agent-service:v1.1.0
   ```

3. **Deploy**:
   ```bash
   # Kubernetes
   kubectl set image deployment/agent-service-api \
     api=your-registry/agent-service:v1.1.0 \
     -n agent-service

   # Or update Helm values and upgrade
   helm upgrade agent-service ./helm/agent-service \
     --namespace agent-service \
     --set image.tag=v1.1.0
   ```

## Advanced Patterns

### Using LangGraph

For more complex workflows:

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class AgentState(TypedDict):
    messages: list
    location: str
    weather_data: dict

class LangGraphWeatherAgent(IAgent):
    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("extract_location", self._extract_location)
        workflow.add_node("fetch_weather", self._fetch_weather)
        workflow.add_node("generate_response", self._generate_response)

        # Add edges
        workflow.add_edge("extract_location", "fetch_weather")
        workflow.add_edge("fetch_weather", "generate_response")
        workflow.add_edge("generate_response", END)

        workflow.set_entry_point("extract_location")

        return workflow.compile()

    # Implement node functions...
```

### Adding Memory/Context

```python
from agent_service.infrastructure.cache import RedisCache

class StatefulWeatherAgent(IAgent):
    def __init__(self):
        self.cache = RedisCache()

    async def invoke(self, input: AgentInput) -> AgentOutput:
        # Get conversation history
        session_key = f"session:{input.session_id}"
        history = await self.cache.get(session_key) or []

        # Add to history
        history.append({"role": "user", "content": input.message})

        # Process with history
        # ...

        # Save updated history
        await self.cache.set(session_key, history, ttl=3600)

        return result
```

### Multiple Tools

```python
class MultiToolAgent(IAgent):
    def __init__(self):
        self.weather_tool = WeatherTool()
        self.news_tool = NewsTool()
        self.calculator_tool = CalculatorTool()

    @property
    def available_tools(self):
        return [
            self.weather_tool.schema,
            self.news_tool.schema,
            self.calculator_tool.schema
        ]

    async def execute_tool(self, name: str, **kwargs):
        tool_map = {
            "get_weather": self.weather_tool,
            "get_news": self.news_tool,
            "calculate": self.calculator_tool
        }

        tool = tool_map.get(name)
        if tool:
            return await tool.execute(**kwargs)

        raise ValueError(f"Unknown tool: {name}")
```

## Next Steps

- **Add more tools**: See [Tool System Guide](./api/tools.md)
- **Implement protocols**: See [Protocol Guide](./api/protocols.md)
- **Add authentication**: See [Authentication Guide](./api/authentication.md)
- **Monitor your agent**: Check metrics at http://localhost:3000

## Troubleshooting

### Agent not appearing in registry

```bash
# Check logs for errors
docker-compose -f docker/docker-compose.yml logs api | grep -i error

# Verify file is in correct location
ls -la src/agent_service/agent/custom/

# Check Python syntax
python -m py_compile src/agent_service/agent/custom/weather_agent.py
```

### Tool execution failures

```bash
# Test tool independently
python -c "
from agent_service.tools.examples.http_request import HTTPRequestTool
import asyncio
tool = HTTPRequestTool()
result = asyncio.run(tool.execute(url='https://wttr.in/London?format=j1', method='GET'))
print(result)
"
```

### OpenAI API errors

```bash
# Verify API key
echo $OPENAI_API_KEY

# Test OpenAI connection
python -c "
from openai import AsyncOpenAI
import asyncio
client = AsyncOpenAI()
result = asyncio.run(client.chat.completions.create(
    model='gpt-4o-mini',
    messages=[{'role': 'user', 'content': 'Hello'}]
))
print(result.choices[0].message.content)
"
```

## Common Patterns

### Rate Limiting

```python
from agent_service.api.middleware.rate_limit import RateLimiter

class RateLimitedAgent(IAgent):
    def __init__(self):
        self.rate_limiter = RateLimiter(max_requests=10, window=60)

    async def invoke(self, input: AgentInput) -> AgentOutput:
        # Check rate limit
        key = f"agent:{self.name}:{input.session_id}"
        if not await self.rate_limiter.check(key):
            return AgentOutput(
                content="Rate limit exceeded. Please try again later."
            )

        # Process normally
        # ...
```

### Logging and Tracing

```python
from agent_service.infrastructure.observability.logging import get_logger
from agent_service.infrastructure.observability.tracing import trace_async

logger = get_logger(__name__)

class TracedAgent(IAgent):
    @trace_async(span_name="weather_agent.invoke")
    async def invoke(self, input: AgentInput) -> AgentOutput:
        logger.info(f"Processing request", extra={
            "agent": self.name,
            "session_id": input.session_id,
            "message_length": len(input.message)
        })

        # Your implementation
        # ...

        logger.info(f"Request completed", extra={
            "agent": self.name,
            "response_length": len(result.content)
        })

        return result
```
