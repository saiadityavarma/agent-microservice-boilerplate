# Protocol Registry and MCP Implementation

This directory contains the protocol registry and implementations for MCP (Model Context Protocol), A2A (Agent-to-Agent), and AGUI (Agent UI) protocols.

## Overview

The protocol system enables the agent service to communicate using multiple industry-standard protocols. Each protocol has a dedicated handler that implements the `IProtocolHandler` interface.

## Components

### 1. Protocol Registry (`registry.py`)

The `ProtocolRegistry` manages all protocol handlers and provides auto-registration based on settings.

**Key Features:**
- Register protocol handlers by name
- Get handlers by protocol name or type
- List all registered protocols
- Check if a protocol is registered
- Auto-registration on startup based on feature flags

**Usage:**
```python
from agent_service.protocols import get_protocol_registry

# Get the global registry
registry = get_protocol_registry()

# Check if MCP is registered
if registry.is_registered("mcp"):
    handler = registry.get_handler("mcp")

# List all registered protocols
protocols = registry.list_protocols()  # ["mcp", "a2a", "agui"]
```

**Auto-Registration:**
Protocols are automatically registered on startup based on settings:
- `enable_mcp=True` → Registers MCP handler
- `enable_a2a=True` → Registers A2A handler
- `enable_agui=True` → Registers AGUI handler

### 2. MCP Implementation (`mcp/`)

Complete implementation of the Model Context Protocol using the FastMCP library.

#### Handler (`mcp/handler.py`)

The `MCPHandler` implements the `IProtocolHandler` interface and provides:

**Supported Methods:**
- `list_tools` - List all available tools
- `call_tool` - Execute a specific tool
- `list_resources` - List available resources
- `read_resource` - Read a specific resource
- `list_prompts` - List available prompt templates
- `get_prompt` - Get a specific prompt template

**Features:**
- Automatic tool registration from tool registry
- Resource providers (system info, etc.)
- Prompt templates
- Streaming support via SSE
- Error handling with MCP error format

**Example Request:**
```json
{
  "method": "list_tools"
}
```

**Example Response:**
```json
{
  "tools": [
    {
      "name": "echo",
      "description": "Echoes the input message back",
      "inputSchema": {
        "type": "object",
        "properties": {
          "message": {"type": "string", "description": "Message to echo"}
        },
        "required": ["message"]
      }
    }
  ]
}
```

#### Server (`mcp/server.py`)

Provides a FastMCP server instance configured with tools and resources.

**Features:**
- Lazy initialization
- Automatic tool registration
- Built-in resources (system info)
- Prompt templates

**Usage:**
```python
from agent_service.protocols.mcp import get_mcp_server

mcp_server = get_mcp_server()
```

#### Tools (`mcp/tools.py`)

Utilities for converting agent service tools to MCP format.

**Key Functions:**
- `register_tools_from_registry(mcp_server)` - Register all tools with MCP
- `convert_tool_to_mcp_format(tool_schema)` - Convert ToolSchema to MCP format
- `create_tool_executor(tool_name)` - Create async executor for a tool
- `validate_tool_arguments(tool_schema, arguments)` - Validate tool arguments

### 3. API Routes

MCP endpoints are available in `api/routes/protocols.py`:

#### Generic Protocol Endpoints

- `POST /{protocol}/invoke` - Invoke any protocol handler
- `POST /{protocol}/stream` - Stream from any protocol handler

#### MCP-Specific Endpoints

- `GET /mcp` - MCP SSE endpoint for streaming
- `GET /mcp/info` - Get MCP server capabilities
- `GET /mcp/tools` - List all available tools
- `POST /mcp/tools/{tool_name}` - Direct tool invocation

**Example Tool Invocation:**
```bash
curl -X POST http://localhost:8000/mcp/tools/echo \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"arguments": {"message": "Hello, MCP!"}}'
```

**Response:**
```json
{
  "success": true,
  "tool": "echo",
  "result": "Echo: Hello, MCP!"
}
```

## Installation

### Install FastMCP

```bash
pip install fastmcp
```

Or install with the MCP extras:

```bash
pip install -e ".[mcp]"
```

## Configuration

Protocol handlers are configured via environment variables:

```env
# Enable/disable protocols
ENABLE_MCP=true
ENABLE_A2A=true
ENABLE_AGUI=true
```

## Architecture

```
┌─────────────────────────────────────────┐
│         FastAPI Application             │
├─────────────────────────────────────────┤
│                                         │
│  ┌───────────────────────────────────┐ │
│  │    Protocol Registry              │ │
│  │  - Auto-registers handlers        │ │
│  │  - Route to correct handler       │ │
│  └───────────────────────────────────┘ │
│           │         │         │         │
│     ┌─────┘    ┌────┘    ┌────┘        │
│     │          │         │              │
│  ┌──▼──┐   ┌──▼──┐   ┌──▼──┐          │
│  │ MCP │   │ A2A │   │AGUI │          │
│  │     │   │     │   │     │          │
│  └──┬──┘   └──┬──┘   └──┬──┘          │
│     │         │         │              │
│  ┌──▼─────────▼─────────▼──┐          │
│  │     Tool Registry        │          │
│  │  - echo                  │          │
│  │  - http_request          │          │
│  │  - custom tools...       │          │
│  └──────────────────────────┘          │
│                                         │
└─────────────────────────────────────────┘
```

## Adding a New Tool

1. Create a tool implementing `ITool`:

```python
from agent_service.interfaces import ITool, ToolSchema

class MyTool(ITool):
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="my_tool",
            description="Does something useful",
            parameters={
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Input value"}
                },
                "required": ["input"]
            }
        )

    async def execute(self, input: str, **kwargs) -> str:
        return f"Result: {input}"
```

2. Register the tool:

```python
from agent_service.tools.registry import tool_registry

tool_registry.register(MyTool())
```

3. The tool is automatically available via MCP!

## Testing

Test the MCP implementation:

```bash
# List tools
curl -X POST http://localhost:8000/mcp/invoke \
  -H "Content-Type: application/json" \
  -d '{"method": "list_tools"}'

# Call a tool
curl -X POST http://localhost:8000/mcp/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "method": "call_tool",
    "params": {
      "name": "echo",
      "arguments": {"message": "Hello"}
    }
  }'

# Get server info
curl http://localhost:8000/mcp/info
```

## Error Handling

The MCP handler provides comprehensive error handling:

- **400 Bad Request**: Invalid JSON or unknown method
- **404 Not Found**: Tool not found or MCP not enabled
- **500 Internal Server Error**: Tool execution errors

Error responses follow MCP format:

```json
{
  "isError": true,
  "content": [
    {
      "type": "text",
      "text": "Error executing tool: Tool not found"
    }
  ]
}
```

## Security

MCP endpoints support authentication via:
- **Bearer Token**: `Authorization: Bearer <token>`
- **API Key**: `X-API-Key: <api-key>`

All endpoints respect the configured authentication middleware.

## Future Enhancements

Potential improvements:
- [ ] Add more built-in resources (database queries, file system)
- [ ] Implement resource templates
- [ ] Add prompt composition utilities
- [ ] Support for MCP protocol extensions
- [ ] WebSocket transport for MCP
- [ ] Tool usage analytics and monitoring

## References

- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Model Context Protocol Specification](https://spec.modelcontextprotocol.io/)
- [A2A Protocol](https://github.com/a2aproject/a2a-python)
- [AG-UI Documentation](https://docs.copilotkit.ai/coagents/ag-ui)
