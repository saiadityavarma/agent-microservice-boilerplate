# Agent Examples

Comprehensive examples demonstrating different agent patterns and capabilities.

## Overview

This directory contains production-ready examples for building AI agents. Each example is self-contained, well-documented, and includes tests.

## Examples

### 1. Chatbot (`chatbot/`)

A conversational agent with session-based memory.

**Key Features:**
- Conversation history management
- Session storage
- Streaming responses
- Easy LLM integration (OpenAI, Anthropic)

**Best For:**
- Building conversational interfaces
- Customer support bots
- Interactive assistants

**Quick Start:**
```python
from agent_service.agent import agent_registry
from agent_service.interfaces import AgentInput

chatbot = agent_registry.get("simple_chatbot")
result = await chatbot.invoke(AgentInput(
    message="Hello!",
    session_id="user_123"
))
```

**Learn More:** [chatbot/README.md](chatbot/README.md)

---

### 2. RAG Agent (`rag-agent/`)

Retrieval Augmented Generation agent with document search.

**Key Features:**
- Semantic document search
- Vector database integration
- Source citations
- Document management

**Best For:**
- Question answering systems
- Knowledge base assistants
- Documentation bots
- Research assistants

**Quick Start:**
```python
from agent_service.agent import agent_registry
from agent_service.interfaces import AgentInput

# Add documents
doc_manager = agent_registry.get("document_manager")
await doc_manager.invoke(AgentInput(
    message="add: title: Python Guide | Python is a programming language..."
))

# Query
rag = agent_registry.get("rag_agent")
result = await rag.invoke(AgentInput(
    message="What is Python?"
))
```

**Learn More:** [rag-agent/README.md](rag-agent/README.md)

---

### 3. Multi-Agent System (`multi-agent/`)

Collaborative system with specialized agents.

**Key Features:**
- Sequential workflows
- Parallel execution
- Adaptive orchestration
- Agent-to-agent communication

**Best For:**
- Complex content creation
- Multi-step workflows
- Quality assurance pipelines
- Collaborative tasks

**Quick Start:**
```python
from agent_service.agent import agent_registry
from agent_service.interfaces import AgentInput

# Orchestrated workflow: Research -> Write -> Review
orchestrator = agent_registry.get("content_orchestrator")
result = await orchestrator.invoke(AgentInput(
    message="Python programming language"
))
```

**Learn More:** [multi-agent/README.md](multi-agent/README.md)

---

### 4. Tool-Using Agent (`tool-use/`)

Agent that uses multiple tools to accomplish tasks.

**Key Features:**
- Dynamic tool selection
- Tool chaining
- Parallel tool execution
- Custom tool creation

**Best For:**
- Task automation
- Data processing
- API integration
- Computational tasks

**Quick Start:**
```python
from agent_service.agent import agent_registry
from agent_service.interfaces import AgentInput

tool_agent = agent_registry.get("tool_agent")

# Calculate
result = await tool_agent.invoke(AgentInput(
    message="Calculate 25 * 4 + 10"
))

# Search
result = await tool_agent.invoke(AgentInput(
    message="Search for Python tutorials"
))
```

**Learn More:** [tool-use/README.md](tool-use/README.md)

---

## Installation

All examples use the base agent framework:

```bash
# Install base dependencies
cd /Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate
pip install -e .

# For development and testing
pip install -e ".[dev]"
```

## Running Examples

### Option 1: Direct Execution

Each example can be run directly:

```bash
# Chatbot
python examples/chatbot/agent.py

# RAG Agent
python examples/rag-agent/agent.py

# Multi-Agent
python examples/multi-agent/orchestrator.py

# Tool-Use
python examples/tool-use/agent.py
```

### Option 2: Interactive Usage

```python
import asyncio
from agent_service.agent import agent_registry
from agent_service.interfaces import AgentInput

# Import examples to register agents
from examples.chatbot import agent as chatbot
from examples.rag_agent import agent as rag
from examples.multi_agent import agents, orchestrator
from examples.tool_use import agent, tools

async def main():
    # List all registered agents
    for name in agent_registry.list():
        print(f"- {name}")

    # Use any agent
    agent = agent_registry.get("simple_chatbot")
    result = await agent.invoke(AgentInput(message="Hello!"))
    print(result.content)

asyncio.run(main())
```

## Testing

Run all example tests:

```bash
pytest examples/ -v
```

Run tests for specific example:

```bash
pytest examples/chatbot/test_chatbot.py -v
pytest examples/rag-agent/test_rag_agent.py -v
pytest examples/multi-agent/test_multi_agent.py -v
pytest examples/tool-use/test_tool_use.py -v
```

## Comparison Matrix

| Feature | Chatbot | RAG Agent | Multi-Agent | Tool-Use |
|---------|---------|-----------|-------------|----------|
| Conversation Memory | ✅ | ❌ | ❌ | ❌ |
| Document Search | ❌ | ✅ | ❌ | ❌ |
| Multiple Agents | ❌ | ❌ | ✅ | ❌ |
| Tool Usage | ❌ | ✅ | ✅ | ✅ |
| Streaming | ✅ | ✅ | ❌ | ❌ |
| Complexity | Low | Medium | High | Medium |
| Best For | Chat | Q&A | Workflows | Automation |

## Combining Examples

