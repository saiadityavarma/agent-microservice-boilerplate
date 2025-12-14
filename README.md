# Agent Service Boilerplate
<img width="1024" height="559" alt="image" src="https://github.com/user-attachments/assets/ef233f0a-79d7-4a76-a354-ecc483cbd831" />

> **Turn your AI agents into production-ready microservices in minutes, not months.**

## The Problem This Solves

If you're a data scientist or ML engineer, you've likely built amazing AI agents using LangChain, CrewAI, or raw OpenAI calls. But then someone asks: *"Can we deploy this to production?"*

Suddenly you need to figure out:
- Authentication (Azure AD? AWS Cognito? API keys?)
- Database connections and migrations
- Rate limiting and security headers
- Logging, metrics, and tracing
- Docker, Kubernetes, CI/CD pipelines
- Error handling and input validation

**This boilerplate handles ALL of that infrastructure** so you can focus on what you do best: building intelligent agents.

```
┌─────────────────────────────────────────────────────────────────┐
│                    WHAT YOU BUILD                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Your Agent  │  │  Your Tools  │  │  Your Logic  │          │
│  │   (10 lines) │  │   (10 lines) │  │  (whatever)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
├─────────────────────────────────────────────────────────────────┤
│                    WHAT WE HANDLE                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Auth │ Database │ Caching │ Rate Limits │ Logging │ ... │   │
│  │ API  │ Metrics  │ Tracing │ Validation  │ Docker  │ K8s │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Architecture Patterns

This boilerplate implements battle-tested software architecture patterns that enable enterprise-grade agent deployments:

### Clean Architecture / Hexagonal Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer                                 │
│  (FastAPI routes, middleware, request/response handling)        │
├─────────────────────────────────────────────────────────────────┤
│                     Application Layer                            │
│  (Agents, Tools, Business Logic, Use Cases)                     │
├─────────────────────────────────────────────────────────────────┤
│                       Domain Layer                               │
│  (Interfaces, Models, Core Abstractions)                        │
├─────────────────────────────────────────────────────────────────┤
│                   Infrastructure Layer                           │
│  (Database, Cache, External APIs, Observability)                │
└─────────────────────────────────────────────────────────────────┘
```

**Why it matters**: Your agent code is isolated from infrastructure concerns. Swap databases, change auth providers, or migrate to different cloud - your agents don't change.

### Key Patterns Implemented

| Pattern | What It Does | Why You Care |
|---------|--------------|--------------|
| **Repository Pattern** | Abstracts database operations | Switch from PostgreSQL to MongoDB without touching business logic |
| **Dependency Injection** | Services receive dependencies | Easy testing, swappable implementations |
| **Interface Segregation** | Small, focused interfaces (`IAgent`, `ITool`, `IProtocolHandler`) | Implement only what you need |
| **Decorator Pattern** | `@agent` and `@tool` decorators | Write 10 lines instead of 100 |
| **Registry Pattern** | Auto-discovery of agents and tools | Add a file, it's automatically available |
| **Strategy Pattern** | Pluggable auth providers | Same code works with Azure AD, Cognito, or API keys |
| **Middleware Chain** | Request processing pipeline | Add logging, auth, rate limiting without changing handlers |

---

## Agent Communication Protocols

This boilerplate supports three major protocols that enable agents to evolve from standalone scripts to interconnected services:

### MCP (Model Context Protocol)

**What**: Anthropic/Claude's protocol for context sharing between AI models and tools.

**Use Case**: Integrate your agents with Claude Desktop, Claude.ai, or any MCP-compatible client.

```
┌──────────────┐      MCP       ┌──────────────┐
│ Claude       │ ◄────────────► │ Your Agent   │
│ Desktop      │   Context &    │ Service      │
└──────────────┘   Tool Calls   └──────────────┘
```

**Endpoints**:
- `GET /mcp/capabilities` - List available capabilities
- `POST /mcp/invoke` - Invoke agent with MCP context
- `POST /mcp/stream` - Stream agent response
- `GET /mcp/tools` - List available tools

### A2A (Agent-to-Agent Protocol)

**What**: Protocol for agents to discover and collaborate with each other.

**Use Case**: Build multi-agent systems where specialized agents delegate tasks.

```
┌──────────────┐      A2A       ┌──────────────┐
│ Orchestrator │ ◄────────────► │ Weather      │
│ Agent        │   Task Mgmt    │ Agent        │
└──────────────┘                └──────────────┘
        │              A2A             │
        └──────────────────────────────┘
                       │
               ┌──────────────┐
               │ Research     │
               │ Agent        │
               └──────────────┘
```

**Endpoints**:
- `GET /a2a/discover` - Discover available agents
- `POST /a2a/task/create` - Create a task for another agent
- `GET /a2a/task/{id}` - Get task status
- `GET /a2a/agents/{name}` - Get agent capabilities (Agent Card)

