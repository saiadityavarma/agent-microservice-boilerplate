# src/agent_service/infrastructure/cache/redis.py
"""
Redis connection manager for caching and rate limiting.

Provides async Redis connection pool with health checks and graceful fallback.
"""
import logging
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from collections import defaultdict
from datetime import datetime

from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from agent_service.config.settings import get_settings

logger = logging.getLogger(__name__)


class CacheMetrics:
    """
    Cache metrics collector for monitoring cache performance.

    Tracks hits, misses, errors, and other cache operations for observability.
    """

    def __init__(self):
        self._metrics: Dict[str, int] = defaultdict(int)
        self._last_reset: datetime = datetime.utcnow()

    def record_hit(self, namespace: str = "default") -> None:
        """Record a cache hit."""
        self._metrics[f"{namespace}:hits"] += 1

    def record_miss(self, namespace: str = "default") -> None:
        """Record a cache miss."""
        self._metrics[f"{namespace}:misses"] += 1

    def record_error(self, namespace: str = "default") -> None:
        """Record a cache error."""
        self._metrics[f"{namespace}:errors"] += 1

    def record_set(self, namespace: str = "default") -> None:
        """Record a cache set operation."""
        self._metrics[f"{namespace}:sets"] += 1

    def record_delete(self, namespace: str = "default") -> None:
        """Record a cache delete operation."""
        self._metrics[f"{namespace}:deletes"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get all metrics.

        Returns:
            Dictionary with metrics and metadata
        """
        return {
            "metrics": dict(self._metrics),
            "last_reset": self._last_reset.isoformat(),
            "uptime_seconds": (datetime.utcnow() - self._last_reset).total_seconds()
        }

    def get_hit_rate(self, namespace: str = "default") -> float:
        """
        Calculate cache hit rate for a namespace.

        Returns:
            Hit rate as a percentage (0-100)
        """
        hits = self._metrics.get(f"{namespace}:hits", 0)
        misses = self._metrics.get(f"{namespace}:misses", 0)
        total = hits + misses

        if total == 0:
            return 0.0

        return (hits / total) * 100

    def reset(self) -> None:
        """Reset all metrics."""
        self._metrics.clear()
        self._last_reset = datetime.utcnow()


class RedisManager:
    """
    Redis connection manager with async connection pool.

    Features:
    - Async connection pool for efficiency
    - Health checks to verify Redis availability
    - Graceful fallback when Redis is unavailable
    - Automatic connection cleanup
    """

    def __init__(self):
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None
        self._is_available: bool = False
        self._settings = get_settings()
        self.metrics = CacheMetrics()

    async def initialize(self) -> None:
        """
        Initialize Redis connection pool.

        Creates connection pool and verifies connectivity.
        Logs errors but doesn't raise - allows graceful degradation.
        """
        if not self._settings.redis_url:
            logger.warning("Redis URL not configured - Redis features will be disabled")
            self._is_available = False
            return

        try:
            # Get the actual string value from SecretStr
            redis_url = self._settings.redis_url.get_secret_value()

            # Create connection pool
            self._pool = ConnectionPool.from_url(
                redis_url,
                decode_responses=True,
                max_connections=10,
                socket_connect_timeout=5,
                socket_keepalive=True,
            )

            # Create Redis client
            self._client = Redis(connection_pool=self._pool)

            # Verify connection
            await self._client.ping()
            self._is_available = True
            logger.info("Redis connection established successfully")

        except (RedisError, RedisConnectionError, Exception) as e:
            logger.error(f"Failed to connect to Redis: {e}")
            logger.warning("Redis features will be disabled - continuing without cache")
            self._is_available = False
            self._client = None
            self._pool = None

    async def close(self) -> None:
        """
        Close Redis connection and cleanup resources.

        Should be called during application shutdown.
        """
        if self._client:
            try:
                await self._client.aclose()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")

        if self._pool:
            try:
                await self._pool.aclose()
            except Exception as e:
                logger.error(f"Error closing Redis connection pool: {e}")

        self._client = None
        self._pool = None
        self._is_available = False

    async def health_check(self) -> bool:
        """
        Perform health check on Redis connection.

        Returns:
            bool: True if Redis is available and responding, False otherwise
        """
        if not self._is_available or not self._client:
            return False

        try:
            await self._client.ping()
            return True
        except (RedisError, RedisConnectionError, Exception) as e:
            logger.error(f"Redis health check failed: {e}")
            self._is_available = False
            return False

    def get_client(self) -> Optional[Redis]:
        """
        Get Redis client instance.

        Returns:
            Redis client if available, None otherwise
        """
        return self._client if self._is_available else None

    @property
    def is_available(self) -> bool:
        """Check if Redis is available."""
        return self._is_available

    async def scan_keys(self, pattern: str, count: int = 100) -> List[str]:
        """
        Scan for keys matching a pattern.

        Uses SCAN command for efficient iteration over large keyspaces.

        Args:
            pattern: Key pattern with wildcards (e.g., "users:*")
            count: Number of keys to scan per iteration

        Returns:
            List of matching keys

        Example:
            >>> manager = await get_redis_manager()
            >>> keys = await manager.scan_keys("users:*")
            >>> print(f"Found {len(keys)} user keys")
        """
        if not self._is_available or not self._client:
            return []

        try:
            keys = []
            cursor = 0

            while True:
                cursor, batch = await self._client.scan(
                    cursor=cursor,
                    match=pattern,
                    count=count
                )
                keys.extend(batch)

                if cursor == 0:
                    break

            return keys

        except (RedisError, RedisConnectionError, Exception) as e:
            logger.error(f"Redis scan_keys error for pattern {pattern}: {e}")
            return []

    async def mget(self, keys: List[str]) -> List[Optional[str]]:
        """
        Get multiple values at once.

        Args:
            keys: List of keys to retrieve

        Returns:
            List of values (None for missing keys)

        Example:
            >>> manager = await get_redis_manager()
            >>> values = await manager.mget(["key1", "key2", "key3"])
        """
        if not self._is_available or not self._client:
            return [None] * len(keys)

        try:
            values = await self._client.mget(keys)
            return values
        except (RedisError, RedisConnectionError, Exception) as e:
            logger.error(f"Redis mget error: {e}")
            return [None] * len(keys)

    async def mset(self, mapping: Dict[str, str]) -> bool:
        """
        Set multiple key-value pairs at once.

        Args:
            mapping: Dictionary of key-value pairs

        Returns:
            True if successful, False otherwise

        Example:
            >>> manager = await get_redis_manager()
            >>> await manager.mset({"key1": "value1", "key2": "value2"})
        """
        if not self._is_available or not self._client:
            return False

        try:
            await self._client.mset(mapping)
            return True
        except (RedisError, RedisConnectionError, Exception) as e:
            logger.error(f"Redis mset error: {e}")
            return False

    def make_namespaced_key(self, namespace: str, key: str) -> str:
        """
        Create namespaced key.

        Args:
            namespace: Namespace prefix
            key: Key name

        Returns:
            Namespaced key in format "namespace:key"

        Example:
            >>> manager = await get_redis_manager()
            >>> key = manager.make_namespaced_key("users", "123")
            >>> # Returns: "users:123"
        """
        if namespace:
            return f"{namespace}:{key}"
        return key

    async def delete_by_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Key pattern with wildcards

        Returns:
            Number of keys deleted

        Example:
            >>> manager = await get_redis_manager()
            >>> deleted = await manager.delete_by_pattern("temp:*")
            >>> print(f"Deleted {deleted} temporary keys")
        """
        if not self._is_available or not self._client:
            return 0

        try:
            keys = await self.scan_keys(pattern)
            if keys:
                deleted = await self._client.delete(*keys)
                return deleted
            return 0
        except (RedisError, RedisConnectionError, Exception) as e:
            logger.error(f"Redis delete_by_pattern error for pattern {pattern}: {e}")
            return 0

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get cache metrics.

        Returns:
            Dictionary with cache performance metrics

        Example:
            >>> manager = await get_redis_manager()
            >>> metrics = manager.get_metrics()
            >>> print(f"Cache hit rate: {metrics['hit_rate']}%")
        """
        return self.metrics.get_metrics()

    def get_hit_rate(self, namespace: str = "default") -> float:
        """
        Get cache hit rate for a namespace.

        Args:
            namespace: Cache namespace

        Returns:
            Hit rate as a percentage (0-100)
        """
        return self.metrics.get_hit_rate(namespace)

    def reset_metrics(self) -> None:
        """Reset cache metrics."""
        self.metrics.reset()


# Global Redis manager instance
_redis_manager: Optional[RedisManager] = None


async def get_redis_manager() -> RedisManager:
    """
    Get or create the global Redis manager instance.

    Returns:
        RedisManager: The global Redis manager instance
    """
    global _redis_manager

    if _redis_manager is None:
        _redis_manager = RedisManager()
        await _redis_manager.initialize()

    return _redis_manager


async def get_redis() -> Optional[Redis]:
    """
    Get Redis client instance.

    This is the main function to use when you need a Redis client.
    Returns None if Redis is unavailable - caller should handle gracefully.

    Returns:
        Redis client if available, None otherwise
    """
    manager = await get_redis_manager()
    return manager.get_client()


async def close_redis() -> None:
    """
    Close Redis connection.

    Should be called during application shutdown.
    """
    global _redis_manager

    if _redis_manager:
        await _redis_manager.close()
        _redis_manager = None


@asynccontextmanager
async def get_redis_context():
    """
    Context manager for Redis operations.

    Usage:
        async with get_redis_context() as redis:
            if redis:
                await redis.set("key", "value")

    Yields:
        Redis client if available, None otherwise
    """
    redis = await get_redis()
    try:
        yield redis
    finally:
        # Connection is managed by the pool, no cleanup needed
        pass
