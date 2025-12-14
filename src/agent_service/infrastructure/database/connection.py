# src/agent_service/infrastructure/database/connection.py
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages async database connections with configurable pool settings and health monitoring.

    Features:
    - Configurable connection pooling (size, overflow, timeout, recycle)
    - Connection health checks via pool_pre_ping
    - Pool statistics and monitoring
    - Graceful shutdown with connection cleanup
    - Automatic session management with commit/rollback

    Usage:
        db = DatabaseManager()
        await db.connect(
            url="postgresql+asyncpg://...",
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=3600,
            echo_sql=False
        )
        async with db.session() as session:
            # use session
        await db.disconnect()
    """

    def __init__(self):
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        self._pool_size: int = 5
        self._max_overflow: int = 10
        self._pool_timeout: int = 30
        self._pool_recycle: int = 3600

    async def connect(
        self,
        url: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
        echo_sql: bool = False,
    ) -> None:
        """
        Connect to the database with configurable pool settings.

        Args:
            url: Database connection URL
            pool_size: Number of connections to maintain in the pool (default: 5)
            max_overflow: Max connections beyond pool_size (default: 10)
            pool_timeout: Timeout in seconds for getting a connection (default: 30)
            pool_recycle: Recycle connections after N seconds (default: 3600 = 1 hour)
            pool_pre_ping: Enable connection health checks (default: True)
            echo_sql: Log all SQL statements (default: False)

        Raises:
            RuntimeError: If already connected
        """
        if self._engine is not None:
            raise RuntimeError("Database already connected")

        # Store pool configuration for monitoring
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._pool_timeout = pool_timeout
        self._pool_recycle = pool_recycle

        # Create async engine with pool configuration
        self._engine = create_async_engine(
            url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=pool_pre_ping,
            echo=echo_sql,
        )

        # Create session factory
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        logger.info(
            "Database connected",
            extra={
                "pool_size": pool_size,
                "max_overflow": max_overflow,
                "pool_timeout": pool_timeout,
                "pool_recycle": pool_recycle,
                "pool_pre_ping": pool_pre_ping,
            }
        )

    async def disconnect(self) -> None:
        """
        Gracefully disconnect from the database and cleanup all connections.

        This will:
        1. Dispose of the engine
        2. Close all connections in the pool
        3. Clean up session factory

        Safe to call multiple times.
        """
        if self._engine:
            logger.info("Disconnecting from database and cleaning up connections")
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database disconnected")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session with automatic commit/rollback.

        Yields:
            AsyncSession: Database session

        Raises:
            RuntimeError: If database not connected

        Usage:
            async with db.session() as session:
                result = await session.execute(select(User))
                # session automatically committed on success
        """
        if not self._session_factory:
            raise RuntimeError("Database not connected. Call connect() first.")

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def get_pool_stats(self) -> Dict[str, Any]:
        """
        Get current connection pool statistics for monitoring.

        Returns:
            Dictionary containing pool statistics:
            - pool_size: Configured pool size
            - max_overflow: Configured max overflow
            - pool_timeout: Configured timeout
            - pool_recycle: Configured recycle time
            - checked_in: Number of connections currently checked in
            - checked_out: Number of connections currently checked out
            - overflow: Number of overflow connections
            - total: Total number of connections

        Raises:
            RuntimeError: If database not connected

        Example:
            >>> stats = db.get_pool_stats()
            >>> print(f"Active connections: {stats['checked_out']}")
        """
        if not self._engine:
            raise RuntimeError("Database not connected")

        pool = self._engine.pool
        return {
            "pool_size": self._pool_size,
            "max_overflow": self._max_overflow,
            "pool_timeout": self._pool_timeout,
            "pool_recycle": self._pool_recycle,
            "checked_in": pool.checkedin() if hasattr(pool, 'checkedin') else None,
            "checked_out": pool.checkedout() if hasattr(pool, 'checkedout') else None,
            "overflow": pool.overflow() if hasattr(pool, 'overflow') else None,
            "total": pool.size() if hasattr(pool, 'size') else None,
        }

    async def health_check(self) -> bool:
        """
        Perform a health check by executing a simple query.

        Returns:
            True if database is healthy, False otherwise

        Example:
            >>> is_healthy = await db.health_check()
            >>> if not is_healthy:
            ...     logger.error("Database health check failed")
        """
        if not self._engine:
            return False

        try:
            async with self.session() as session:
                await session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._engine is not None


# Global instance
db = DatabaseManager()
