# Agent Service Boilerplate

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

## Quick Start (5 Minutes)

### 1. Clone and Setup

```bash
git clone https://github.com/saiadityavarma/agents_boiler_plate.git
cd agents_boiler_plate

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

## Project Structure (What Goes Where)

```
agents_boiler_plate/
├── src/agent_service/
│   ├── agent/                  # YOUR AGENTS GO HERE
│   │   ├── decorators.py       # @agent decorator (don't edit)
│   │   ├── context.py          # AgentContext (don't edit)
│   │   └── examples/           # ADD YOUR AGENTS HERE
│   │       ├── my_agent.py     # Your custom agents
│   │       └── ...
│   │
│   ├── tools/                  # YOUR TOOLS GO HERE
│   │   ├── decorators.py       # @tool decorator (don't edit)
│   │   └── examples/           # ADD YOUR TOOLS HERE
│   │       ├── my_tool.py      # Your custom tools
│   │       └── ...
│   │
│   ├── auth/                   # Authentication (pre-configured)
│   ├── api/                    # REST API (pre-configured)
│   ├── config/                 # Configuration (edit .env)
│   └── infrastructure/         # Database, cache, etc. (pre-configured)
│
├── .env                        # YOUR SECRETS AND CONFIG
├── docker/                     # Docker setup (ready to use)
├── helm/                       # Kubernetes deployment (ready to use)
└── tests/                      # Test examples
```

---

## What Data Scientists Need to Edit

### 1. Your Agents (`src/agent_service/agent/examples/`)

This is where your AI logic lives. Here's a real-world example:

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

Tools are actions your agent can take:

```python
from agent_service.tools.decorators import tool

@tool(name="search_database", description="Search the product database")
async def search_database(query: str, limit: int = 10) -> dict:
    """Search for products matching the query."""
    # Your database logic here
    results = await db.search(query, limit=limit)
    return {"results": results, "count": len(results)}
```

Then use it in your agent:

```python
@agent(name="shopping_agent", description="Helps users find products")
async def shopping_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    # Call your tool
    results = await ctx.call_tool("search_database", {
        "query": input.message,
        "limit": 5
    })

    return AgentOutput(content=f"Found {results['count']} products...")
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

# For API Keys (simplest option):
# Just set AUTH_PROVIDER=api_key and create keys via /api/v1/auth/keys

# Your API keys for LLM providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Optional: Redis for caching (recommended for production)
REDIS_URL=redis://localhost:6379/0
```

### 4. That's It!

Everything else is pre-configured:
- Authentication middleware
- Rate limiting
- Request validation
- Error handling
- Logging and metrics
- Database connections
- Docker and Kubernetes configs

---

## Common Agent Patterns

### Pattern 1: Simple LLM Agent

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

### Pattern 2: Tool-Using Agent

```python
@agent(name="assistant", description="Agent with tools")
async def assistant_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    # Decide which tool to use based on input
    if "weather" in input.message.lower():
        weather = await ctx.call_tool("get_weather", {"city": "NYC"})
        return AgentOutput(content=f"Weather: {weather}")

    if "search" in input.message.lower():
        results = await ctx.call_tool("web_search", {"query": input.message})
        return AgentOutput(content=f"Found: {results}")

    return AgentOutput(content="I can help with weather and search!")
```

### Pattern 3: RAG Agent (Retrieval-Augmented Generation)

```python
@agent(name="rag", description="Answers from your documents")
async def rag_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    # 1. Search your vector database
    docs = await ctx.call_tool("vector_search", {
        "query": input.message,
        "top_k": 5
    })

    # 2. Build context from retrieved docs
    context = "\n".join([doc["content"] for doc in docs["results"]])

    # 3. Generate answer with context
    api_key = await ctx.get_secret("OPENAI_API_KEY")
    client = openai.AsyncOpenAI(api_key=api_key)

    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": f"Answer based on: {context}"},
            {"role": "user", "content": input.message}
        ]
    )

    return AgentOutput(content=response.choices[0].message.content)
```

### Pattern 4: Multi-Step Agent

```python
@agent(name="researcher", description="Multi-step research agent")
async def researcher_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    ctx.logger.info(f"Starting research on: {input.message}")

    # Step 1: Break down the question
    subtopics = await analyze_question(input.message)

    # Step 2: Research each subtopic
    findings = []
    for topic in subtopics:
        result = await ctx.call_tool("web_search", {"query": topic})
        findings.append(result)

    # Step 3: Synthesize findings
    summary = await synthesize_findings(findings)

    return AgentOutput(
        content=summary,
        metadata={"subtopics_researched": len(subtopics)}
    )
```

---

## Using LangGraph, CrewAI, or Other Frameworks

Already have agents built with a framework? Wrap them!

### LangGraph Integration

```python
from agent_service.agent.integrations.langgraph_adapter import langgraph_agent
from your_langgraph_app import your_graph

@langgraph_agent(name="my_langgraph_agent", graph=your_graph)
async def langgraph_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    # The adapter handles running your graph
    pass
