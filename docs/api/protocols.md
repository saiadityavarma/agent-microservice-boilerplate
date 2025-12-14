# Protocol Reference: MCP, A2A, AG-UI

Guide to implementing and using Model Context Protocol (MCP), Agent-to-Agent (A2A), and AG-UI protocols.

## Overview

The Agent Service supports three major agent protocols:

1. **MCP (Model Context Protocol)** - Claude/Anthropic's protocol for context sharing
2. **A2A (Agent-to-Agent)** - Protocol for agent collaboration
3. **AG-UI (Agent-UI)** - Protocol for agent-to-UI communication

## Model Context Protocol (MCP)

### What is MCP?

MCP allows agents to share context, tools, and resources in a standardized way.

### Enable MCP

```bash
# .env
ENABLE_MCP=true
```

### MCP Endpoints

```
GET  /mcp/capabilities     - List available capabilities
POST /mcp/invoke          - Invoke agent with MCP context
POST /mcp/stream          - Stream agent response
GET  /mcp/tools           - List available tools
POST /mcp/tools/{name}    - Execute a tool directly
```

### MCP Request Format

```json
{
  "context": {
    "conversation_id": "conv-123",
    "user_id": "user-456",
    "metadata": {
      "source": "claude-desktop",
      "version": "1.0"
    }
  },
  "message": "What's the weather in London?",
  "available_tools": ["get_weather", "http_request"]
}
```

### MCP Response Format

```json
{
  "response": {
    "content": "The weather in London is...",
    "tool_calls": [
      {
        "tool": "get_weather",
        "arguments": {"location": "London"},
        "result": {"temperature": "15°C"}
      }
    ]
  },
  "context": {
    "conversation_id": "conv-123",
    "turn_id": "turn-789"
  }
}
```

### Using MCP from Python

```python
import requests

# MCP invoke request
response = requests.post(
    "http://localhost:8000/mcp/invoke",
    json={
        "context": {
            "conversation_id": "conv-123",
            "user_id": "user-456"
        },
        "message": "What's the weather?",
        "agent": "weather-agent",
        "available_tools": ["get_weather"]
    }
)

result = response.json()
print(result["response"]["content"])
```

### MCP Server Implementation

```python
# src/agent_service/protocols/mcp/server.py
from agent_service.interfaces import IProtocolHandler, ProtocolType
from fastapi import Request

class MCPServer(IProtocolHandler):
    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.MCP

    async def handle_request(self, request: Request, agent) -> dict:
        # Parse MCP request
        body = await request.json()

        # Transform to AgentInput
        agent_input = AgentInput(
            message=body["message"],
            session_id=body["context"].get("conversation_id"),
            context=body.get("context", {})
        )

        # Invoke agent
        output = await agent.invoke(agent_input)

        # Transform to MCP response
        return {
            "response": {
                "content": output.content,
                "tool_calls": output.tool_calls
            },
            "context": body["context"]
        }
```

### MCP Capabilities

List MCP capabilities:

```bash
curl http://localhost:8000/mcp/capabilities
```

Response:
```json
{
  "protocol": "mcp",
  "version": "1.0",
  "capabilities": {
    "agents": ["weather-agent", "simple-llm"],
    "tools": ["get_weather", "http_request"],
    "streaming": true,
    "tool_execution": true
  }
}
```

## Agent-to-Agent Protocol (A2A)

### What is A2A?

A2A enables agents to discover and communicate with each other.

### Enable A2A

```bash
# .env
ENABLE_A2A=true
```

### A2A Endpoints

```
GET  /a2a/discover         - Discover available agents
POST /a2a/task/create      - Create a task for another agent
GET  /a2a/task/{id}        - Get task status
POST /a2a/task/{id}/result - Submit task result
GET  /a2a/agents/{name}    - Get agent card
```

### Agent Discovery

```bash
curl http://localhost:8000/a2a/discover
```

Response:
```json
{
  "agents": [
    {
      "id": "weather-agent",
      "name": "Weather Agent",
      "description": "Provides weather information",
      "capabilities": ["weather_lookup", "forecast"],
      "endpoint": "http://localhost:8000/a2a/agents/weather-agent",
      "protocols": ["a2a", "mcp"]
    }
  ]
}
```

### Create A2A Task

```python
import requests

# Agent A creates task for Agent B
response = requests.post(
    "http://localhost:8000/a2a/task/create",
    json={
        "source_agent": "orchestrator",
        "target_agent": "weather-agent",
        "task": {
            "type": "weather_lookup",
            "parameters": {
                "location": "London",
                "units": "metric"
            }
        },
        "callback_url": "http://orchestrator:8000/a2a/callback"
    }
)

task = response.json()
task_id = task["task_id"]

# Poll for result
result = requests.get(f"http://localhost:8000/a2a/task/{task_id}")
print(result.json())
```

