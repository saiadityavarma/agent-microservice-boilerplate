# src/agent_service/api/app.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_service.config.settings import get_settings
from agent_service.api.middleware.cors import get_cors_middleware_config
from agent_service.api.middleware.request_id import RequestIDMiddleware
from agent_service.api.middleware.logging import RequestLoggingMiddleware
from agent_service.api.middleware.security import SecurityHeadersMiddleware
from agent_service.api.middleware.errors import register_error_handlers
from agent_service.api.middleware.rate_limit import setup_rate_limiting
from agent_service.api.middleware.versioning import APIVersioningMiddleware
from agent_service.api.routes import health, auth
from agent_service.api import v1
from agent_service.infrastructure.cache.redis import get_redis_manager, close_redis
from agent_service.infrastructure.database import db
from agent_service.infrastructure.observability.tracing import (
    init_tracing,
    shutdown_tracing,
)
from agent_service.infrastructure.observability.tracing_instrumentation import (
    instrument_fastapi,
    instrument_http_client,
)
from agent_service.infrastructure.observability.error_tracking import (
    init_sentry,
    flush as flush_sentry,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    settings = get_settings()
    # Initialize resources here (DB, cache, etc.)

    # Initialize Sentry error tracking
    init_sentry(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment or settings.environment,
        release=settings.app_version,
        sample_rate=settings.sentry_sample_rate,
        traces_sample_rate=settings.sentry_traces_sample_rate,
    )

    # Initialize distributed tracing
    init_tracing(
        service_name=settings.app_name,
        environment=settings.environment,
    )

    # Instrument HTTP client for outbound requests
    instrument_http_client()

    # Initialize database connection if configured
    if settings.database_url:
        database_url = settings.database_url.get_secret_value()
        await db.connect(
            url=database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_recycle=settings.db_pool_recycle,
            pool_pre_ping=True,
            echo_sql=settings.db_echo_sql,
        )
        print(f"Database connection established (pool_size={settings.db_pool_size}, max_overflow={settings.db_max_overflow})")
    else:
        print("Database not configured - database features will be disabled")

    # Initialize Redis connection
    redis_manager = await get_redis_manager()
    if redis_manager.is_available:
        # Perform health check
        is_healthy = await redis_manager.health_check()
        if is_healthy:
            print("Redis connection established and healthy")
        else:
            print("Redis connection established but health check failed")
    else:
        print("Redis is not available - rate limiting will use in-memory storage")

    yield

    # Shutdown
    # Cleanup resources here
    await close_redis()

    # Close database connection
    if db._engine:
        await db.disconnect()
        print("Database connection closed")

    # Shutdown tracing and flush remaining spans
    shutdown_tracing()

    # Flush Sentry events before shutdown
    flush_sentry(timeout=5.0)


def create_app() -> FastAPI:
    """
    Application factory.

    Claude Code: Register new routes here.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="""
# Agent Service API

A comprehensive, production-ready API service for managing AI agents with support for multiple protocols and integrations.

## Features

- **Agent Management**: Create, configure, and invoke AI agents with streaming support
- **Multi-Protocol Support**: MCP, A2A, AGUI protocols for seamless integration
- **Authentication & Authorization**:
  - JWT Bearer tokens (Azure AD, AWS Cognito)
  - API Key authentication with scoped access
  - Role-based access control (RBAC)
- **Background Jobs**: Asynchronous task execution with Celery
- **Observability**:
  - Distributed tracing (OpenTelemetry)
  - Error tracking (Sentry)
  - Structured logging
  - Audit logging
- **Rate Limiting**: Configurable rate limits per endpoint and tier
- **Caching**: Redis-backed caching for optimal performance

## Getting Started

### Authentication

This API supports two authentication methods:

1. **Bearer Token (JWT)**:
   ```
   Authorization: Bearer <your-jwt-token>
   ```

2. **API Key**:
   ```
   X-API-Key: sk_live_your_api_key
   ```

### Quick Example

```python
import httpx

# Using API Key
headers = {"X-API-Key": "sk_live_your_api_key"}
response = httpx.post(
    "http://localhost:8000/api/v1/agents/invoke",
    json={"message": "Hello, agent!"},
    headers=headers
)
print(response.json())
```

## Rate Limits

Default rate limits by tier:
- **Free**: 100 requests/hour
- **Pro**: 1,000 requests/hour
- **Enterprise**: Unlimited

## Support

For issues or questions, please contact your system administrator.
        """,
        docs_url="/docs" if settings.debug else None,
        lifespan=lifespan,
        # OpenAPI metadata
        contact={
            "name": "API Support Team",
            "url": "https://example.com/support",
            "email": "support@example.com",
        },
        license_info={
            "name": "Apache 2.0",
            "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
        },
        openapi_tags=[
            {
                "name": "Health",
                "description": "Health check and readiness endpoints for monitoring service status and dependencies.",
            },
            {
                "name": "Authentication",
                "description": "Authentication endpoints for user info, permissions, and token validation. Supports JWT and API key authentication.",
            },
            {
                "name": "Agents",
                "description": "Agent invocation endpoints for synchronous, asynchronous, and streaming interactions with AI agents.",
            },
            {
                "name": "API Keys",
                "description": "API key management for creating, listing, rotating, and revoking API keys. Keys provide scoped access and rate limiting.",
            },
            {
                "name": "Protocols",
                "description": "Protocol handlers for MCP (Model Context Protocol), A2A (Agent-to-Agent), and AGUI (Agent UI) integrations.",
            },
            {
                "name": "Audit Logs",
                "description": "Administrative endpoints for querying audit logs and tracking user actions. Requires admin privileges.",
            },
            {
                "name": "Background Jobs",
                "description": "Asynchronous task management for long-running operations like agent invocations and maintenance tasks.",
            },
        ],
    )

    # Middleware (order matters - added in reverse order of execution)
    # Request ID should be first so it's available to all other middleware
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(APIVersioningMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # CORS middleware with environment-aware configuration
    cors_config = get_cors_middleware_config(settings)
    app.add_middleware(CORSMiddleware, **cors_config)

    # Error handlers
    register_error_handlers(app)

    # Rate limiting
    setup_rate_limiting(app)

    # Instrument FastAPI with tracing
    instrument_fastapi(app)

    # ============================================================================
    # Routes
    # ============================================================================

    # Health routes (no versioning - kept at root level)
    app.include_router(health.router, tags=["Health"])

    # Authentication routes (no versioning - kept at root level)
    # These include: /auth/me, /auth/permissions, /auth/validate
    app.include_router(auth.router, tags=["Authentication"])

    # API v1 routes
    # All versioned routes are under /api/v1
    # Includes: agents, auth/api-keys, protocols, admin/audit
    app.include_router(v1.router, prefix="/api/v1")

    # ──────────────────────────────────────────────
    # Claude Code: Add new versioned routers to api/v1/router.py
    # Add new root-level (unversioned) routers here if needed
    # ──────────────────────────────────────────────

    return app


app = create_app()
