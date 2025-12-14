# src/agent_service/infrastructure/cache/cache.py
"""
Cache abstraction layer with Redis and in-memory implementations.

Provides a unified interface for caching operations with automatic fallback
to in-memory cache when Redis is unavailable.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, Any
from datetime import timedelta
from collections import OrderedDict
from threading import Lock

from redis.asyncio import Redis
from redis.exceptions import RedisError

from agent_service.infrastructure.cache.redis import get_redis_manager

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ICache(ABC, Generic[T]):
    """
    Abstract cache interface.

    Defines the contract for cache implementations supporting basic
    cache operations with TTL support.
    """

    @abstractmethod
    async def get(self, key: str) -> T | None:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        pass

    @abstractmethod
    async def set(self, key: str, value: T, ttl: int | None = None) -> bool:
        """
        Set value in cache with optional TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None = no expiration)

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        pass

    @abstractmethod
    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment numeric value in cache.

        Args:
            key: Cache key
            amount: Amount to increment by

        Returns:
            New value after increment
        """
        pass

    @abstractmethod
    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration on existing key.

        Args:
            key: Cache key
            ttl: Time to live in seconds

        Returns:
            True if successful, False if key doesn't exist
        """
        pass


class RedisCache(ICache[T]):
    """
    Redis-based cache implementation.

    Uses Redis for distributed caching with automatic serialization
    and deserialization of Python objects.

    Features:
    - JSON serialization for complex types
    - Namespace support for key isolation
    - Automatic connection management
    - Graceful error handling

    Example:
        >>> cache = RedisCache(namespace="users")
        >>> await cache.set("user:123", {"name": "John"}, ttl=300)
        >>> user = await cache.get("user:123")
        >>> print(user["name"])  # "John"
    """

    def __init__(self, namespace: str = ""):
        """
        Initialize Redis cache.

        Args:
            namespace: Namespace prefix for all keys
        """
        self.namespace = namespace
        self._redis: Optional[Redis] = None

    async def _get_redis(self) -> Redis | None:
        """Get Redis client, initializing if needed."""
        if self._redis is None:
            manager = await get_redis_manager()
            self._redis = manager.get_client()
        return self._redis

    def _make_key(self, key: str) -> str:
        """Create namespaced key."""
        if self.namespace:
            return f"{self.namespace}:{key}"
        return key

    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string."""
        try:
            return json.dumps(value)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize value: {e}")
            raise

    def _deserialize(self, value: str) -> Any:
        """Deserialize JSON string to value."""
        try:
            return json.loads(value)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to deserialize value: {e}")
            return value  # Return as-is if not JSON

    async def get(self, key: str) -> T | None:
        """Get value from Redis cache."""
        redis = await self._get_redis()
        if not redis:
            return None

        try:
            namespaced_key = self._make_key(key)
            value = await redis.get(namespaced_key)

            if value is None:
                return None

            return self._deserialize(value)
        except RedisError as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: T, ttl: int | None = None) -> bool:
        """Set value in Redis cache with optional TTL."""
        redis = await self._get_redis()
        if not redis:
            return False

        try:
            namespaced_key = self._make_key(key)
            serialized_value = self._serialize(value)

            if ttl is not None:
                await redis.setex(namespaced_key, ttl, serialized_value)
            else:
                await redis.set(namespaced_key, serialized_value)

            return True
        except RedisError as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from Redis cache."""
        redis = await self._get_redis()
        if not redis:
            return False

        try:
            namespaced_key = self._make_key(key)
            result = await redis.delete(namespaced_key)
            return result > 0
        except RedisError as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache."""
        redis = await self._get_redis()
        if not redis:
            return False

        try:
            namespaced_key = self._make_key(key)
            result = await redis.exists(namespaced_key)
            return result > 0
        except RedisError as e:
            logger.error(f"Redis exists error for key {key}: {e}")
            return False

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment numeric value in Redis cache."""
        redis = await self._get_redis()
        if not redis:
            raise RuntimeError("Redis not available for increment operation")

        try:
            namespaced_key = self._make_key(key)
            result = await redis.incrby(namespaced_key, amount)
            return result
        except RedisError as e:
            logger.error(f"Redis increment error for key {key}: {e}")
            raise

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on existing key in Redis cache."""
        redis = await self._get_redis()
        if not redis:
            return False

        try:
            namespaced_key = self._make_key(key)
            result = await redis.expire(namespaced_key, ttl)
            return result
        except RedisError as e:
            logger.error(f"Redis expire error for key {key}: {e}")
            return False


class InMemoryCache(ICache[T]):
    """
    In-memory cache implementation with LRU eviction.

    Fallback cache implementation when Redis is unavailable.
    Uses OrderedDict for LRU eviction and thread-safe operations.

    Features:
    - LRU eviction when max size reached
    - TTL support with lazy expiration
    - Thread-safe operations
    - Namespace support

    Limitations:
    - Not distributed (single process only)
    - Data lost on restart
    - Limited by available memory

    Example:
        >>> cache = InMemoryCache(max_size=1000, namespace="sessions")
        >>> await cache.set("session:abc", {"user_id": "123"}, ttl=300)
        >>> session = await cache.get("session:abc")
    """

    def __init__(self, max_size: int = 10000, namespace: str = ""):
        """
        Initialize in-memory cache.

        Args:
            max_size: Maximum number of items to store
            namespace: Namespace prefix for all keys
        """
        self.max_size = max_size
        self.namespace = namespace
        self._cache: OrderedDict[str, tuple[Any, Optional[float]]] = OrderedDict()
        self._lock = Lock()

    def _make_key(self, key: str) -> str:
        """Create namespaced key."""
        if self.namespace:
            return f"{self.namespace}:{key}"
        return key

    def _is_expired(self, expiry: Optional[float]) -> bool:
        """Check if item has expired."""
        if expiry is None:
            return False

        import time
        return time.time() > expiry

    def _evict_if_needed(self) -> None:
        """Evict oldest item if cache is full."""
        if len(self._cache) >= self.max_size:
            # Remove oldest item (first item in OrderedDict)
            self._cache.popitem(last=False)

    async def get(self, key: str) -> T | None:
        """Get value from in-memory cache."""
        namespaced_key = self._make_key(key)

        with self._lock:
            if namespaced_key not in self._cache:
                return None

            value, expiry = self._cache[namespaced_key]

            # Check if expired
            if self._is_expired(expiry):
                del self._cache[namespaced_key]
                return None

            # Move to end (mark as recently used)
            self._cache.move_to_end(namespaced_key)
            return value

    async def set(self, key: str, value: T, ttl: int | None = None) -> bool:
        """Set value in in-memory cache with optional TTL."""
        namespaced_key = self._make_key(key)

        import time
        expiry = None
        if ttl is not None:
            expiry = time.time() + ttl

        with self._lock:
            # Remove old value if exists
            if namespaced_key in self._cache:
                del self._cache[namespaced_key]

            # Evict if needed before adding
            self._evict_if_needed()

            # Add new value
            self._cache[namespaced_key] = (value, expiry)

        return True

    async def delete(self, key: str) -> bool:
        """Delete key from in-memory cache."""
        namespaced_key = self._make_key(key)

        with self._lock:
            if namespaced_key in self._cache:
                del self._cache[namespaced_key]
                return True
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in in-memory cache."""
        namespaced_key = self._make_key(key)

        with self._lock:
            if namespaced_key not in self._cache:
                return False

            _, expiry = self._cache[namespaced_key]

            # Check if expired
            if self._is_expired(expiry):
                del self._cache[namespaced_key]
                return False

            return True

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment numeric value in in-memory cache."""
        namespaced_key = self._make_key(key)

        with self._lock:
            if namespaced_key in self._cache:
                value, expiry = self._cache[namespaced_key]

                # Check if expired
                if self._is_expired(expiry):
                    del self._cache[namespaced_key]
                    new_value = amount
                else:
                    if not isinstance(value, (int, float)):
                        raise ValueError(f"Cannot increment non-numeric value: {type(value)}")
                    new_value = value + amount

                self._cache[namespaced_key] = (new_value, expiry)
                self._cache.move_to_end(namespaced_key)
            else:
                new_value = amount
                self._evict_if_needed()
                self._cache[namespaced_key] = (new_value, None)

            return new_value

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on existing key in in-memory cache."""
        namespaced_key = self._make_key(key)

        import time
        expiry = time.time() + ttl

        with self._lock:
            if namespaced_key not in self._cache:
                return False

            value, _ = self._cache[namespaced_key]
            self._cache[namespaced_key] = (value, expiry)
            return True

    def clear(self) -> None:
        """Clear all items from cache."""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)


async def get_cache(namespace: str = "", fallback_to_memory: bool = True) -> ICache:
    """
    Get cache instance with automatic fallback.

    Returns Redis cache if available, otherwise falls back to in-memory cache.

    Args:
        namespace: Namespace prefix for cache keys
        fallback_to_memory: If True, use in-memory cache when Redis unavailable

    Returns:
        Cache instance (Redis or in-memory)

    Example:
        >>> cache = await get_cache(namespace="users")
        >>> await cache.set("user:123", {"name": "John"}, ttl=300)
    """
    from agent_service.infrastructure.cache.redis import get_redis_manager

    manager = await get_redis_manager()

    if manager.is_available:
        logger.debug(f"Using Redis cache with namespace: {namespace}")
        return RedisCache(namespace=namespace)
    elif fallback_to_memory:
        logger.warning(f"Redis unavailable, using in-memory cache with namespace: {namespace}")
        return InMemoryCache(namespace=namespace)
    else:
        raise RuntimeError("Redis cache not available and fallback disabled")