### AG-UI (Agent-User Interface Protocol)

**What**: Protocol for agents to return rich UI components, not just text.

**Use Case**: Build interactive agent experiences with charts, forms, buttons.

```
┌──────────────┐     AG-UI     ┌──────────────┐
│ Your App     │ ◄───────────► │ Agent        │
│ (React/Vue)  │   UI Components│ Service      │
└──────────────┘               └──────────────┘
       ↓
  ┌─────────────────────────────────┐
  │  Card: Weather in London        │
  │  ┌─────┐  ┌─────┐  ┌─────┐     │
  │  │ 15°C│  │ 65% │  │ 🌤️  │     │
  │  └─────┘  └─────┘  └─────┘     │
  │  [Get 7-Day Forecast] [Share]  │
  └─────────────────────────────────┘
```

**Endpoints**:
- `POST /agui/invoke` - Invoke with UI components
- `POST /agui/stream` - Stream with UI components
- `POST /agui/action` - Handle UI actions (button clicks, form submits)

### Enabling Protocols

```bash
# .env
ENABLE_MCP=true
ENABLE_A2A=true
ENABLE_AGUI=true
```

---

## Quick Start (5 Minutes)

### 1. Clone and Setup

```bash
git clone https://github.com/saiadityavarma/agent-microservice-boilerplate.git
cd agent-microservice-boilerplate

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env
```

### 2. Start Services

```bash
# Start PostgreSQL and Redis (requires Docker)
docker-compose -f docker/docker-compose.yml up -d postgres redis

# Run database migrations
alembic upgrade head

# Start the server
uvicorn agent_service.api.app:app --reload
```

### 3. Create Your First Agent (The Fun Part!)

Create `src/agent_service/agent/examples/my_agent.py`:

```python
from agent_service.agent.decorators import agent
from agent_service.agent.context import AgentContext
from agent_service.interfaces.agent import AgentInput, AgentOutput

@agent(name="greeting_agent", description="A friendly greeting agent")
async def greeting_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    """Your agent logic goes here - this is ALL you need to write!"""

    # Access the user's message
    user_message = input.message

    # Use a tool if needed
    # result = await ctx.call_tool("my_tool", {"param": "value"})

    # Return a response
    return AgentOutput(
        content=f"Hello! You said: {user_message}",
        metadata={"processed_by": "greeting_agent"}
    )
```

### 4. Test It

```bash
curl -X POST http://localhost:8000/api/v1/agents/greeting_agent/invoke \
  -H "Content-Type: application/json" \
  -d '{"message": "Hi there!"}'
```

That's it! Your agent is now a production-ready API endpoint with authentication, logging, metrics, and more.

---

## Project Structure

```
agent-microservice-boilerplate/
├── src/agent_service/
│   ├── agent/                  # YOUR AGENTS GO HERE
│   │   ├── decorators.py       # @agent decorator
│   │   ├── context.py          # AgentContext (db, cache, tools, secrets)
│   │   ├── registry.py         # Auto-discovers agents
│   │   ├── integrations/       # LangGraph, CrewAI adapters
│   │   └── examples/           # ADD YOUR AGENTS HERE
│   │
│   ├── tools/                  # YOUR TOOLS GO HERE
│   │   ├── decorators.py       # @tool decorator
│   │   ├── registry.py         # Auto-discovers tools
│   │   └── examples/           # ADD YOUR TOOLS HERE
│   │
│   ├── protocols/              # MCP, A2A, AG-UI implementations
│   │   ├── mcp/                # Model Context Protocol
│   │   ├── a2a/                # Agent-to-Agent
│   │   └── agui/               # Agent-UI
│   │
│   ├── auth/                   # Authentication system
│   │   ├── providers/          # Azure AD, AWS Cognito, API Keys
│   │   ├── rbac/               # Role-based access control
│   │   └── middleware.py       # Auth middleware
│   │
│   ├── api/                    # REST API
│   │   ├── v1/                 # Versioned endpoints
│   │   ├── middleware/         # Request ID, rate limiting, etc.
│   │   └── routes/             # Route handlers
│   │
│   ├── infrastructure/         # Infrastructure services
│   │   ├── database/           # SQLAlchemy, repositories
│   │   ├── cache/              # Redis cache
│   │   └── observability/      # Logging, metrics, tracing
│   │
│   └── interfaces/             # Core abstractions
│       ├── agent.py            # IAgent interface
│       ├── tool.py             # ITool interface
│       └── protocol.py         # IProtocolHandler interface
│
├── docker/                     # Docker configuration
├── helm/                       # Kubernetes Helm charts
├── k8s/                        # Raw Kubernetes manifests
├── monitoring/                 # Prometheus, Grafana configs
├── docs/                       # Documentation
├── tests/                      # Test suite
└── examples/                   # Example implementations
```

