# Task 04: FastAPI Foundation

## Objective
Establish FastAPI application factory, middleware patterns, error handling, and dependency injection that Claude Code follows.

## Deliverables

### Application Factory
```python
# src/agent_service/api/app.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_service.config.settings import get_settings
from agent_service.api.middleware.logging import RequestLoggingMiddleware
from agent_service.api.middleware.errors import register_error_handlers
from agent_service.api.routes import health, agents


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    settings = get_settings()
    # Initialize resources here (DB, cache, etc.)
    yield
    # Shutdown
    # Cleanup resources here


def create_app() -> FastAPI:
    """
    Application factory.
    
    Claude Code: Register new routes here.
    """
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.debug else None,
        lifespan=lifespan,
    )
    
    # Middleware
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure in production
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Error handlers
    register_error_handlers(app)
    
    # Routes
    app.include_router(health.router, tags=["Health"])
    app.include_router(agents.router, prefix="/api/v1", tags=["Agents"])
    
    # ──────────────────────────────────────────────
    # Claude Code: Add new routers here
    # Example: app.include_router(my_router, prefix="/api/v1/my-feature")
    # ──────────────────────────────────────────────
    
    return app


app = create_app()
```

### Error Handling Pattern
```python
# src/agent_service/api/middleware/errors.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base error class. Claude Code: Extend this for custom errors."""
    def __init__(self, message: str, code: str, status: int = 500):
        self.message = message
        self.code = code
        self.status = status


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, "NOT_FOUND", 404)


class ValidationError(AppError):
    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR", 400)


def register_error_handlers(app: FastAPI):
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status,
            content={"error": exc.code, "message": exc.message},
        )
    
    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"error": "INTERNAL_ERROR", "message": "An error occurred"},
        )
```

### Dependency Injection Pattern
```python
# src/agent_service/api/dependencies.py
from typing import Annotated
from fastapi import Depends

from agent_service.config.settings import Settings, get_settings
from agent_service.interfaces import IAgent
from agent_service.agent.registry import get_default_agent


# Type aliases for clean injection
AppSettings = Annotated[Settings, Depends(get_settings)]
CurrentAgent = Annotated[IAgent, Depends(get_default_agent)]


# Claude Code: Add new dependencies here following this pattern
# Example:
# async def get_my_service() -> MyService:
#     return MyService()
# MyServiceDep = Annotated[MyService, Depends(get_my_service)]
```

### Route Pattern
```python
# src/agent_service/api/routes/agents.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from agent_service.api.dependencies import CurrentAgent, AppSettings
from agent_service.interfaces import AgentInput

router = APIRouter()


@router.post("/agents/invoke")
async def invoke_agent(
    message: str,
    agent: CurrentAgent,
    settings: AppSettings,
):
    """Invoke agent synchronously."""
    result = await agent.invoke(AgentInput(message=message))
    return {"response": result.content}


@router.post("/agents/stream")
async def stream_agent(
    message: str,
    agent: CurrentAgent,
):
    """Invoke agent with streaming response."""
    async def generate():
        async for chunk in agent.stream(AgentInput(message=message)):
            yield f"data: {chunk.content}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

## Pattern for Claude Code

When adding new routes:
```python
# 1. Create route file in api/routes/
# src/agent_service/api/routes/my_feature.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/my-feature")
async def my_endpoint():
    return {"status": "ok"}

# 2. Register in app.py
app.include_router(my_feature.router, prefix="/api/v1/my-feature")
```

## Acceptance Criteria
- [ ] App factory creates working FastAPI app
- [ ] Error handlers return consistent JSON
- [ ] Middleware stack configured
- [ ] Health endpoint responds
- [ ] Streaming endpoint works
