# Task 01: Project Structure & Scaffold

## Objective
Create the directory structure and dependency file that establishes where all code belongs.

## Deliverables

### Directory Structure
```
agent-microservice/
├── src/
│   └── agent_service/
│       ├── __init__.py
│       ├── main.py                    # App entrypoint
│       │
│       ├── interfaces/                # ⭐ CONTRACTS - Claude Code implements these
│       │   ├── __init__.py
│       │   ├── agent.py               # IAgent abstract class
│       │   ├── tool.py                # ITool abstract class
│       │   ├── protocol.py            # IProtocolHandler abstract class
│       │   └── repository.py          # IRepository generic interface
│       │
│       ├── config/
│       │   ├── __init__.py
│       │   └── settings.py            # Pydantic Settings
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── app.py                 # FastAPI app factory
│       │   ├── dependencies.py        # Dependency injection
│       │   ├── routes/
│       │   │   ├── __init__.py
│       │   │   ├── health.py
│       │   │   └── agents.py
│       │   └── middleware/
│       │       ├── __init__.py
│       │       ├── logging.py
│       │       └── errors.py
│       │
│       ├── protocols/                  # Protocol implementations
│       │   ├── __init__.py
│       │   ├── mcp/
│       │   │   ├── __init__.py
│       │   │   └── handler.py         # Implements IProtocolHandler
│       │   ├── a2a/
│       │   │   ├── __init__.py
│       │   │   └── handler.py
│       │   └── agui/
│       │       ├── __init__.py
│       │       └── handler.py
│       │
│       ├── agent/                      # Agent implementations
│       │   ├── __init__.py
│       │   ├── base.py                # Default IAgent implementation
│       │   └── registry.py            # Agent registry
│       │
│       ├── tools/                      # Tool implementations
│       │   ├── __init__.py
│       │   ├── registry.py            # Tool registry
│       │   └── examples/
│       │       └── echo.py            # Example tool implementing ITool
│       │
│       ├── infrastructure/
│       │   ├── __init__.py
│       │   ├── database/
│       │   │   ├── __init__.py
│       │   │   ├── connection.py
│       │   │   ├── base_model.py
│       │   │   └── repositories/
│       │   │       └── __init__.py
│       │   ├── cache/
│       │   │   ├── __init__.py
│       │   │   └── redis.py
│       │   └── observability/
│       │       ├── __init__.py
│       │       ├── logging.py
│       │       ├── metrics.py
│       │       └── tracing.py
│       │
│       └── domain/
│           ├── __init__.py
│           ├── models.py              # Domain entities
│           ├── events.py              # Domain events
│           └── exceptions.py          # Domain exceptions
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   └── integration/
│
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── scripts/
│   └── dev.sh
│
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

### pyproject.toml
```toml
[project]
name = "agent-service"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    # Core
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    
    # Database
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    
    # Cache
    "redis>=5.2.0",
    
    # Observability
    "structlog>=24.4.0",
    "prometheus-client>=0.21.0",
    
    # HTTP
    "httpx>=0.28.0",
    "sse-starlette>=2.1.0",
    
    # Utilities
    "tenacity>=9.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
]

# Agent frameworks - install what you need
langgraph = ["langgraph>=0.2.0", "langchain-core>=0.3.0"]
autogen = ["autogen-agentchat>=0.4.0"]
crewai = ["crewai>=0.1.0"]

# Protocol SDKs - install what you need  
mcp = ["fastmcp>=2.0.0"]
a2a = ["a2a-sdk>=0.2.0"]
agui = ["ag-ui-protocol>=0.1.0"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### Key Conventions for Claude Code

1. **New tools** → Create in `src/agent_service/tools/` implementing `ITool`
2. **New agent** → Create in `src/agent_service/agent/` implementing `IAgent`
3. **New protocol** → Create in `src/agent_service/protocols/` implementing `IProtocolHandler`
4. **New DB model** → Create in `src/agent_service/infrastructure/database/` extending `BaseModel`
5. **New route** → Create in `src/agent_service/api/routes/`

## Acceptance Criteria
- [ ] All directories exist with `__init__.py`
- [ ] `pyproject.toml` allows installing with `uv sync`
- [ ] Framework/protocol dependencies are optional extras
- [ ] README explains the structure