```

### CrewAI Integration

```python
from agent_service.agent.integrations.crewai_adapter import crewai_agent
from crewai import Crew, Agent, Task

my_crew = Crew(agents=[...], tasks=[...])

@crewai_agent(name="my_crew", crew=my_crew)
async def crew_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
    pass
```

---

## Production Deployment Checklist

### Before You Deploy

- [ ] Set `DEBUG=false` in `.env`
- [ ] Configure your auth provider (Azure AD, AWS Cognito, or API keys)
- [ ] Set strong `SECRET_KEY` (generate with `openssl rand -hex 32`)
- [ ] Configure production database URL
- [ ] Set up Redis for caching and rate limiting
- [ ] Review rate limits in `config/settings.py`

### Using Docker

```bash
# Build production image
docker build -f docker/Dockerfile -t agent-service:latest .

# Run with docker-compose
docker-compose -f docker/docker-compose.yml up -d
```

### Using Kubernetes

```bash
# Deploy with Helm
helm install agent-service ./helm/agent-service \
  --values ./helm/agent-service/values-prod.yaml \
  --set secrets.databaseUrl=$DATABASE_URL \
  --set secrets.openaiApiKey=$OPENAI_API_KEY
```

### Monitoring

- **Metrics**: Prometheus endpoint at `/metrics`
- **Health**: `/health/live` and `/health/ready`
- **Logs**: Structured JSON logs (configure your log aggregator)
- **Tracing**: OpenTelemetry support (configure Jaeger/Zipkin)

---

## Authentication Options

### Option 1: API Keys (Simplest)

Best for: Internal tools, B2B integrations, getting started quickly.

```bash
# In .env
AUTH_PROVIDER=api_key

# Create a key via API
curl -X POST http://localhost:8000/api/v1/auth/keys \
  -H "Content-Type: application/json" \
  -d '{"name": "My API Key", "scopes": ["read", "write"]}'

# Use the key
curl http://localhost:8000/api/v1/agents/my_agent/invoke \
  -H "X-API-Key: sk_live_abc123..."
```

### Option 2: Azure AD

Best for: Enterprise apps using Microsoft/Azure ecosystem.

```bash
# In .env
AUTH_PROVIDER=azure_ad
AZURE_AD_TENANT_ID=your-tenant-id
AZURE_AD_CLIENT_ID=your-client-id

# Client gets token from Azure AD, then:
curl http://localhost:8000/api/v1/agents/my_agent/invoke \
  -H "Authorization: Bearer <azure-ad-token>"
```

### Option 3: AWS Cognito

Best for: Apps in AWS ecosystem.

```bash
# In .env
AUTH_PROVIDER=aws_cognito
AWS_COGNITO_REGION=us-east-1
AWS_COGNITO_USER_POOL_ID=us-east-1_xxxxx
AWS_COGNITO_APP_CLIENT_ID=your-client-id

# Client gets token from Cognito, then:
curl http://localhost:8000/api/v1/agents/my_agent/invoke \
  -H "Authorization: Bearer <cognito-token>"
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/agents` | GET | List all available agents |
| `/api/v1/agents/{name}/invoke` | POST | Invoke an agent |
| `/api/v1/agents/{name}/stream` | POST | Stream agent response |
| `/api/v1/tools` | GET | List all available tools |
| `/api/v1/auth/keys` | POST | Create API key |
| `/api/v1/auth/keys` | GET | List your API keys |
| `/health/live` | GET | Liveness probe |
| `/health/ready` | GET | Readiness probe |
| `/metrics` | GET | Prometheus metrics |
| `/docs` | GET | Swagger UI |

---

## FAQ

### Q: Do I need to know FastAPI/SQLAlchemy/Docker?

**No!** Just write your agents and tools in Python. The infrastructure is pre-configured.

### Q: Can I use my existing LangChain/CrewAI agents?

**Yes!** Use the framework adapters in `agent/integrations/`. See examples above.

### Q: How do I add a new API endpoint?

Add a new file in `src/agent_service/api/routes/` and register it in `api/app.py`. But for most cases, just creating a new agent automatically creates its endpoint.

### Q: How do I connect to my own database?

Update `DATABASE_URL` in `.env`. For additional models, add them in `domain/models.py`.

### Q: How do I add custom middleware?

Add to `src/agent_service/api/middleware/`. See existing middleware for examples.

### Q: Where do logs go?

By default, structured JSON to stdout. Configure your log aggregator (CloudWatch, Datadog, etc.) to collect from stdout.

### Q: How do I run tests?

```bash
# All tests
pytest

# Just unit tests
pytest tests/unit/

# With coverage
pytest --cov=agent_service
```

---

## Support

- **Issues**: [GitHub Issues](https://github.com/saiadityavarma/agents_boiler_plate/issues)
- **Documentation**: See `/docs` folder for detailed guides

---

## License

MIT License - Use freely for commercial and personal projects.
