# Task 10: Docker & Development Scripts

## Objective
Create Docker setup and development scripts for consistent local development.

## Deliverables

### Dockerfile
```dockerfile
# docker/Dockerfile
FROM python:3.11-slim AS base

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Development stage
FROM base AS dev
RUN uv sync --frozen
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
CMD ["uvicorn", "agent_service.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base AS prod
RUN uv sync --frozen --no-dev
COPY src/ src/
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
# Create non-root user
RUN useradd -r -s /bin/false appuser && chown -R appuser /app
USER appuser
CMD ["uvicorn", "agent_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose
```yaml
# docker/docker-compose.yml
version: "3.9"

services:
  api:
    build:
      context: ..
      dockerfile: docker/Dockerfile
      target: dev
    ports:
      - "8000:8000"
    volumes:
      - ../src:/app/src:cached
      - ../tests:/app/tests:cached
    environment:
      - ENVIRONMENT=local
      - DEBUG=true
      - LOG_LEVEL=DEBUG
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/agent_db
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=dev-secret-not-for-production
    env_file:
      - ../.env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  postgres:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=agent_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
```

### Development Script
```bash
#!/bin/bash
# scripts/dev.sh - Development helper script

set -e

COMPOSE_FILE="docker/docker-compose.yml"

case "$1" in
  start)
    echo "Starting development environment..."
    docker compose -f $COMPOSE_FILE up -d --build
    echo ""
    echo "✓ API: http://localhost:8000"
    echo "✓ Docs: http://localhost:8000/docs"
    echo "✓ Health: http://localhost:8000/health/live"
    ;;
  
  stop)
    echo "Stopping development environment..."
    docker compose -f $COMPOSE_FILE down
    ;;
  
  logs)
    docker compose -f $COMPOSE_FILE logs -f api
    ;;
  
  shell)
    docker compose -f $COMPOSE_FILE exec api bash
    ;;
  
  test)
    echo "Running tests..."
    docker compose -f $COMPOSE_FILE exec api pytest tests/ -v
    ;;
  
  lint)
    echo "Running linter..."
    docker compose -f $COMPOSE_FILE exec api ruff check src/
    ;;
  
  format)
    echo "Formatting code..."
    docker compose -f $COMPOSE_FILE exec api ruff format src/
    ;;
  
  migrate)
    echo "Running migrations..."
    docker compose -f $COMPOSE_FILE exec api alembic upgrade head
    ;;
  
  reset)
    echo "Resetting environment..."
    docker compose -f $COMPOSE_FILE down -v
    docker compose -f $COMPOSE_FILE up -d --build
    ;;
  
  *)
    echo "Usage: $0 {start|stop|logs|shell|test|lint|format|migrate|reset}"
    exit 1
    ;;
esac
```

### Makefile (Alternative)
```makefile
# Makefile
.PHONY: help start stop logs shell test lint format migrate reset

COMPOSE = docker compose -f docker/docker-compose.yml

help:
	@echo "Commands:"
	@echo "  start   - Start dev environment"
	@echo "  stop    - Stop dev environment"
	@echo "  logs    - View API logs"
	@echo "  shell   - Open shell in API container"
	@echo "  test    - Run tests"
	@echo "  lint    - Run linter"
	@echo "  format  - Format code"
	@echo "  migrate - Run DB migrations"
	@echo "  reset   - Reset environment"

start:
	$(COMPOSE) up -d --build
	@echo "API: http://localhost:8000"

stop:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f api

shell:
	$(COMPOSE) exec api bash

test:
	$(COMPOSE) exec api pytest tests/ -v

lint:
	$(COMPOSE) exec api ruff check src/

format:
	$(COMPOSE) exec api ruff format src/

migrate:
	$(COMPOSE) exec api alembic upgrade head

reset:
	$(COMPOSE) down -v
	$(COMPOSE) up -d --build
```

### .gitignore
```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
*.egg-info/

# Environment
.env
.env.local

# IDE
.idea/
.vscode/
*.swp

# Docker
docker/data/

# Testing
.pytest_cache/
.coverage
htmlcov/

# Build
dist/
build/

# OS
.DS_Store
```

### README.md Template
```markdown
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
```

## Acceptance Criteria
- [ ] `./scripts/dev.sh start` brings up environment
- [ ] Hot reload works for code changes
- [ ] PostgreSQL and Redis accessible
- [ ] Tests run in container
- [ ] README explains usage
