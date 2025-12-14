# Agent Service - Project Context for Claude

This document provides essential context for Claude Code when working with this agent microservice boilerplate.

## Project Overview

A production-ready, framework-agnostic agent microservice boilerplate with:
- Interface-based architecture (IAgent, ITool, IProtocolHandler)
- Multi-protocol support (MCP, A2A, AG-UI)
- Production patterns (auth, observability, deployment)
- Automatic discovery and registration

**Key Philosophy**: Claude Code should implement interfaces, not modify core infrastructure.

## Architecture

```
src/agent_service/
├── interfaces/          # THE CONTRACTS - implement these
│   ├── agent.py        # IAgent interface
│   ├── tool.py         # ITool interface
│   ├── protocol.py     # IProtocolHandler interface
│   └── repository.py   # IRepository interface
│
├── agent/
│   ├── examples/       # Reference implementations
│   └── custom/         # ADD NEW AGENTS HERE (auto-discovered)
│
├── tools/
│   ├── examples/       # Reference implementations
│   └── custom/         # ADD NEW TOOLS HERE (auto-discovered)
│
├── protocols/          # MCP, A2A, AG-UI implementations
├── api/                # FastAPI routes and middleware
├── auth/               # Authentication (Azure AD, Cognito, API keys)
├── config/             # Pydantic settings pattern
├── domain/             # Domain models and exceptions
├── infrastructure/     # Database, cache, observability
└── workers/            # Celery background tasks
```

## Key Patterns and Conventions

### 1. Agent Implementation Pattern

All agents must implement `IAgent`:

```python
from agent_service.interfaces import IAgent, AgentInput, AgentOutput, StreamChunk
from typing import AsyncGenerator

class MyAgent(IAgent):
    @property
    def name(self) -> str:
        return "my-agent"  # Unique identifier, kebab-case

    @property
    def description(self) -> str:
        return "Clear description of what this agent does"

    async def invoke(self, input: AgentInput) -> AgentOutput:
        # Synchronous execution
        return AgentOutput(content="response")

    async def stream(self, input: AgentInput) -> AsyncGenerator[StreamChunk, None]:
        # Streaming execution
        yield StreamChunk(type="text", content="word ")
```

**Location**: `src/agent_service/agent/custom/{name}_agent.py`

**Auto-discovery**: Agents in `custom/` are automatically registered on startup.

### 2. Tool Implementation Pattern

All tools must implement `ITool`:

```python
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
                    "param": {"type": "string", "description": "Parameter description"}
                },
                "required": ["param"]
            }
        )

    async def execute(self, param: str, **kwargs) -> dict:
        # Tool implementation
        return {"result": "value"}

    @property
    def requires_confirmation(self) -> bool:
        return False  # True for destructive operations
```

**Location**: `src/agent_service/tools/custom/{name}_tool.py`

**Auto-discovery**: Tools in `custom/` are automatically available.

### 3. Naming Conventions

- **Files**: `snake_case` (e.g., `weather_agent.py`, `http_request_tool.py`)
- **Classes**: `PascalCase` (e.g., `WeatherAgent`, `HTTPRequestTool`)
- **Agent names**: `kebab-case` (e.g., `weather-agent`, `simple-llm`)
- **Tool names**: `snake_case` (e.g., `get_weather`, `send_email`)
- **Environment variables**: `UPPER_SNAKE_CASE` (e.g., `DATABASE_URL`)

### 4. Error Handling Pattern

```python
from agent_service.domain.exceptions import AgentError, ToolExecutionError
import logging

logger = logging.getLogger(__name__)

class MyAgent(IAgent):
    async def invoke(self, input: AgentInput) -> AgentOutput:
        try:
            # Your logic
            result = await self._process(input)
            return AgentOutput(content=result)

        except ToolExecutionError as e:
            logger.error(f"Tool execution failed: {e}", exc_info=True)
            return AgentOutput(
                content="I encountered an error while using a tool.",
                metadata={"error": str(e)}
            )

        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise AgentError(f"Agent execution failed: {str(e)}")
```

### 5. Testing Pattern