### A2A Task Format

```json
{
  "task_id": "task-abc123",
  "source_agent": "orchestrator",
  "target_agent": "weather-agent",
  "status": "pending",  // pending, in_progress, completed, failed
  "task": {
    "type": "weather_lookup",
    "parameters": {
      "location": "London"
    }
  },
  "result": null,
  "created_at": "2024-12-14T10:00:00Z",
  "updated_at": "2024-12-14T10:00:00Z"
}
```

### Agent Card

Each agent exposes a card with capabilities:

```bash
curl http://localhost:8000/a2a/agents/weather-agent
```

Response:
```json
{
  "id": "weather-agent",
  "name": "Weather Agent",
  "version": "1.0.0",
  "description": "Provides current weather and forecasts",
  "capabilities": [
    {
      "name": "weather_lookup",
      "description": "Get current weather",
      "parameters": {
        "location": {"type": "string", "required": true},
        "units": {"type": "string", "enum": ["metric", "imperial"]}
      }
    }
  ],
  "protocols": ["a2a", "mcp"],
  "endpoint": "http://localhost:8000/a2a/agents/weather-agent"
}
```

### A2A Implementation

```python
# src/agent_service/protocols/a2a/handler.py
from agent_service.interfaces import IProtocolHandler, ProtocolType

class A2AHandler(IProtocolHandler):
    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.A2A

    async def handle_request(self, request: Request, agent) -> dict:
        body = await request.json()

        # Create task
        task_id = await self.task_manager.create_task(
            source=body["source_agent"],
            target=agent.name,
            task_data=body["task"]
        )

        # Execute task asynchronously
        await self.task_manager.execute_task(task_id, agent)

        return {
            "task_id": task_id,
            "status": "pending"
        }
```

## AG-UI Protocol

### What is AG-UI?

AG-UI provides rich UI components and interactive elements in agent responses.

### Enable AG-UI

```bash
# .env
ENABLE_AGUI=true
```

### AG-UI Endpoints

```
POST /agui/invoke        - Invoke with UI components
POST /agui/stream        - Stream with UI components
POST /agui/action        - Handle UI action (button click, etc.)
```

### AG-UI Response Format

```json
{
  "content": "Here's the weather forecast:",
  "ui_components": [
    {
      "type": "card",
      "props": {
        "title": "London Weather",
        "content": {
          "type": "grid",
          "items": [
            {
              "type": "metric",
              "label": "Temperature",
              "value": "15°C",
              "icon": "thermometer"
            },
            {
              "type": "metric",
              "label": "Humidity",
              "value": "65%",
              "icon": "droplet"
            }
          ]
        }
      }
    },
    {
      "type": "button",
      "props": {
        "label": "Get 7-day Forecast",
        "action": "get_forecast",
        "style": "primary"
      }
    }
  ]
}
```

### AG-UI Components

Supported component types:

- `card` - Card container
- `grid` - Grid layout
- `metric` - Metric display
- `chart` - Chart (line, bar, pie)
- `button` - Interactive button
- `input` - Input field
- `select` - Dropdown select
- `table` - Data table
- `code` - Code block
- `markdown` - Markdown content

### Using AG-UI from Python

```python
import requests

# Invoke with AG-UI
response = requests.post(
    "http://localhost:8000/agui/invoke",
    json={
        "agent": "weather-agent",
        "message": "Show me the weather in London",
        "session_id": "user-123"
    }
)

result = response.json()

# Result includes UI components
print(result["content"])
for component in result.get("ui_components", []):
    print(f"Component: {component['type']}")
```

### Handling AG-UI Actions

```python
# Handle button click or form submission
response = requests.post(
    "http://localhost:8000/agui/action",
    json={
        "action": "get_forecast",
        "session_id": "user-123",
        "parameters": {
            "days": 7
        }
    }
)
```

### AG-UI Implementation Example

