"""
Example integration of enhanced Prometheus metrics with FastAPI application.

This file demonstrates how to integrate the metrics collector and middleware
into your application.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware

from agent_service.config.settings import get_settings
from agent_service.api.middleware.metrics import MetricsMiddleware
from agent_service.infrastructure.observability.metrics_collectors import (
    metrics_collector_lifespan,
    start_metrics_collector,
    stop_metrics_collector,
)
from agent_service.infrastructure.cache.redis import get_redis_manager, close_redis
from agent_service.infrastructure.database.connection import db
from agent_service.auth.dependencies import get_current_user_any, optional_auth
from agent_service.auth.schemas import UserInfo


# ============================================================================
# Option 1: Using lifespan context manager (Recommended)
# ============================================================================

@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """
    Application lifespan with metrics collection.

    This is the recommended approach for FastAPI 0.109+
    """
    settings = get_settings()

    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")

    # Initialize database
    if settings.database_url:
        await db.connect(settings.database_url.get_secret_value())
        print("Database connection established")

    # Initialize Redis
    redis_manager = await get_redis_manager()
    if redis_manager.is_available:
        is_healthy = await redis_manager.health_check()
        if is_healthy:
            print("Redis connection established and healthy")
        else:
            print("Redis connection established but health check failed")
    else:
        print("Redis is not available - some features will be limited")

    # Start metrics collector (collects gauge metrics every 30 seconds)
    async with metrics_collector_lifespan(collection_interval=30):
        print("Metrics collector started")

        yield  # Application is running

        # Shutdown happens after this point
        print("Starting shutdown sequence")

    # Cleanup
    await close_redis()
    print("Redis connection closed")

    await db.disconnect()
    print("Database connection closed")

    print("Shutdown complete")


def create_app_with_lifespan() -> FastAPI:
    """
    Create FastAPI application with lifespan-based metrics collection.

    This is the recommended approach.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.debug else None,
        lifespan=app_lifespan,
    )

    # Add metrics middleware
    # This should be added early in the middleware stack
    app.add_middleware(MetricsMiddleware)

    # Add other middleware
    app.add_middleware(CORSMiddleware, allow_origins=["*"])

    # Register routes here
    # app.include_router(...)

    return app


# ============================================================================
# Option 2: Using startup/shutdown events (Legacy)
# ============================================================================

def create_app_with_events() -> FastAPI:
    """
    Create FastAPI application with event-based metrics collection.

    This approach uses @app.on_event which is being deprecated
    in favor of lifespan context managers.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.debug else None,
    )

    @app.on_event("startup")
    async def startup():
        """Application startup."""
        # Initialize database
        if settings.database_url:
            await db.connect(settings.database_url.get_secret_value())

        # Initialize Redis
        await get_redis_manager()

        # Start metrics collector
        await start_metrics_collector(collection_interval=30)
        print("Metrics collector started")

    @app.on_event("shutdown")
    async def shutdown():
        """Application shutdown."""
        # Stop metrics collector
        await stop_metrics_collector()
        print("Metrics collector stopped")

        # Cleanup other resources
        await close_redis()
        await db.disconnect()

    # Add metrics middleware
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=["*"])

    # Register routes here
    # app.include_router(...)

    return app


# ============================================================================
# Middleware Configuration with User State
# ============================================================================

class UserStateMiddleware:
    """
    Middleware to attach user information to request state.

    This allows the MetricsMiddleware to access user info for detailed metrics.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)

            # Try to get user info (optional auth)
            # This will not raise exceptions for unauthenticated requests
            try:
                user = await optional_auth(
                    token=request.headers.get("authorization"),
                    api_key=request.headers.get("x-api-key"),
                )
                if user:
                    # Store user in request state for metrics middleware
                    scope["state"]["user"] = user
            except Exception:
                # If auth fails, continue without user info
                pass

        await self.app(scope, receive, send)


