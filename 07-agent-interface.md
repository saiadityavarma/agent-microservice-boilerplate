# Task 07: Agent Interface & Placeholder Implementation

## Objective
Create a placeholder agent implementation and registry. Claude Code swaps in any agent framework by implementing `IAgent`.

## Deliverables

### Agent Registry
```python
# src/agent_service/agent/registry.py
from agent_service.interfaces import IAgent


class AgentRegistry:
    """
    Registry for agent implementations.
    
    Claude Code: Register new agent implementations here.
    """
    
    def __init__(self):
        self._agents: dict[str, IAgent] = {}
        self._default: str | None = None
    
    def register(self, agent: IAgent, default: bool = False) -> None:
        self._agents[agent.name] = agent
        if default or self._default is None:
            self._default = agent.name
    
    def get(self, name: str) -> IAgent | None:
        return self._agents.get(name)
    
    def get_default(self) -> IAgent | None:
        if self._default:
            return self._agents.get(self._default)
        return None
    
    def list_agents(self) -> list[str]:
        return list(self._agents.keys())


# Global registry
agent_registry = AgentRegistry()


def get_default_agent() -> IAgent:
    """FastAPI dependency to get default agent."""
    agent = agent_registry.get_default()
    if not agent:
        raise RuntimeError("No agent registered")
    return agent
```

### Placeholder Agent (Echo)
```python
# src/agent_service/agent/placeholder.py
"""
Placeholder agent that echoes input.

Claude Code: Replace this with actual agent framework implementation.
See examples below for different frameworks.
"""
from typing import AsyncGenerator

from agent_service.interfaces import IAgent, AgentInput, AgentOutput, StreamChunk


class PlaceholderAgent(IAgent):
    """
    Simple echo agent for testing the pipeline.
    
    Replace with actual implementation:
    - LangGraph: see agent/examples/langgraph_agent.py
    - AutoGen: see agent/examples/autogen_agent.py
    - Custom: implement IAgent directly
    """
    
    @property
    def name(self) -> str:
        return "placeholder"
    
    @property
    def description(self) -> str:
        return "Echo agent for testing"
    
    async def invoke(self, input: AgentInput) -> AgentOutput:
        """Echo the input back."""
        return AgentOutput(
            content=f"Echo: {input.message}",
            metadata={"session_id": input.session_id},
        )
    
    async def stream(self, input: AgentInput) -> AsyncGenerator[StreamChunk, None]:
        """Stream the echo response word by word."""
        words = f"Echo: {input.message}".split()
        for word in words:
            yield StreamChunk(type="text", content=word + " ")
```

### Framework Example: LangGraph
```python
# src/agent_service/agent/examples/langgraph_agent.py
"""
Example: LangGraph agent implementation.

Install: uv add langgraph langchain-openai

Claude Code: Use this as a template for LangGraph-based agents.
"""
from typing import AsyncGenerator

from agent_service.interfaces import IAgent, AgentInput, AgentOutput, StreamChunk


class LangGraphAgent(IAgent):
    """
    LangGraph-based agent.
    
    Requirements:
        - langgraph
        - langchain-openai (or langchain-anthropic)
    """
    
    def __init__(self, model: str = "gpt-4o-mini"):
        self._model = model
        self._graph = None  # Initialized in setup()
    
    @property
    def name(self) -> str:
        return "langgraph"
    
    @property
    def description(self) -> str:
        return f"LangGraph agent using {self._model}"
    
    async def setup(self) -> None:
        """Initialize the LangGraph workflow."""
        # TODO (Claude Code): Build your graph here
        # from langgraph.graph import StateGraph
        # from langchain_openai import ChatOpenAI
        # 
        # llm = ChatOpenAI(model=self._model)
        # graph = StateGraph(...)
        # self._graph = graph.compile()
        pass
    
    async def invoke(self, input: AgentInput) -> AgentOutput:
        """Execute graph synchronously."""
        if not self._graph:
            await self.setup()
        
        # TODO: Implement
        # result = await self._graph.ainvoke({"messages": [...]})
        # return AgentOutput(content=result["messages"][-1].content)
        raise NotImplementedError("Implement with LangGraph")
    
    async def stream(self, input: AgentInput) -> AsyncGenerator[StreamChunk, None]:
        """Execute graph with streaming."""
        if not self._graph:
            await self.setup()
        
        # TODO: Implement
        # async for event in self._graph.astream_events(...):
        #     yield StreamChunk(type="text", content=event["data"])
        raise NotImplementedError("Implement with LangGraph")
        yield
```

### Framework Example: Simple LLM
```python
# src/agent_service/agent/examples/simple_llm_agent.py
"""
Example: Simple LLM agent (no framework).

Install: uv add openai  # or anthropic

Claude Code: Use this for simple LLM-based agents without a framework.
"""
from typing import AsyncGenerator

from agent_service.interfaces import IAgent, AgentInput, AgentOutput, StreamChunk


class SimpleLLMAgent(IAgent):
    """
    Direct LLM agent without a framework.
    
    Good for simple use cases without complex workflows.
    """
    
    def __init__(self, provider: str = "openai", model: str = "gpt-4o-mini"):
        self._provider = provider
        self._model = model
        self._client = None
    
    @property
    def name(self) -> str:
        return "simple-llm"
    
    @property
    def description(self) -> str:
        return f"Simple {self._provider} agent"
    
    async def setup(self) -> None:
        """Initialize LLM client."""
        if self._provider == "openai":
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI()
        # Add other providers as needed
    
    async def invoke(self, input: AgentInput) -> AgentOutput:
        if not self._client:
            await self.setup()
        
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": input.message}],
        )
        return AgentOutput(content=response.choices[0].message.content)
    
    async def stream(self, input: AgentInput) -> AsyncGenerator[StreamChunk, None]:
        if not self._client:
            await self.setup()
        
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": input.message}],
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield StreamChunk(type="text", content=chunk.choices[0].delta.content)
```

### Registration on Startup
```python
# In src/agent_service/api/app.py lifespan:

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register default agent
    from agent_service.agent.registry import agent_registry
    from agent_service.agent.placeholder import PlaceholderAgent
    
    agent = PlaceholderAgent()
    await agent.setup()
    agent_registry.register(agent, default=True)
    
    yield
    
    await agent.teardown()
```

## Pattern for Claude Code

When adding a new agent:
```python
# 1. Create agent implementing IAgent
class MyAgent(IAgent):
    @property
    def name(self) -> str:
        return "my-agent"
    
    async def invoke(self, input: AgentInput) -> AgentOutput:
        # Your implementation
        ...
    
    async def stream(self, input: AgentInput) -> AsyncGenerator[StreamChunk, None]:
        # Your implementation
        ...

# 2. Register in startup
agent_registry.register(MyAgent(), default=True)
```

## Acceptance Criteria
- [ ] IAgent interface is clear and documented
- [ ] PlaceholderAgent works for testing
- [ ] Registry allows multiple agents
- [ ] Framework examples show patterns