```python
# tests/unit/agents/test_my_agent.py
import pytest
from agent_service.agent.custom.my_agent import MyAgent
from agent_service.interfaces import AgentInput

@pytest.fixture
def my_agent():
    return MyAgent()

@pytest.mark.asyncio
async def test_invoke(my_agent):
    result = await my_agent.invoke(AgentInput(
        message="test message",
        session_id="test"
    ))
    assert result.content is not None

@pytest.mark.asyncio
async def test_stream(my_agent):
    chunks = []
    async for chunk in my_agent.stream(AgentInput(message="test", session_id="test")):
        chunks.append(chunk)
    assert len(chunks) > 0
```

**Test locations**:
- Unit tests: `tests/unit/{module}/test_{name}.py`
- Integration tests: `tests/integration/{module}/test_{name}.py`
- E2E tests: `tests/e2e/test_{feature}.py`

### 6. Observability Pattern

```python
from agent_service.infrastructure.observability.logging import get_logger
from agent_service.infrastructure.observability.tracing import trace_async
from agent_service.infrastructure.observability.metrics import metrics

logger = get_logger(__name__)

class MyAgent(IAgent):
    @trace_async(span_name="my_agent.invoke")
    async def invoke(self, input: AgentInput) -> AgentOutput:
        logger.info("Processing request", extra={
            "agent": self.name,
            "session_id": input.session_id
        })

        metrics.increment("agent.invocations", tags={"agent": self.name})

        # Your implementation
        # ...
```

## Where to Find Things

### Configuration
- Environment variables: `.env` (copy from `.env.example`)
- Settings classes: `src/agent_service/config/`
- Secrets management: `src/agent_service/config/secrets.py`

### Database
- Models: `src/agent_service/infrastructure/database/models/`
- Migrations: `alembic/versions/`
- Base model: `src/agent_service/infrastructure/database/base_model.py`

### API
- Routes: `src/agent_service/api/routes/`
- Middleware: `src/agent_service/api/middleware/`
- Dependencies: `src/agent_service/api/dependencies.py`

### Authentication
- Providers: `src/agent_service/auth/providers/` (Azure AD, Cognito)
- API keys: `src/agent_service/auth/api_key.py`
- RBAC: `src/agent_service/auth/rbac/`

### Deployment
- Docker: `docker/` (Dockerfile, docker-compose.yml)
- Kubernetes: `k8s/` (manifests)
- Helm: `helm/agent-service/`
- Monitoring: `monitoring/` (Prometheus, Grafana configs)

### Documentation
- Quick start: `docs/quickstart.md`
- Installation: `docs/installation.md`
- First agent: `docs/first-agent.md`
- API reference: `docs/api/`

## Common Tasks

### Add a New Agent

1. Create file: `src/agent_service/agent/custom/{name}_agent.py`
2. Implement `IAgent` interface
3. Add tests: `tests/unit/agents/test_{name}_agent.py`
4. Restart service (auto-discovered)

Use slash command: `/new-agent {name}`

### Add a New Tool

1. Create file: `src/agent_service/tools/custom/{name}_tool.py`
2. Implement `ITool` interface
3. Add tests: `tests/unit/tools/test_{name}_tool.py`
4. Use in agent

Use slash command: `/new-tool {name}`

### Add Authentication

1. Edit `.env`:
   ```bash
   AUTH_PROVIDER=azure_ad  # or aws_cognito
   AZURE_TENANT_ID=your-tenant-id
   AZURE_CLIENT_ID=your-client-id
   AZURE_CLIENT_SECRET=your-secret
   ```
2. Restart service
3. See `docs/api/authentication.md` for details

### Add Database Model

1. Create model: `src/agent_service/infrastructure/database/models/{name}.py`
   - Inherit from `BaseModel`
   - Use SQLAlchemy 2.0 style

2. Create migration:
   ```bash
   alembic revision --autogenerate -m "add {name} table"
   ```

3. Apply migration:
   ```bash
   alembic upgrade head
   ```

### Deploy Changes

Use slash command: `/deploy`

Or manually:
```bash
# Build image
docker build -f docker/Dockerfile -t agent-service:v1.x.x --target prod .

# Push to registry
docker push your-registry/agent-service:v1.x.x

# Update Kubernetes
kubectl set image deployment/agent-service-api api=your-registry/agent-service:v1.x.x -n agent-service
```

## Important Files

### Core Interfaces (READ THESE FIRST)
- `src/agent_service/interfaces/agent.py` - Agent contract
- `src/agent_service/interfaces/tool.py` - Tool contract
- `src/agent_service/interfaces/protocol.py` - Protocol contract
- `src/agent_service/interfaces/repository.py` - Repository pattern