Examples can be combined for more powerful agents:

### Chatbot + RAG

```python
@agent(name="rag_chatbot")
async def rag_chatbot(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    """Chatbot with RAG capabilities."""
    # Get conversation history
    history = await get_history(input.session_id, ctx)

    # Search documents
    docs = await ctx.call_tool("search_documents", query=input.message)

    # Generate response with context
    response = await generate_with_context(
        message=input.message,
        history=history,
        documents=docs
    )

    # Save to history
    await save_history(input.session_id, input.message, response, ctx)

    return AgentOutput(content=response)
```

### Multi-Agent + Tools

```python
@agent(name="tool_orchestrator")
async def tool_orchestrator(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    """Orchestrator that delegates to tool-using agents."""
    # Research agent uses search tools
    researcher = agent_registry.get("researcher_agent")
    research = await researcher.invoke(input)

    # Data agent uses processing tools
    processor = agent_registry.get("data_processor_agent")
    processed = await processor.invoke(AgentInput(message=research.content))

    return processed
```

### RAG + Multi-Agent

```python
@agent(name="knowledge_orchestrator")
async def knowledge_orchestrator(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    """Multi-agent system with RAG capabilities."""
    # Each agent has access to RAG
    researcher = agent_registry.get("researcher_agent")
    writer = agent_registry.get("writer_agent")

    # Research with RAG
    research = await researcher.invoke(input)

    # Write with RAG for fact-checking
    article = await writer.invoke(AgentInput(message=research.content))

    return article
```

## Architecture Patterns

### Pattern 1: Simple Agent

```
User Input → Agent → LLM → Response
```

**Examples:** Chatbot (basic mode)

### Pattern 2: Tool-Augmented Agent

```
User Input → Agent → Tool Selection → Tool Execution → Response
```

**Examples:** Tool-Use Agent

### Pattern 3: RAG Pattern

```
User Input → Query → Vector Search → Context Retrieval → LLM + Context → Response
```

**Examples:** RAG Agent

### Pattern 4: Multi-Agent Pipeline

```
User Input → Orchestrator → Agent 1 → Agent 2 → Agent 3 → Final Response
```

**Examples:** Multi-Agent (Sequential)

### Pattern 5: Multi-Agent Parallel

```
                    ┌→ Agent 1 →┐
User Input → Orchestrator → Agent 2 → Aggregator → Response
                    └→ Agent 3 →┘
```

**Examples:** Multi-Agent (Parallel)

## Best Practices

### 1. Error Handling

All examples demonstrate proper error handling:

```python
try:
    result = await agent.invoke(input)
except Exception as e:
    ctx.logger.error("agent_failed", error=str(e))
    return AgentOutput(content=f"Error: {str(e)}")
```

### 2. Logging

Use structured logging for observability:

```python
ctx.logger.info("operation_started", param=value)
ctx.logger.info("operation_completed", duration=duration)
```

### 3. Caching

Cache expensive operations:

```python
cache_key = f"result:{hash(input.message)}"
cached = await ctx.cache.get(cache_key)
if cached:
    return cached

result = await expensive_operation()
await ctx.cache.set(cache_key, result, ttl=3600)
```

### 4. Testing

Write comprehensive tests:

```python
@pytest.mark.asyncio
async def test_agent(agent_context):
    result = await agent(input, agent_context)
    assert isinstance(result, AgentOutput)
    assert len(result.content) > 0
```

## Production Deployment

### Environment Variables

Create `.env` file:

```bash
# LLM API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Vector Database
PINECONE_API_KEY=...
PINECONE_ENVIRONMENT=...

# Other Services
GOOGLE_API_KEY=...
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements/base.txt .
RUN pip install -r base.txt

COPY src/ ./src/
COPY examples/ ./examples/

CMD ["uvicorn", "src.agent_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes

See main [DEPLOYMENT.md](/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/DEPLOYMENT.md) for Kubernetes deployment.

## Common Issues

### Issue: Agent not registered

**Solution:** Import the agent module before using:

```python
from examples.chatbot import agent  # This registers the agent
chatbot = agent_registry.get("simple_chatbot")
```

### Issue: Tools not found

**Solution:** Import tools module:

```python
from examples.rag_agent import tools  # Registers tools
from examples.tool_use import tools  # Registers tools
```

### Issue: Cache not available

**Solution:** Ensure Redis is running or use in-memory cache:

```bash
# Start Redis
docker run -d -p 6379:6379 redis

# Or configure in-memory cache in config
```

## Next Steps

1. **Customize Examples**: Modify examples for your specific use case
2. **Combine Patterns**: Mix and match different patterns
3. **Add Integrations**: Connect to your APIs and services
4. **Deploy to Production**: Use Docker/Kubernetes deployment
5. **Monitor Performance**: Add metrics and tracing
6. **Scale Up**: Implement load balancing and caching

## Resources

- [Main Documentation](/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/docs/)
- [API Reference](/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/docs/api/)
- [Deployment Guide](/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/DEPLOYMENT.md)
- [Contributing Guidelines](/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/.github/CONTRIBUTING.md)

## Support

For questions and issues:
- Check example READMEs for specific guidance
- Review test files for usage examples
- See main project documentation
- Open an issue on GitHub

## License

All examples are part of the agent-service project and use the same license.