```python
# src/agent_service/protocols/agui/handler.py
class AGUIHandler(IProtocolHandler):
    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.AGUI

    async def handle_request(self, request: Request, agent) -> dict:
        body = await request.json()

        # Invoke agent
        agent_input = AgentInput(
            message=body["message"],
            session_id=body.get("session_id"),
            context={"ui_enabled": True}
        )

        output = await agent.invoke(agent_input)

        # Add UI components based on output
        ui_components = self._generate_ui_components(output)

        return {
            "content": output.content,
            "ui_components": ui_components,
            "metadata": output.metadata
        }

    def _generate_ui_components(self, output: AgentOutput) -> list:
        """Generate UI components from agent output."""
        components = []

        # Example: Create weather card if weather data in metadata
        if "weather_data" in output.metadata:
            weather = output.metadata["weather_data"]
            components.append({
                "type": "card",
                "props": {
                    "title": f"Weather in {weather['location']}",
                    "content": {
                        "type": "grid",
                        "items": [
                            {
                                "type": "metric",
                                "label": "Temperature",
                                "value": weather["temperature"],
                                "icon": "thermometer"
                            }
                        ]
                    }
                }
            })

        return components
```

## Protocol Comparison

| Feature | MCP | A2A | AG-UI |
|---------|-----|-----|-------|
| Purpose | Context sharing | Agent collaboration | Rich UI responses |
| Use Case | Claude integration | Multi-agent systems | Interactive UIs |
| Streaming | Yes | No | Yes |
| Tool Execution | Yes | Via tasks | Yes |
| UI Components | No | No | Yes |
| Discovery | Capabilities endpoint | Agent discovery | N/A |

## Implementing Custom Protocol

### Step 1: Create Protocol Handler

```python
# src/agent_service/protocols/custom/my_protocol.py
from agent_service.interfaces import IProtocolHandler, ProtocolType

class MyProtocolHandler(IProtocolHandler):
    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.CUSTOM  # Add to enum

    async def handle_request(self, request: Request, agent) -> dict:
        # Parse custom protocol request
        body = await request.json()

        # Transform to AgentInput
        agent_input = self._transform_request(body)

        # Invoke agent
        output = await agent.invoke(agent_input)

        # Transform to custom protocol response
        return self._transform_response(output)

    async def handle_stream(self, request: Request, agent):
        # Implement streaming
        body = await request.json()
        agent_input = self._transform_request(body)

        async for chunk in agent.stream(agent_input):
            yield self._format_chunk(chunk)
```

### Step 2: Register Protocol

```python
# src/agent_service/protocols/registry.py
from agent_service.protocols.custom.my_protocol import MyProtocolHandler

protocol_registry = {
    "mcp": MCPHandler(),
    "a2a": A2AHandler(),
    "agui": AGUIHandler(),
    "custom": MyProtocolHandler()
}
```

### Step 3: Add Routes

```python
# src/agent_service/api/routes/protocols.py
from fastapi import APIRouter

router = APIRouter()

@router.post("/custom/invoke")
async def custom_invoke(request: Request):
    handler = protocol_registry["custom"]
    agent = get_agent(request.agent_name)
    return await handler.handle_request(request, agent)
```

## Testing Protocols

### MCP Tests

```python
# tests/integration/protocols/test_mcp.py
import pytest

@pytest.mark.asyncio
async def test_mcp_invoke(client):
    response = client.post(
        "/mcp/invoke",
        json={
            "context": {"conversation_id": "test"},
            "message": "Hello",
            "agent": "simple-llm"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "content" in data["response"]
```

### A2A Tests

```python
# tests/integration/protocols/test_a2a.py
@pytest.mark.asyncio
async def test_a2a_task_creation(client):
    # Create task
    response = client.post(
        "/a2a/task/create",
        json={
            "source_agent": "test-agent",
            "target_agent": "weather-agent",
            "task": {
                "type": "weather_lookup",
                "parameters": {"location": "London"}
            }
        }
    )

    assert response.status_code == 200
    task = response.json()
    assert "task_id" in task

    # Check task status
    status_response = client.get(f"/a2a/task/{task['task_id']}")
    assert status_response.status_code == 200
```

## Best Practices

1. **Protocol Versioning**: Version your protocol implementations
2. **Error Handling**: Return protocol-specific error formats
3. **Validation**: Validate protocol-specific request schemas
4. **Documentation**: Document protocol extensions
5. **Testing**: Test protocol compatibility
6. **Performance**: Optimize protocol transformations
7. **Security**: Validate cross-agent requests in A2A

## Examples

See `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/examples/protocols/`:

- `mcp_client.py` - MCP client implementation
- `a2a_orchestrator.py` - A2A orchestration example
- `agui_components.py` - AG-UI component examples

## Next Steps

- [Agent API](./agents.md) - Learn about agent endpoints
- [Tool System](./tools.md) - Add tools to protocols
- [Authentication](./authentication.md) - Secure protocol endpoints
