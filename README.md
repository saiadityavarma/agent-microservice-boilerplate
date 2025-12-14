# Agent Microservice

Production-ready agent microservice boilerplate with MCP, A2A, and AG-UI protocol support.

## Quick Start

```bash
# Start development environment
./scripts/dev.sh start
# or: make start

# View logs
./scripts/dev.sh logs

# Run tests
./scripts/dev.sh test
```

## Architecture

See `src/agent_service/interfaces/` for core contracts:
- `IAgent` - Agent implementations
- `ITool` - Tool implementations
- `IProtocolHandler` - Protocol handlers

## Adding Features

### New Tool
```python
# src/agent_service/tools/my_tool.py
from agent_service.interfaces import ITool, ToolSchema

class MyTool(ITool):
    # See Task 08 for full example
```

### New Agent
```python
# src/agent_service/agent/my_agent.py
from agent_service.interfaces import IAgent

class MyAgent(IAgent):
    # See Task 07 for full example
```

## Configuration

Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- Health: http://localhost:8000/health/live
- Metrics: http://localhost:8000/metrics
