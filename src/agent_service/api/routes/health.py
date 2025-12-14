"""Health check endpoints for Kubernetes probes and detailed diagnostics."""
import asyncio
import logging
import time
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

import psutil
from fastapi import APIRouter, Response, status
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel, Field
from sqlalchemy import text

from agent_service.api.dependencies import AppSettings
from agent_service.infrastructure.cache.redis import get_redis_manager
from agent_service.infrastructure.database.connection import db

logger = logging.getLogger(__name__)

# Application startup time for uptime calculation
_startup_time = time.time()
_app_initialized = False

router = APIRouter()


# ===== Schemas =====


class HealthStatus(str, Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    """Health status of a single component."""
    name: str = Field(..., description="Component name")
    status: HealthStatus = Field(..., description="Component health status")
    latency_ms: Optional[float] = Field(None, description="Response latency in milliseconds")
    details: Optional[Dict] = Field(None, description="Additional component details")
    error: Optional[str] = Field(None, description="Error message if unhealthy")


class HealthResponse(BaseModel):
    """Detailed health check response."""
    status: HealthStatus = Field(..., description="Overall system health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    uptime_seconds: float = Field(..., description="Application uptime in seconds")
    version: str = Field(..., description="Application version")
    components: List[ComponentHealth] = Field(default_factory=list, description="Component health details")


class LivenessResponse(BaseModel):
    """Liveness probe response."""
    status: str = Field("alive", description="Liveness status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReadinessResponse(BaseModel):
    """Readiness probe response."""
    status: str = Field(..., description="Readiness status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    components: List[ComponentHealth] = Field(default_factory=list)


class StartupResponse(BaseModel):
    """Startup probe response."""
    status: str = Field(..., description="Startup status")
    initialized: bool = Field(..., description="Whether app is fully initialized")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ===== Health Check Helpers =====


async def check_database_health(timeout: float = 5.0) -> ComponentHealth:
    """
    Check database connectivity and performance.

    Args:
        timeout: Maximum time to wait for check in seconds

    Returns:
        ComponentHealth with database status
    """
    start_time = time.time()

    if not db._engine:
        return ComponentHealth(
            name="database",
            status=HealthStatus.UNHEALTHY,
            error="Database not configured"
        )

    try:
        async with asyncio.timeout(timeout):
            async with db.session() as session:
                # Simple connectivity check
                result = await session.execute(text("SELECT 1"))
                result.scalar()

                latency_ms = (time.time() - start_time) * 1000

                # Get pool stats using the DatabaseManager method
                try:
                    pool_stats = db.get_pool_stats()
                except Exception:
                    pool_stats = None

                return ComponentHealth(
                    name="database",
                    status=HealthStatus.HEALTHY,
                    latency_ms=round(latency_ms, 2),
                    details=pool_stats if pool_stats else None
                )

    except asyncio.TimeoutError:
        return ComponentHealth(
            name="database",
            status=HealthStatus.UNHEALTHY,
            latency_ms=(time.time() - start_time) * 1000,
            error=f"Database check timed out after {timeout}s"
        )
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        return ComponentHealth(
            name="database",
            status=HealthStatus.UNHEALTHY,
            latency_ms=(time.time() - start_time) * 1000,
            error=f"Database error: {str(e)}"
        )


async def check_redis_health(timeout: float = 5.0) -> ComponentHealth:
    """
    Check Redis connectivity and performance.

    Args:
        timeout: Maximum time to wait for check in seconds

    Returns:
        ComponentHealth with Redis status
    """
    start_time = time.time()

    try:
        async with asyncio.timeout(timeout):
            redis_manager = await get_redis_manager()

            if not redis_manager.is_available:
                return ComponentHealth(
                    name="redis",
                    status=HealthStatus.DEGRADED,
                    error="Redis not configured or unavailable"
                )

            # Perform ping check
            is_healthy = await redis_manager.health_check()
            latency_ms = (time.time() - start_time) * 1000

            if is_healthy:
                # Get additional info from Redis
                client = redis_manager.get_client()
                details = {}
                if client:
                    try:
                        info = await client.info("server")
                        details = {
                            "redis_version": info.get("redis_version"),
                            "uptime_days": info.get("uptime_in_days"),
                        }
                    except Exception:
                        pass

                return ComponentHealth(
                    name="redis",
                    status=HealthStatus.HEALTHY,
                    latency_ms=round(latency_ms, 2),
                    details=details if details else None
                )
            else:
                return ComponentHealth(
                    name="redis",
                    status=HealthStatus.UNHEALTHY,
                    latency_ms=round(latency_ms, 2),
                    error="Redis ping failed"
                )

    except asyncio.TimeoutError:
        return ComponentHealth(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            latency_ms=(time.time() - start_time) * 1000,
            error=f"Redis check timed out after {timeout}s"
        )
    except Exception as e:
        logger.error(f"Redis health check failed: {e}", exc_info=True)
        return ComponentHealth(
            name="redis",
            status=HealthStatus.DEGRADED,
            latency_ms=(time.time() - start_time) * 1000,
            error=f"Redis error: {str(e)}"
        )


async def check_system_resources() -> ComponentHealth:
    """
    Check system resource usage.

    Returns:
        ComponentHealth with system resource status
    """
    try:
        # Get memory info
        memory = psutil.virtual_memory()
        process = psutil.Process()
        process_memory = process.memory_info()

        details = {
            "memory_percent": round(memory.percent, 2),
            "memory_available_mb": round(memory.available / (1024 * 1024), 2),
            "process_memory_mb": round(process_memory.rss / (1024 * 1024), 2),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
        }

        # Determine status based on memory usage
        if memory.percent > 90:
            status = HealthStatus.UNHEALTHY
            error = "High memory usage"
        elif memory.percent > 80:
            status = HealthStatus.DEGRADED
            error = "Elevated memory usage"
        else:
            status = HealthStatus.HEALTHY
            error = None

        return ComponentHealth(
            name="system_resources",
            status=status,
            details=details,
            error=error
        )

    except Exception as e:
        logger.error(f"System resource check failed: {e}", exc_info=True)
        return ComponentHealth(
            name="system_resources",
            status=HealthStatus.DEGRADED,
            error=f"Failed to get system resources: {str(e)}"
        )


async def check_database_migrations() -> ComponentHealth:
    """
    Verify database migrations are applied (for startup probe).

    Returns:
        ComponentHealth with migration status
    """
    if not db._engine:
        return ComponentHealth(
            name="database_migrations",
            status=HealthStatus.DEGRADED,
            error="Database not configured"
        )

    try:
        async with db.session() as session:
            # Check if alembic_version table exists
            result = await session.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_name = 'alembic_version'"
            ))
            table_exists = result.scalar() > 0

            if table_exists:
                # Get current migration version
                result = await session.execute(text("SELECT version_num FROM alembic_version"))
                version = result.scalar()

                return ComponentHealth(
                    name="database_migrations",
                    status=HealthStatus.HEALTHY,
                    details={"current_version": version}
                )
            else:
                return ComponentHealth(
                    name="database_migrations",
                    status=HealthStatus.DEGRADED,
                    error="Alembic version table not found - migrations may not be initialized"
                )

    except Exception as e:
        logger.error(f"Database migration check failed: {e}", exc_info=True)
        return ComponentHealth(
            name="database_migrations",
            status=HealthStatus.DEGRADED,
            error=f"Migration check error: {str(e)}"
        )


def determine_overall_status(components: List[ComponentHealth]) -> HealthStatus:
    """
    Determine overall health status from component statuses.

    Args:
        components: List of component health checks

    Returns:
        Overall health status
    """
    if not components:
        return HealthStatus.HEALTHY

    statuses = [c.status for c in components]

    if HealthStatus.UNHEALTHY in statuses:
        return HealthStatus.UNHEALTHY
    elif HealthStatus.DEGRADED in statuses:
        return HealthStatus.DEGRADED
    else:
        return HealthStatus.HEALTHY


# ===== Health Endpoints =====


@router.get("/health/live", response_model=LivenessResponse)
async def liveness_probe():
    """
    Kubernetes liveness probe.

    Simple check that the application process is running.
    Always returns 200 if the process is alive.
    This endpoint is fast and has no dependencies.

    Use this for:
    - Kubernetes liveness probe
    - Detecting if the app needs to be restarted
    """
    return LivenessResponse(status="alive")


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness_probe(response: Response):
    """
    Kubernetes readiness probe.

    Checks that the application is ready to serve traffic.
    Verifies critical dependencies (database, Redis) are available.
    Returns 200 if ready, 503 if not ready.

    Use this for:
    - Kubernetes readiness probe
    - Load balancer health checks
    - Determining if app should receive traffic
    """
    components = []

    # Check database connectivity
    if db._engine:
        db_health = await check_database_health(timeout=3.0)
        components.append(db_health)

    # Check Redis connectivity
    redis_health = await check_redis_health(timeout=3.0)
    # Only fail if Redis is unhealthy (degraded is acceptable for readiness)
    if redis_health.status != HealthStatus.DEGRADED:
        components.append(redis_health)

    # Determine overall readiness
    critical_components = [c for c in components if c.status == HealthStatus.UNHEALTHY]

    if critical_components:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(
            status="not_ready",
            components=components
        )
    else:
        return ReadinessResponse(
            status="ready",
            components=components
        )


@router.get("/health/startup", response_model=StartupResponse)
async def startup_probe(response: Response):
    """
    Kubernetes startup probe.

    Checks that the application is fully initialized and ready to start.
    Verifies database migrations are applied.
    Returns 200 when startup is complete, 503 otherwise.

    Use this for:
    - Kubernetes startup probe
    - Ensuring app is fully initialized before accepting traffic
    - Protecting slow-starting applications
    """
    global _app_initialized

    checks_passed = True

    # Check if database is configured and migrations are applied
    migration_health = None
    if db._engine:
        migration_health = await check_database_migrations()
        if migration_health.status == HealthStatus.UNHEALTHY:
            checks_passed = False

    # Mark as initialized if all checks pass
    if checks_passed and not _app_initialized:
        _app_initialized = True
        logger.info("Application startup complete - ready to accept traffic")

    if not _app_initialized:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return StartupResponse(
            status="starting",
            initialized=False
        )
    else:
        return StartupResponse(
            status="started",
            initialized=True
        )


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: AppSettings):
    """
    Detailed health check endpoint.

    Provides comprehensive health information including:
    - Database connectivity, pool stats, and latency
    - Redis connectivity and latency
    - System resource usage (memory, CPU)
    - Application uptime and version
    - Individual component statuses

    Use this for:
    - Detailed diagnostics
    - Monitoring dashboards
    - Troubleshooting issues
    """
    components = []

    # Calculate uptime
    uptime_seconds = time.time() - _startup_time

    # Check database
    if db._engine:
        db_health = await check_database_health()
        components.append(db_health)

    # Check Redis
    redis_health = await check_redis_health()
    components.append(redis_health)

    # Check system resources
    system_health = await check_system_resources()
    components.append(system_health)

    # Determine overall status
    overall_status = determine_overall_status(components)

    return HealthResponse(
        status=overall_status,
        uptime_seconds=round(uptime_seconds, 2),
        version=settings.app_version,
        components=components
    )


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus metrics endpoint."""
    return PlainTextResponse(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
