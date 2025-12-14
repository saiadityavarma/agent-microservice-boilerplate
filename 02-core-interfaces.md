# Task 02: Core Interfaces (Contracts)

## Objective
Define abstract interfaces that establish contracts for all implementations. Claude Code extends the system by implementing these interfaces.

## Deliverables

### IAgent Interface
```python
# src/agent_service/interfaces/agent.py
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator
from dataclasses import dataclass


@dataclass
class AgentInput:
    """Standard input to any agent."""
    message: str
    session_id: str | None = None
    context: dict[str, Any] | None = None


@dataclass
class AgentOutput:
    """Standard output from any agent."""
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class StreamChunk:
    """Chunk emitted during streaming."""
    type: str  # "text", "tool_start", "tool_end", "error"
    content: str = ""
    metadata: dict[str, Any] | None = None


class IAgent(ABC):
    """
    Interface for any agent implementation.
    
    Claude Code: Implement this interface to add a new agent framework.
    
    Example:
        class LangGraphAgent(IAgent):
            async def invoke(self, input: AgentInput) -> AgentOutput:
                # Your LangGraph implementation
                ...
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this agent."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        pass
    
    @abstractmethod
    async def invoke(self, input: AgentInput) -> AgentOutput:
        """
        Execute agent synchronously.
        
        Args:
            input: Standardized agent input
            
        Returns:
            Standardized agent output
        """
        pass
    
    @abstractmethod
    async def stream(self, input: AgentInput) -> AsyncGenerator[StreamChunk, None]:
        """
        Execute agent with streaming output.
        
        Args:
            input: Standardized agent input
            
        Yields:
            StreamChunk for each piece of output
        """
        pass
    
    async def setup(self) -> None:
        """Optional: Called once when agent is registered."""
        pass
    
    async def teardown(self) -> None:
        """Optional: Called when agent is unregistered."""
        pass
```

### ITool Interface
```python
# src/agent_service/interfaces/tool.py
from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel


class ToolSchema(BaseModel):
    """JSON Schema for tool parameters."""
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema format


class ITool(ABC):
    """
    Interface for any tool implementation.
    
    Claude Code: Implement this interface to add a new tool.
    
    Example:
        class WebSearchTool(ITool):
            @property
            def schema(self) -> ToolSchema:
                return ToolSchema(
                    name="web_search",
                    description="Search the web",
                    parameters={"query": {"type": "string"}}
                )
            
            async def execute(self, **kwargs) -> Any:
                query = kwargs["query"]
                # Your implementation
                ...
    """
    
    @property
    @abstractmethod
    def schema(self) -> ToolSchema:
        """Return tool schema for LLM function calling."""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """
        Execute the tool with given arguments.
        
        Args:
            **kwargs: Tool-specific arguments matching schema
            
        Returns:
            Tool execution result
        """
        pass
    
    @property
    def requires_confirmation(self) -> bool:
        """Override to require human confirmation before execution."""
        return False
```

### IProtocolHandler Interface
```python
# src/agent_service/interfaces/protocol.py
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator
from fastapi import Request
from enum import Enum


class ProtocolType(str, Enum):
    MCP = "mcp"
    A2A = "a2a"
    AGUI = "agui"


class IProtocolHandler(ABC):
    """
    Interface for protocol handlers (MCP, A2A, AG-UI).
    
    Claude Code: Implement this interface to add protocol support.
    
    Example:
        class MCPHandler(IProtocolHandler):
            protocol_type = ProtocolType.MCP
            
            async def handle_request(self, request, agent):
                # Transform MCP request -> AgentInput
                # Call agent
                # Transform AgentOutput -> MCP response
                ...
    """
    
    @property
    @abstractmethod
    def protocol_type(self) -> ProtocolType:
        """Which protocol this handler supports."""
        pass
    
    @abstractmethod
    async def handle_request(
        self,
        request: Request,
        agent: "IAgent",
    ) -> Any:
        """
        Handle incoming protocol request.
        
        Args:
            request: FastAPI request
            agent: Agent to invoke
            
        Returns:
            Protocol-specific response
        """
        pass
    
    @abstractmethod
    async def handle_stream(
        self,
        request: Request,
        agent: "IAgent",
    ) -> AsyncGenerator[str, None]:
        """
        Handle streaming protocol request.
        
        Args:
            request: FastAPI request
            agent: Agent to invoke
            
        Yields:
            Protocol-formatted SSE events
        """
        pass
    
    def get_capability_info(self) -> dict[str, Any]:
        """Return protocol-specific capability info (agent card, etc.)."""
        return {}
```

### IRepository Interface
```python
# src/agent_service/interfaces/repository.py
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Sequence
from uuid import UUID

T = TypeVar("T")


class IRepository(ABC, Generic[T]):
    """
    Generic repository interface for data access.
    
    Claude Code: Implement this for each domain entity.
    
    Example:
        class SessionRepository(IRepository[Session]):
            async def get(self, id: UUID) -> Session | None:
                ...
    """
    
    @abstractmethod
    async def get(self, id: UUID) -> T | None:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    async def get_many(
        self,
        skip: int = 0,
        limit: int = 100,
        **filters: Any,
    ) -> Sequence[T]:
        """Get multiple entities with filtering."""
        pass
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create new entity."""
        pass
    
    @abstractmethod
    async def update(self, id: UUID, **values: Any) -> T | None:
        """Update entity by ID."""
        pass
    
    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete entity by ID."""
        pass
```

### Re-export from interfaces/__init__.py
```python
# src/agent_service/interfaces/__init__.py
from .agent import IAgent, AgentInput, AgentOutput, StreamChunk
from .tool import ITool, ToolSchema
from .protocol import IProtocolHandler, ProtocolType
from .repository import IRepository

__all__ = [
    "IAgent",
    "AgentInput", 
    "AgentOutput",
    "StreamChunk",
    "ITool",
    "ToolSchema",
    "IProtocolHandler",
    "ProtocolType",
    "IRepository",
]
```

## Acceptance Criteria
- [ ] All interfaces defined with clear docstrings
- [ ] Type hints complete for all methods
- [ ] Example usage in docstrings
- [ ] Interfaces importable from `agent_service.interfaces`

## Why This Matters for Claude Code
When Claude Code needs to add functionality:
1. It looks at the interface
2. Creates a new class implementing the interface
3. Registers it with the appropriate registry
4. Done - no need to modify core code