### Reference Implementations
- `src/agent_service/agent/examples/simple_llm_agent.py` - Simple LLM agent
- `src/agent_service/agent/examples/langgraph_agent.py` - LangGraph agent
- `src/agent_service/tools/examples/http_request.py` - HTTP tool
- `src/agent_service/tools/examples/echo.py` - Echo tool

### Configuration
- `.env.example` - All available environment variables
- `src/agent_service/config/__init__.py` - Settings pattern
- `pyproject.toml` - Dependencies and project metadata

### Entry Points
- `src/agent_service/main.py` - FastAPI application
- `docker/docker-compose.yml` - Local development stack
- `k8s/deployment.yaml` - Kubernetes deployment

## Development Workflow

### Local Development

```bash
# Start infrastructure
docker-compose -f docker/docker-compose.yml up -d postgres redis

# Install dependencies
uv sync

# Run migrations
alembic upgrade head

# Start API
uvicorn agent_service.main:app --reload
```

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/agents/test_my_agent.py -v

# Run with coverage
pytest --cov=src/agent_service --cov-report=html

# Run integration tests only
pytest tests/integration/ -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## Environment Variables Reference

### Required
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - JWT signing key (min 32 chars)
- `ENVIRONMENT` - local, development, staging, production

### Authentication
- `AUTH_PROVIDER` - azure_ad, aws_cognito, none
- `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` - For Azure AD
- `AWS_COGNITO_USER_POOL_ID`, `AWS_COGNITO_CLIENT_ID` - For Cognito

### Feature Flags
- `ENABLE_MCP` - Enable MCP protocol (default: true)
- `ENABLE_A2A` - Enable A2A protocol (default: true)
- `ENABLE_AGUI` - Enable AG-UI protocol (default: true)

### Observability
- `SENTRY_DSN` - Sentry error tracking
- `OTLP_ENDPOINT` - OpenTelemetry endpoint
- `LOG_LEVEL` - DEBUG, INFO, WARNING, ERROR

See `.env.example` for complete list.

## Common Pitfalls to Avoid

1. **Don't modify core interfaces** - Implement them, don't change them
2. **Don't skip async/await** - All I/O operations must be async
3. **Don't hardcode config** - Use environment variables via Settings
4. **Don't forget error handling** - Always handle exceptions gracefully
5. **Don't skip tests** - Write tests for new agents and tools
6. **Don't commit secrets** - Use `.env` (gitignored) for local secrets
7. **Don't use blocking I/O** - Use async clients (httpx, asyncpg, etc.)
8. **Don't forget logging** - Add structured logging with context
9. **Don't skip auto-discovery** - Put code in `custom/` directories
10. **Don't modify examples** - Copy and adapt, don't change originals

## Getting Help

- **Documentation**: `docs/` directory
- **Examples**: `examples/` directory
- **Reference implementations**: `src/agent_service/*/examples/`
- **Slash commands**: Use `/new-agent`, `/new-tool`, `/deploy`
- **API docs**: http://localhost:8000/docs (when running)

## Quick Reference

### Agent Skeleton
```python
from agent_service.interfaces import IAgent, AgentInput, AgentOutput, StreamChunk
from typing import AsyncGenerator

class MyAgent(IAgent):
    @property
    def name(self) -> str:
        return "my-agent"

    @property
    def description(self) -> str:
        return "Agent description"

    async def invoke(self, input: AgentInput) -> AgentOutput:
        return AgentOutput(content="response")

    async def stream(self, input: AgentInput) -> AsyncGenerator[StreamChunk, None]:
        yield StreamChunk(type="text", content="chunk")
```

### Tool Skeleton
```python
from agent_service.interfaces import ITool, ToolSchema

class MyTool(ITool):
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="my_tool",
            description="Tool description",
            parameters={"type": "object", "properties": {}}
        )

    async def execute(self, **kwargs) -> dict:
        return {"result": "value"}
```

### Test Skeleton
```python
import pytest
from agent_service.agent.custom.my_agent import MyAgent
from agent_service.interfaces import AgentInput

@pytest.mark.asyncio
async def test_my_agent():
    agent = MyAgent()
    result = await agent.invoke(AgentInput(message="test", session_id="test"))
    assert result.content is not None
```

---

**Last Updated**: 2024-12-14

**Project Path**: `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/`