---

## What Data Scientists Need to Edit

### 1. Your Agents (`src/agent_service/agent/examples/`)

```python
from agent_service.agent.decorators import agent
from agent_service.agent.context import AgentContext
from agent_service.interfaces.agent import AgentInput, AgentOutput
import openai

@agent(name="qa_agent", description="Answers questions using GPT-4")
async def qa_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    # Get API key securely from context
    api_key = await ctx.get_secret("OPENAI_API_KEY")

    # Your LLM logic
    client = openai.AsyncOpenAI(api_key=api_key)
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": input.message}]
    )

    return AgentOutput(content=response.choices[0].message.content)
```

### 2. Your Tools (`src/agent_service/tools/examples/`)

```python
from agent_service.tools.decorators import tool

@tool(name="search_database", description="Search the product database")
async def search_database(query: str, limit: int = 10) -> dict:
    """Search for products matching the query."""
    results = await db.search(query, limit=limit)
    return {"results": results, "count": len(results)}
```

### 3. Environment Variables (`.env`)

```bash
# Required: Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/agents

# Required: Choose your auth provider
AUTH_PROVIDER=azure_ad  # or: aws_cognito, api_key

# For Azure AD:
AZURE_AD_TENANT_ID=your-tenant-id
AZURE_AD_CLIENT_ID=your-client-id

# For AWS Cognito:
AWS_COGNITO_REGION=us-east-1
AWS_COGNITO_USER_POOL_ID=your-pool-id
AWS_COGNITO_APP_CLIENT_ID=your-client-id

# Enable protocols
ENABLE_MCP=true
ENABLE_A2A=true
ENABLE_AGUI=true

# Your LLM API keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### 4. That's It!

Everything else is pre-configured.

---

## Common Agent Patterns

### Simple LLM Agent
```python
@agent(name="chat", description="General chat agent")
async def chat_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    api_key = await ctx.get_secret("OPENAI_API_KEY")
    client = openai.AsyncOpenAI(api_key=api_key)
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": input.message}]
    )
    return AgentOutput(content=response.choices[0].message.content)
```

### Tool-Using Agent
```python
@agent(name="assistant", description="Agent with tools")
async def assistant_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    if "weather" in input.message.lower():
        weather = await ctx.call_tool("get_weather", {"city": "NYC"})
        return AgentOutput(content=f"Weather: {weather}")
    return AgentOutput(content="I can help with weather!")
```

### RAG Agent
```python
@agent(name="rag", description="Answers from your documents")
async def rag_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    docs = await ctx.call_tool("vector_search", {"query": input.message, "top_k": 5})
    context = "\n".join([doc["content"] for doc in docs["results"]])
    # Generate answer with context...
```

---

## Framework Integrations

### LangGraph
```python
from agent_service.agent.integrations.langgraph_adapter import langgraph_agent

@langgraph_agent(name="my_langgraph_agent", graph=your_graph)
async def lg_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    pass
```

### CrewAI
```python
from agent_service.agent.integrations.crewai_adapter import crewai_agent

@crewai_agent(name="my_crew", crew=my_crew)
async def crew_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    pass
```

---

## Authentication Options

| Provider | Best For | Config |
|----------|----------|--------|
| **API Keys** | Internal tools, B2B | `AUTH_PROVIDER=api_key` |
| **Azure AD** | Microsoft/Enterprise | `AUTH_PROVIDER=azure_ad` |
| **AWS Cognito** | AWS ecosystem | `AUTH_PROVIDER=aws_cognito` |

---

## Production Deployment

### Docker
```bash
docker build -f docker/Dockerfile -t agent-service:latest .
docker-compose -f docker/docker-compose.yml up -d
```

### Kubernetes
```bash
helm install agent-service ./helm/agent-service \
  --values ./helm/agent-service/values-prod.yaml
```

### Monitoring
- **Metrics**: `/metrics` (Prometheus)
- **Health**: `/health/live`, `/health/ready`
- **Tracing**: OpenTelemetry (Jaeger/Zipkin)

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/agents` | GET | List available agents |
| `/api/v1/agents/{name}/invoke` | POST | Invoke agent |
| `/api/v1/agents/{name}/stream` | POST | Stream response |
| `/mcp/invoke` | POST | MCP protocol invoke |
| `/a2a/discover` | GET | A2A agent discovery |
| `/agui/invoke` | POST | AG-UI with components |
| `/health/live` | GET | Liveness probe |
| `/metrics` | GET | Prometheus metrics |

---

## Documentation

- [Quick Start](docs/quickstart.md)
- [Creating Your First Agent](docs/first-agent.md)
- [API Reference](docs/api/)
- [Deployment Guide](docs/deployment.md)
- [Protocol Reference](docs/api/protocols.md)

---

## License

MIT License - Use freely for commercial and personal projects.
