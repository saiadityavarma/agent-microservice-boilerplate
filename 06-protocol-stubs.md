# Task 06: Protocol Stubs (MCP, A2A, AG-UI)

## Objective
Create minimal protocol handler stubs implementing `IProtocolHandler`. Shows the pattern without full implementation - Claude Code completes based on actual SDK docs.

## Deliverables

### Protocol Registry
```python
# src/agent_service/protocols/registry.py
from agent_service.interfaces import IProtocolHandler, ProtocolType


class ProtocolRegistry:
    """Registry for protocol handlers."""
    
    def __init__(self):
        self._handlers: dict[ProtocolType, IProtocolHandler] = {}
    
    def register(self, handler: IProtocolHandler) -> None:
        self._handlers[handler.protocol_type] = handler
    
    def get(self, protocol: ProtocolType) -> IProtocolHandler | None:
        return self._handlers.get(protocol)
    
    def all(self) -> list[IProtocolHandler]:
        return list(self._handlers.values())


# Global registry
protocol_registry = ProtocolRegistry()
```

### MCP Handler Stub
```python
# src/agent_service/protocols/mcp/handler.py
"""
MCP (Model Context Protocol) handler stub.

SDK: pip install fastmcp
Docs: https://github.com/jlowin/fastmcp

Claude Code: Complete this implementation using the FastMCP SDK.
"""
from typing import Any, AsyncGenerator
from fastapi import Request

from agent_service.interfaces import IProtocolHandler, ProtocolType, IAgent


class MCPHandler(IProtocolHandler):
    """
    MCP protocol handler.
    
    Key concepts:
    - Tools: Functions the LLM can call
    - Resources: Data the LLM can read
    - Prompts: Reusable prompt templates
    """
    
    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.MCP
    
    async def handle_request(self, request: Request, agent: IAgent) -> Any:
        """
        Handle MCP request.
        
        TODO (Claude Code): 
        1. Parse MCP request format
        2. If tool call -> execute via agent
        3. Return MCP response format
        """
        # Stub - implement with FastMCP SDK
        raise NotImplementedError("Implement with FastMCP SDK")
    
    async def handle_stream(self, request: Request, agent: IAgent) -> AsyncGenerator[str, None]:
        """
        Handle MCP streaming request.
        
        TODO (Claude Code):
        1. Parse MCP request
        2. Stream agent response
        3. Format as MCP SSE events
        """
        raise NotImplementedError("Implement with FastMCP SDK")
        yield  # Make it a generator
    
    def get_capability_info(self) -> dict[str, Any]:
        """Return MCP server info for discovery."""
        return {
            "name": "Agent Service MCP",
            "version": "1.0",
            "capabilities": ["tools", "resources"],
        }
```

### A2A Handler Stub
```python
# src/agent_service/protocols/a2a/handler.py
"""
A2A (Agent-to-Agent) protocol handler stub.

SDK: pip install a2a-sdk
Docs: https://github.com/a2aproject/a2a-python

Claude Code: Complete this implementation using the A2A SDK.
"""
from typing import Any, AsyncGenerator
from fastapi import Request

from agent_service.interfaces import IProtocolHandler, ProtocolType, IAgent


class A2AHandler(IProtocolHandler):
    """
    A2A protocol handler.
    
    Key concepts:
    - Agent Card: /.well-known/agent.json describes capabilities
    - Tasks: Unit of work with lifecycle (submitted → working → completed)
    - Messages: Communication within tasks
    """
    
    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.A2A
    
    async def handle_request(self, request: Request, agent: IAgent) -> Any:
        """
        Handle A2A task request.
        
        TODO (Claude Code):
        1. Parse A2A task format
        2. Create task, update state
        3. Execute via agent
        4. Return A2A response
        """
        raise NotImplementedError("Implement with A2A SDK")
    
    async def handle_stream(self, request: Request, agent: IAgent) -> AsyncGenerator[str, None]:
        """
        Handle A2A streaming (tasks/sendSubscribe).
        
        TODO (Claude Code):
        1. Parse A2A request
        2. Emit task lifecycle events
        3. Stream agent response
        """
        raise NotImplementedError("Implement with A2A SDK")
        yield
    
    def get_capability_info(self) -> dict[str, Any]:
        """Return A2A agent card."""
        return {
            "name": "Agent Service",
            "description": "Agent microservice with multi-protocol support",
            "url": "/a2a",
            "capabilities": {
                "streaming": True,
                "pushNotifications": False,
            },
            "skills": [],  # TODO: Populate from tool registry
        }
```