def create_app_with_user_tracking() -> FastAPI:
    """
    Create FastAPI application with user tracking in metrics.

    This adds user information to request state so the MetricsMiddleware
    can track requests by user and auth type.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=app_lifespan,
    )

    # Add middlewares in order
    # UserStateMiddleware should come before MetricsMiddleware
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(UserStateMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=["*"])

    return app


# ============================================================================
# Example Route with Metrics
# ============================================================================

from fastapi import APIRouter, HTTPException
import time
from agent_service.infrastructure.observability.metrics import (
    AGENT_INVOCATIONS,
    AGENT_EXECUTION_DURATION_SECONDS,
    AGENT_TOKENS_USED_TOTAL,
    AUTH_LOGIN_TOTAL,
    DB_QUERY_DURATION_SECONDS,
    REDIS_OPERATIONS_TOTAL,
)

router = APIRouter()


@router.post("/agents/execute")
async def execute_agent(
    agent_name: str,
    task: str,
    user: UserInfo = Depends(get_current_user_any),
):
    """
    Example endpoint showing how to track agent metrics.
    """
    start = time.perf_counter()

    try:
        # Simulate agent execution
        # In real code, this would be your agent execution logic
        result = {"output": "Agent executed successfully", "tokens": {"input": 100, "output": 50}}

        # Track successful invocation
        AGENT_INVOCATIONS.labels(
            agent_name=agent_name,
            status="success"
        ).inc()

        # Track token usage
        AGENT_TOKENS_USED_TOTAL.labels(
            agent_name=agent_name,
            token_type="input"
        ).inc(result["tokens"]["input"])

        AGENT_TOKENS_USED_TOTAL.labels(
            agent_name=agent_name,
            token_type="output"
        ).inc(result["tokens"]["output"])

        return result

    except Exception as e:
        # Track failed invocation
        AGENT_INVOCATIONS.labels(
            agent_name=agent_name,
            status="error"
        ).inc()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Track execution duration
        duration = time.perf_counter() - start
        AGENT_EXECUTION_DURATION_SECONDS.labels(
            agent_name=agent_name
        ).observe(duration)


@router.post("/auth/login")
async def login(username: str, password: str):
    """
    Example login endpoint with auth metrics.
    """
    try:
        # Simulate authentication
        # In real code, this would be your auth logic
        if username == "admin" and password == "secret":
            AUTH_LOGIN_TOTAL.labels(
                provider="custom",
                success="true"
            ).inc()
            return {"token": "fake-jwt-token"}
        else:
            AUTH_LOGIN_TOTAL.labels(
                provider="custom",
                success="false"
            ).inc()
            raise HTTPException(status_code=401, detail="Invalid credentials")

    except HTTPException:
        raise
    except Exception as e:
        AUTH_LOGIN_TOTAL.labels(
            provider="custom",
            success="false"
        ).inc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{item_id}")
async def get_data(item_id: str):
    """
    Example endpoint with database and cache metrics.
    """
    # Try cache first
    start = time.perf_counter()

    # Simulate Redis get
    REDIS_OPERATIONS_TOTAL.labels(operation="get").inc()
    cache_duration = time.perf_counter() - start

    # Cache miss - query database
    start = time.perf_counter()

    try:
        # Simulate database query
        # In real code: result = await session.execute(select(Item).where(Item.id == item_id))
        result = {"id": item_id, "name": "Example Item"}

        duration = time.perf_counter() - start
        DB_QUERY_DURATION_SECONDS.labels(query_type="select").observe(duration)

        # Store in cache
        REDIS_OPERATIONS_TOTAL.labels(operation="set").inc()

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Helper Functions and Decorators
# ============================================================================

from functools import wraps
from typing import Callable
from contextlib import contextmanager


@contextmanager
def track_agent_execution(agent_name: str):
    """
    Context manager to track agent execution metrics.

    Usage:
        with track_agent_execution("code_analyzer"):
            result = await agent.execute(task)
    """
    start = time.perf_counter()
    success = False

    try:
        yield
        success = True
    except Exception:
        raise
    finally:
        duration = time.perf_counter() - start

        # Track invocation
        AGENT_INVOCATIONS.labels(
            agent_name=agent_name,
            status="success" if success else "error"
        ).inc()

        # Track duration
        AGENT_EXECUTION_DURATION_SECONDS.labels(
            agent_name=agent_name
        ).observe(duration)


def track_db_query(query_type: str):
    """
    Decorator to track database query metrics.

    Usage:
        @track_db_query("select")
        async def get_user(session, user_id):
            return await session.execute(select(User).where(User.id == user_id))
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                DB_QUERY_DURATION_SECONDS.labels(query_type=query_type).observe(duration)
        return wrapper
    return decorator


# Example usage of helpers
async def example_agent_execution():
    """Example showing how to use the track_agent_execution context manager."""
    with track_agent_execution("code_analyzer"):
        # Your agent execution code here
        await asyncio.sleep(1)  # Simulated work

        # Track token usage
        AGENT_TOKENS_USED_TOTAL.labels(
            agent_name="code_analyzer",
            token_type="input"
        ).inc(150)

        AGENT_TOKENS_USED_TOTAL.labels(
            agent_name="code_analyzer",
            token_type="output"
        ).inc(75)


@track_db_query("select")
async def example_db_query(session):
    """Example showing how to use the track_db_query decorator."""
    # Your database query here
    result = await session.execute(text("SELECT * FROM users LIMIT 10"))
    return result.fetchall()


# ============================================================================
# Export configured app
# ============================================================================

# Use this in your main.py
app = create_app_with_lifespan()

# Or if you want user tracking
# app = create_app_with_user_tracking()
