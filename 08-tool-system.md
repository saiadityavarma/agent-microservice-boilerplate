# Task 08: Tool System

## Objective
Create tool registry and example tool implementing `ITool`. Claude Code adds tools by implementing this interface.

## Deliverables

### Tool Registry
```python
# src/agent_service/tools/registry.py
from typing import Any
from agent_service.interfaces import ITool, ToolSchema


class ToolRegistry:
    """
    Registry for tool implementations.
    
    Claude Code: Register new tools here.
    """
    
    def __init__(self):
        self._tools: dict[str, ITool] = {}
    
    def register(self, tool: ITool) -> None:
        self._tools[tool.schema.name] = tool
    
    def get(self, name: str) -> ITool | None:
        return self._tools.get(name)
    
    def list_tools(self) -> list[ToolSchema]:
        return [t.schema for t in self._tools.values()]
    
    def to_openai_format(self) -> list[dict[str, Any]]:
        """Export tools in OpenAI function calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t.schema.name,
                    "description": t.schema.description,
                    "parameters": t.schema.parameters,
                }
            }
            for t in self._tools.values()
        ]
    
    async def execute(self, name: str, **kwargs) -> Any:
        """Execute a tool by name."""
        tool = self.get(name)
        if not tool:
            raise ValueError(f"Tool not found: {name}")
        return await tool.execute(**kwargs)


# Global registry
tool_registry = ToolRegistry()
```

### Example Tool: Echo
```python
# src/agent_service/tools/examples/echo.py
"""
Example tool implementation.

Claude Code: Use this as a template for new tools.
"""
from typing import Any
from agent_service.interfaces import ITool, ToolSchema


class EchoTool(ITool):
    """Simple echo tool for testing."""
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="echo",
            description="Echoes the input message back",
            parameters={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Message to echo",
                    }
                },
                "required": ["message"],
            },
        )
    
    async def execute(self, message: str, **kwargs) -> str:
        return f"Echo: {message}"
```

### Example Tool: HTTP Request
```python
# src/agent_service/tools/examples/http_request.py
"""
Example: HTTP request tool.

Claude Code: Shows a more complex tool with validation and error handling.
"""
from typing import Any, Literal
import httpx

from agent_service.interfaces import ITool, ToolSchema


class HTTPRequestTool(ITool):
    """Make HTTP requests."""
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="http_request",
            description="Make an HTTP request to a URL",
            parameters={
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST"],
                        "description": "HTTP method",
                    },
                    "url": {
                        "type": "string",
                        "description": "URL to request",
                    },
                    "body": {
                        "type": "object",
                        "description": "Request body (for POST)",
                    },
                },
                "required": ["method", "url"],
            },
        )
    
    @property
    def requires_confirmation(self) -> bool:
        """Require user confirmation before making requests."""
        return True
    
    async def execute(
        self,
        method: Literal["GET", "POST"],
        url: str,
        body: dict | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url)
            else:
                response = await client.post(url, json=body)
            
            return {
                "status_code": response.status_code,
                "body": response.text[:1000],  # Truncate
            }
```

### Tool Registration
```python
# In src/agent_service/api/app.py lifespan:

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register tools
    from agent_service.tools.registry import tool_registry
    from agent_service.tools.examples.echo import EchoTool
    
    tool_registry.register(EchoTool())
    # tool_registry.register(HTTPRequestTool())
    
    yield
```

### Tool Execution in Agents
```python
# Example: Using tools in an agent

from agent_service.tools.registry import tool_registry

async def handle_tool_call(tool_name: str, arguments: dict) -> Any:
    """Execute a tool call from the LLM."""
    tool = tool_registry.get(tool_name)
    if not tool:
        return {"error": f"Unknown tool: {tool_name}"}
    
    # Check if confirmation required
    if tool.requires_confirmation:
        # TODO: Implement confirmation flow
        pass
    
    return await tool.execute(**arguments)
```

## Pattern for Claude Code

When adding a new tool:
```python
# 1. Create tool file in tools/
# src/agent_service/tools/my_tool.py

from agent_service.interfaces import ITool, ToolSchema

class MyTool(ITool):
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="my_tool",
            description="What this tool does",
            parameters={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "..."},
                },
                "required": ["param1"],
            },
        )
    
    async def execute(self, param1: str, **kwargs) -> Any:
        # Implementation
        return result

# 2. Register in startup
tool_registry.register(MyTool())
```

## Acceptance Criteria
- [ ] ITool interface is clear
- [ ] Tool registry works
- [ ] Example tools demonstrate patterns
- [ ] Tools export to OpenAI format
- [ ] requires_confirmation flag available
