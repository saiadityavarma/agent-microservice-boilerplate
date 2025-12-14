"""
Metrics collectors for periodic gauge updates.

This module provides background tasks that periodically collect and update
gauge metrics for database pools, active sessions, and other system resources.
"""

import asyncio
import logging
from typing import Optional
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.pool import Pool

from agent_service.infrastructure.observability.metrics import (
    DB_POOL_SIZE,
    DB_POOL_CHECKED_OUT,
    REDIS_CONNECTIONS_ACTIVE,
    USERS_TOTAL,
    API_KEYS_ACTIVE,
    SESSIONS_ACTIVE,
)
from agent_service.infrastructure.database.connection import db
from agent_service.infrastructure.cache.redis import get_redis

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Background task manager for collecting gauge metrics.

    This collector runs periodic tasks to update gauge metrics that require
    active polling of system resources.
    """

    def __init__(self, collection_interval: int = 30):
        """
        Initialize the metrics collector.

        Args:
            collection_interval: Interval in seconds between metric collections (default: 30)
        """
        self.collection_interval = collection_interval
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the background metrics collection task."""
        if self._running:
            logger.warning("Metrics collector is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._collection_loop())
        logger.info(f"Metrics collector started (interval: {self.collection_interval}s)")

    async def stop(self) -> None:
        """Stop the background metrics collection task."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("Metrics collector stopped")

    async def _collection_loop(self) -> None:
        """Main collection loop that runs periodically."""
        while self._running:
            try:
                await self.collect_all_metrics()
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}", exc_info=True)

            # Wait for the next collection interval
            try:
                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break

    async def collect_all_metrics(self) -> None:
        """Collect all gauge metrics."""
        await asyncio.gather(
            self.collect_database_pool_metrics(),
            self.collect_redis_metrics(),
            self.collect_business_metrics(),
            return_exceptions=True,
        )

    async def collect_database_pool_metrics(self) -> None:
        """
        Collect database connection pool metrics.

        Updates:
        - db_pool_size: Total pool size
        - db_pool_checked_out: Number of connections currently in use
        """
        try:
            if not db._engine:
                logger.debug("Database engine not initialized, skipping pool metrics")
                return

            pool: Pool = db._engine.pool

            # Get pool statistics
            pool_size = pool.size()
            checked_out = pool.checkedout()

            # Update metrics
            DB_POOL_SIZE.set(pool_size)
            DB_POOL_CHECKED_OUT.set(checked_out)

            logger.debug(
                f"Database pool metrics: size={pool_size}, checked_out={checked_out}"
            )

        except Exception as e:
            logger.error(f"Failed to collect database pool metrics: {e}")

    async def collect_redis_metrics(self) -> None:
        """
        Collect Redis connection metrics.

        Updates:
        - redis_connections_active: Number of active Redis connections
        """
        try:
            redis = await get_redis()
            if not redis:
                logger.debug("Redis not available, skipping Redis metrics")
                REDIS_CONNECTIONS_ACTIVE.set(0)
                return

            # Get Redis connection pool info
            pool = redis.connection_pool
            if hasattr(pool, '_available_connections'):
                # Calculate active connections
                # Total connections - available = active
                max_connections = pool.max_connections
                available = len(pool._available_connections)
                active_connections = max_connections - available

                REDIS_CONNECTIONS_ACTIVE.set(active_connections)

                logger.debug(f"Redis metrics: active_connections={active_connections}")
            else:
                logger.debug("Redis pool info not available")

        except Exception as e:
            logger.error(f"Failed to collect Redis metrics: {e}")

    async def collect_business_metrics(self) -> None:
        """
        Collect business metrics from the database.

        Updates:
        - users_total: Total number of users
        - api_keys_active: Number of active API keys
        - sessions_active: Number of active sessions
        """
        try:
            if not db._engine:
                logger.debug("Database engine not initialized, skipping business metrics")
                return

            async with db.session() as session:
                # Count total users
                # Note: Adjust table name based on your actual schema
                try:
                    result = await session.execute(
                        text("SELECT COUNT(*) FROM users")
                    )
                    users_count = result.scalar() or 0
                    USERS_TOTAL.set(users_count)
                except Exception as e:
                    logger.debug(f"Could not query users table: {e}")
                    USERS_TOTAL.set(0)

                # Count active API keys
                # Note: Adjust table name and conditions based on your actual schema
                try:
                    result = await session.execute(
                        text(
                            "SELECT COUNT(*) FROM api_keys "
                            "WHERE is_active = true AND (expires_at IS NULL OR expires_at > NOW())"
                        )
                    )
                    api_keys_count = result.scalar() or 0
                    API_KEYS_ACTIVE.set(api_keys_count)
                except Exception as e:
                    logger.debug(f"Could not query api_keys table: {e}")
                    API_KEYS_ACTIVE.set(0)

                # Count active sessions
                # Note: Adjust based on your session management approach
                try:
                    result = await session.execute(
                        text(
                            "SELECT COUNT(*) FROM sessions "
                            "WHERE expires_at > NOW()"
                        )
                    )
                    sessions_count = result.scalar() or 0
                    SESSIONS_ACTIVE.set(sessions_count)
                except Exception as e:
                    logger.debug(f"Could not query sessions table: {e}")
                    SESSIONS_ACTIVE.set(0)

                logger.debug(
                    f"Business metrics: users={users_count if 'users_count' in locals() else 0}, "
                    f"api_keys={api_keys_count if 'api_keys_count' in locals() else 0}, "
                    f"sessions={sessions_count if 'sessions_count' in locals() else 0}"
                )

        except Exception as e:
            logger.error(f"Failed to collect business metrics: {e}")


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


async def start_metrics_collector(collection_interval: int = 30) -> MetricsCollector:
    """
    Start the global metrics collector.

    This should be called during application startup.

    Args:
        collection_interval: Interval in seconds between metric collections (default: 30)

    Returns:
        The metrics collector instance

    Example:
        >>> from fastapi import FastAPI
        >>> from agent_service.infrastructure.observability.metrics_collectors import start_metrics_collector
        >>>
        >>> app = FastAPI()
        >>>
        >>> @app.on_event("startup")
        >>> async def startup():
        ...     await start_metrics_collector(collection_interval=30)
    """
    global _metrics_collector

    if _metrics_collector is not None:
        logger.warning("Metrics collector already started")
        return _metrics_collector

    _metrics_collector = MetricsCollector(collection_interval=collection_interval)
    await _metrics_collector.start()

    return _metrics_collector


async def stop_metrics_collector() -> None:
    """
    Stop the global metrics collector.

    This should be called during application shutdown.

    Example:
        >>> from fastapi import FastAPI
        >>> from agent_service.infrastructure.observability.metrics_collectors import stop_metrics_collector
        >>>
        >>> app = FastAPI()
        >>>
        >>> @app.on_event("shutdown")
        >>> async def shutdown():
        ...     await stop_metrics_collector()
    """
    global _metrics_collector

    if _metrics_collector is not None:
        await _metrics_collector.stop()
        _metrics_collector = None


@asynccontextmanager
async def metrics_collector_lifespan(collection_interval: int = 30):
    """
    Context manager for metrics collector lifecycle.

    Use this with FastAPI's lifespan context manager for clean startup/shutdown.

    Args:
        collection_interval: Interval in seconds between metric collections (default: 30)

    Example:
        >>> from fastapi import FastAPI
        >>> from contextlib import asynccontextmanager
        >>> from agent_service.infrastructure.observability.metrics_collectors import metrics_collector_lifespan
        >>>
        >>> @asynccontextmanager
        >>> async def lifespan(app: FastAPI):
        ...     async with metrics_collector_lifespan(collection_interval=30):
        ...         yield
        >>>
        >>> app = FastAPI(lifespan=lifespan)
    """
    collector = await start_metrics_collector(collection_interval=collection_interval)
    try:
        yield collector
    finally:
        await stop_metrics_collector()
