# Quick Start Guide

Get your agent service running in 5 minutes.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.12+ (for local development)
- Git

## Step 1: Clone and Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd agents_boiler_plate

# Copy environment file
cp .env.example .env

# Edit .env if needed (optional for local development)
# The defaults work out of the box for Docker Compose
```

## Step 2: Run Locally with Docker Compose

```bash
# Start all services (API, Workers, PostgreSQL, Redis, Prometheus, Grafana)
docker-compose -f docker/docker-compose.yml up -d

# Wait for services to be ready (30-60 seconds)
# Check health
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-12-14T10:30:00.000Z",
  "checks": {
    "database": "healthy",
    "redis": "healthy"
  }
}
```

## Step 3: Access the Services

- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Alternative API Docs**: http://localhost:8000/redoc (ReDoc)
- **Metrics**: http://localhost:8000/metrics (Prometheus format)
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

## Step 4: Create Your First Agent

Create a simple agent file:

```bash
# Create agent file
cat > src/agent_service/agent/custom/hello_agent.py << 'EOF'
"""Simple hello world agent."""
from typing import AsyncGenerator
from agent_service.interfaces import IAgent, AgentInput, AgentOutput, StreamChunk


class HelloAgent(IAgent):
    """A simple hello world agent."""

    @property
    def name(self) -> str:
        return "hello-agent"

    @property
    def description(self) -> str:
        return "A friendly greeting agent"

    async def invoke(self, input: AgentInput) -> AgentOutput:
        """Return a greeting."""
        greeting = f"Hello {input.message}! I'm a simple agent."
        return AgentOutput(content=greeting)

    async def stream(self, input: AgentInput) -> AsyncGenerator[StreamChunk, None]:
        """Stream the greeting word by word."""
        words = f"Hello {input.message}! I'm a simple agent.".split()
        for word in words:
            yield StreamChunk(type="text", content=word + " ")
EOF
```

The agent is automatically discovered - no registration needed!

## Step 5: Make Your First API Call

### Using curl

```bash
# Invoke the agent
curl -X POST http://localhost:8000/api/v1/agents/hello-agent/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "message": "World",
    "session_id": "test-session"
  }'
```

Expected response:
```json
{
  "content": "Hello World! I'm a simple agent.",
  "tool_calls": null,
  "metadata": null
}
```

### Using Python

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/agents/hello-agent/invoke",
    json={
        "message": "World",
        "session_id": "test-session"
    }
)

print(response.json())
# {'content': "Hello World! I'm a simple agent.", 'tool_calls': None, 'metadata': None}
```

### Using the Swagger UI

1. Navigate to http://localhost:8000/docs
2. Find the `/api/v1/agents/{agent_name}/invoke` endpoint
3. Click "Try it out"
4. Enter `hello-agent` for agent_name
5. Enter request body:
   ```json
   {
     "message": "World",
     "session_id": "test-session"
   }
   ```
6. Click "Execute"

## Step 6: Test Streaming

```bash
# Stream the response
curl -X POST http://localhost:8000/api/v1/agents/hello-agent/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "World",
    "session_id": "test-session"
  }'
```

You'll see the response streamed word by word.

## Viewing Logs

```bash
# View all logs
docker-compose -f docker/docker-compose.yml logs -f

# View API logs only
docker-compose -f docker/docker-compose.yml logs -f api

# View worker logs
docker-compose -f docker/docker-compose.yml logs -f worker
```

## Stopping the Services

```bash
# Stop all services
docker-compose -f docker/docker-compose.yml down

# Stop and remove volumes (WARNING: deletes database data)
docker-compose -f docker/docker-compose.yml down -v
```

## Next Steps

- **Build a real agent**: See [Build Your First Agent](./first-agent.md)
- **Add authentication**: See [Authentication Guide](./api/authentication.md)
- **Add tools**: See [Tool System](./api/tools.md)
- **Deploy to production**: See [Installation Guide](./installation.md)

## Troubleshooting

### Port already in use
If port 8000 is already in use, modify `docker/docker-compose.yml`:
```yaml
services:
  api:
    ports:
      - "8001:8000"  # Change 8000 to 8001 (or any available port)
```

### Services not starting
```bash
# Check service status
docker-compose -f docker/docker-compose.yml ps

# Check logs for errors
docker-compose -f docker/docker-compose.yml logs

# Restart services
docker-compose -f docker/docker-compose.yml restart
```

### Database connection errors
```bash
# Wait for PostgreSQL to be ready
docker-compose -f docker/docker-compose.yml exec postgres pg_isready -U postgres

# Check database logs
docker-compose -f docker/docker-compose.yml logs postgres
```

## Local Development (Without Docker)

```bash
# Install dependencies
pip install uv
uv sync

# Start PostgreSQL and Redis separately (or use Docker for just these)
docker-compose -f docker/docker-compose.yml up -d postgres redis

# Set environment variables
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/agent_db
export REDIS_URL=redis://localhost:6379/0

# Run migrations
alembic upgrade head

# Start the API server
uvicorn agent_service.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000 with auto-reload on code changes.