### AG-UI Handler Stub
```python
# src/agent_service/protocols/agui/handler.py
"""
AG-UI (Agent-User Interaction) protocol handler stub.

SDK: pip install ag-ui-protocol
Docs: https://docs.copilotkit.ai/coagents/ag-ui

Claude Code: Complete this implementation using the AG-UI SDK.
"""
from typing import Any, AsyncGenerator
from fastapi import Request

from agent_service.interfaces import IProtocolHandler, ProtocolType, IAgent


class AGUIHandler(IProtocolHandler):
    """
    AG-UI protocol handler for frontend integration.
    
    Key concepts:
    - Events: TEXT_MESSAGE_*, TOOL_CALL_*, STATE_*, RUN_*
    - Streaming: SSE events to frontend
    - State: Sync state between agent and UI
    """
    
    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.AGUI
    
    async def handle_request(self, request: Request, agent: IAgent) -> Any:
        """Non-streaming not typically used for AG-UI."""
        raise NotImplementedError("AG-UI uses streaming")
    
    async def handle_stream(self, request: Request, agent: IAgent) -> AsyncGenerator[str, None]:
        """
        Handle AG-UI streaming request.
        
        TODO (Claude Code):
        1. Emit RUN_STARTED
        2. Emit TEXT_MESSAGE_START
        3. Stream content as TEXT_MESSAGE_CONTENT
        4. Emit TOOL_CALL_* for tool usage
        5. Emit RUN_FINISHED
        
        Event format: {"type": "EVENT_TYPE", ...}
        """
        raise NotImplementedError("Implement with AG-UI SDK")
        yield
    
    def get_capability_info(self) -> dict[str, Any]:
        """Return AG-UI server capabilities."""
        return {
            "protocol": "ag-ui",
            "version": "1.0",
            "capabilities": {
                "streaming": True,
                "stateManagement": True,
                "toolCalls": True,
            },
        }
```

### Protocol Routes
```python
# src/agent_service/api/routes/protocols.py
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse

from agent_service.protocols.registry import protocol_registry
from agent_service.interfaces import ProtocolType
from agent_service.agent.registry import get_default_agent

router = APIRouter()


@router.get("/.well-known/agent.json")
async def agent_card():
    """A2A agent card endpoint."""
    handler = protocol_registry.get(ProtocolType.A2A)
    if handler:
        return handler.get_capability_info()
    return JSONResponse(status_code=404, content={"error": "A2A not enabled"})


@router.post("/{protocol}/invoke")
async def protocol_invoke(protocol: ProtocolType, request: Request):
    """Generic protocol invoke endpoint."""
    handler = protocol_registry.get(protocol)
    if not handler:
        return JSONResponse(status_code=404, content={"error": f"{protocol} not enabled"})
    
    agent = get_default_agent()
    return await handler.handle_request(request, agent)


@router.post("/{protocol}/stream")
async def protocol_stream(protocol: ProtocolType, request: Request):
    """Generic protocol stream endpoint."""
    handler = protocol_registry.get(protocol)
    if not handler:
        return JSONResponse(status_code=404, content={"error": f"{protocol} not enabled"})
    
    agent = get_default_agent()
    return StreamingResponse(
        handler.handle_stream(request, agent),
        media_type="text/event-stream",
    )
```

## Pattern for Claude Code

When implementing a protocol:
```python
# 1. Install SDK
# uv add fastmcp  # or a2a-sdk, ag-ui-protocol

# 2. Complete the handler implementation
class MCPHandler(IProtocolHandler):
    async def handle_request(self, request: Request, agent: IAgent) -> Any:
        # Use SDK to parse request
        # Call agent.invoke() or agent.stream()
        # Format response per protocol spec
        ...

# 3. Register in startup
from agent_service.protocols.registry import protocol_registry
protocol_registry.register(MCPHandler())
```

## Acceptance Criteria
- [ ] Protocol registry works
- [ ] Handler stubs implement IProtocolHandler
- [ ] Routes dispatch to correct handler
- [ ] Clear TODOs for Claude Code to implement
