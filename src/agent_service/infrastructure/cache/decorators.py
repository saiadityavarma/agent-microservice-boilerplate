# src/agent_service/infrastructure/cache/decorators.py
"""
Caching decorators for function result memoization.

Provides decorators to cache function results with automatic key generation,
TTL support, and cache invalidation patterns.
"""

import asyncio
import functools
import hashlib
import inspect
import json
import logging
from typing import Any, Callable, Optional, TypeVar, ParamSpec, Awaitable

from agent_service.infrastructure.cache.cache import get_cache, ICache
from agent_service.config.settings import get_settings

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def _generate_cache_key(
    func: Callable,
    key_prefix: str,
    args: tuple,
    kwargs: dict,
    include_args: bool = True
) -> str:
    """
    Generate cache key from function name and arguments.

    Args:
        func: Function being cached
        key_prefix: Prefix for the cache key
        args: Positional arguments
        kwargs: Keyword arguments
        include_args: Whether to include arguments in key

    Returns:
        Cache key string

    Example:
        >>> def my_func(user_id, limit=10): pass
        >>> key = _generate_cache_key(my_func, "users", (123,), {"limit": 10})
        >>> # Returns: "users:my_func:hash_of_args"
    """
    # Start with prefix and function name
    parts = []
    if key_prefix:
        parts.append(key_prefix)
    parts.append(func.__name__)

    # Add arguments if requested
    if include_args and (args or kwargs):
        # Create deterministic representation of arguments
        # Skip 'self' or 'cls' for methods
        func_signature = inspect.signature(func)
        param_names = list(func_signature.parameters.keys())

        # Skip first param if it's self/cls
        if param_names and param_names[0] in ("self", "cls"):
            args = args[1:]

        # Create argument dict for hashing
        arg_dict = {}

        # Add positional args
        for i, arg in enumerate(args):
            if i < len(param_names):
                arg_dict[param_names[i]] = arg

        # Add keyword args
        arg_dict.update(kwargs)

        # Serialize and hash arguments
        try:
            arg_str = json.dumps(arg_dict, sort_keys=True, default=str)
            arg_hash = hashlib.md5(arg_str.encode()).hexdigest()[:12]
            parts.append(arg_hash)
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize arguments for cache key: {e}")
            # Fallback to string representation
            arg_str = str((args, sorted(kwargs.items())))
            arg_hash = hashlib.md5(arg_str.encode()).hexdigest()[:12]
            parts.append(arg_hash)

    return ":".join(parts)


def cached(
    ttl: int | None = None,
    key_prefix: str = "",
    namespace: str = "",
    include_args: bool = True,
    cache_none: bool = False
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """
    Decorator to cache async function results.

    Caches the return value of async functions with automatic key generation
    based on function name and arguments. Supports custom TTL and key prefixes.

    Args:
        ttl: Time to live in seconds (None = use default from settings)
        key_prefix: Prefix for cache keys (default: empty)
        namespace: Cache namespace for isolation (default: from settings)
        include_args: Include function arguments in cache key (default: True)
        cache_none: Whether to cache None results (default: False)

    Returns:
        Decorator function

    Example:
        >>> @cached(ttl=300, key_prefix="users")
        >>> async def get_user(user_id: str):
        >>>     # Expensive database query
        >>>     return await db.get_user(user_id)
        >>>
        >>> # First call hits database
        >>> user = await get_user("123")
        >>> # Second call returns cached result
        >>> user = await get_user("123")

    Example with custom namespace:
        >>> @cached(ttl=60, namespace="api_responses", key_prefix="weather")
        >>> async def get_weather(city: str):
        >>>     return await api.fetch_weather(city)
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            settings = get_settings()

            # Determine TTL
            cache_ttl = ttl if ttl is not None else settings.cache_default_ttl

            # Determine namespace
            cache_namespace = namespace or settings.cache_key_prefix

            # Get cache instance
            try:
                cache = await get_cache(namespace=cache_namespace)
            except Exception as e:
                logger.error(f"Failed to get cache, executing function directly: {e}")
                return await func(*args, **kwargs)

            # Generate cache key
            cache_key = _generate_cache_key(
                func=func,
                key_prefix=key_prefix,
                args=args,
                kwargs=kwargs,
                include_args=include_args
            )

            # Try to get from cache
            try:
                cached_value = await cache.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit for key: {cache_key}")
                    return cached_value
                logger.debug(f"Cache miss for key: {cache_key}")
            except Exception as e:
                logger.error(f"Cache get error for key {cache_key}: {e}")
                # Continue to execute function on cache error

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result if not None or if cache_none=True
            if result is not None or cache_none:
                try:
                    await cache.set(cache_key, result, ttl=cache_ttl)
                    logger.debug(f"Cached result for key: {cache_key} (ttl={cache_ttl}s)")
                except Exception as e:
                    logger.error(f"Cache set error for key {cache_key}: {e}")

            return result

        return wrapper

    return decorator


def cache_invalidate(
    key_pattern: str = "",
    namespace: str = ""
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """
    Decorator to invalidate cache entries after function execution.

    Useful for mutation operations that should invalidate cached data.
    Requires the enhanced RedisManager with scan_keys support.

    Args:
        key_pattern: Pattern for keys to invalidate (supports wildcards)
        namespace: Cache namespace (default: from settings)

    Returns:
        Decorator function

    Example:
        >>> @cache_invalidate(key_pattern="users:get_user:*")
        >>> async def update_user(user_id: str, data: dict):
        >>>     # Update user in database
        >>>     await db.update_user(user_id, data)
        >>>
        >>> # After this call, all cached get_user results are invalidated
        >>> await update_user("123", {"name": "New Name"})

    Example with specific key:
        >>> @cache_invalidate(key_pattern="users:get_user:123")
        >>> async def update_specific_user(data: dict):
        >>>     await db.update_user("123", data)
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Execute function first
            result = await func(*args, **kwargs)

            # Invalidate cache after successful execution
            if key_pattern:
                settings = get_settings()
                cache_namespace = namespace or settings.cache_key_prefix

                try:
                    from agent_service.infrastructure.cache.redis import get_redis_manager

                    manager = await get_redis_manager()
                    redis = manager.get_client()

                    if redis:
                        # Build full pattern with namespace
                        full_pattern = f"{cache_namespace}:{key_pattern}" if cache_namespace else key_pattern

                        # Scan and delete matching keys
                        # Note: This requires the scan_keys method added to RedisManager
                        keys = await manager.scan_keys(full_pattern)
                        if keys:
                            deleted = await redis.delete(*keys)
                            logger.info(f"Invalidated {deleted} cache keys matching pattern: {full_pattern}")
                        else:
                            logger.debug(f"No cache keys found matching pattern: {full_pattern}")
                    else:
                        logger.warning("Redis not available, cache invalidation skipped")

                except Exception as e:
                    logger.error(f"Cache invalidation error for pattern {key_pattern}: {e}")
                    # Don't fail the function if cache invalidation fails

            return result

        return wrapper

    return decorator


class CacheContext:
    """
    Context manager for manual cache operations.

    Provides a convenient way to work with cache within a context,
    with automatic namespace handling.

    Example:
        >>> async with CacheContext(namespace="sessions") as cache:
        >>>     await cache.set("session:abc", {"user_id": "123"}, ttl=300)
        >>>     session = await cache.get("session:abc")
    """

    def __init__(self, namespace: str = ""):
        """
        Initialize cache context.

        Args:
            namespace: Cache namespace
        """
        self.namespace = namespace
        self._cache: Optional[ICache] = None

    async def __aenter__(self) -> ICache:
        """Enter context and return cache instance."""
        settings = get_settings()
        cache_namespace = self.namespace or settings.cache_key_prefix
        self._cache = await get_cache(namespace=cache_namespace)
        return self._cache

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context (no cleanup needed)."""
        pass


def cached_property(ttl: int | None = None, key_prefix: str = ""):
    """
    Decorator for caching property values.

    Similar to @cached but for class properties. Caches the property value
    per instance using the instance's id as part of the cache key.

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache keys

    Returns:
        Property decorator

    Example:
        >>> class UserService:
        >>>     def __init__(self, user_id: str):
        >>>         self.user_id = user_id
        >>>
        >>>     @cached_property(ttl=300, key_prefix="user_profile")
        >>>     async def profile(self):
        >>>         # Expensive operation
        >>>         return await db.get_user_profile(self.user_id)
        >>>
        >>> service = UserService("123")
        >>> profile = await service.profile  # Fetches from DB
        >>> profile = await service.profile  # Returns cached value
    """

    def decorator(func: Callable[[Any], Awaitable[R]]) -> property:
        @functools.wraps(func)
        async def wrapper(self) -> R:
            settings = get_settings()
            cache_ttl = ttl if ttl is not None else settings.cache_default_ttl

            # Get cache instance
            try:
                cache = await get_cache(namespace=settings.cache_key_prefix)
            except Exception as e:
                logger.error(f"Failed to get cache, executing function directly: {e}")
                return await func(self)

            # Generate cache key with instance id
            instance_id = id(self)
            cache_key = f"{key_prefix}:{func.__name__}:{instance_id}"

            # Try to get from cache
            try:
                cached_value = await cache.get(cache_key)
                if cached_value is not None:
                    return cached_value
            except Exception as e:
                logger.error(f"Cache get error for key {cache_key}: {e}")

            # Execute function
            result = await func(self)

            # Cache result
            if result is not None:
                try:
                    await cache.set(cache_key, result, ttl=cache_ttl)
                except Exception as e:
                    logger.error(f"Cache set error for key {cache_key}: {e}")

            return result

        # Return as property to maintain property semantics
        return property(lambda self: wrapper(self))

    return decorator


async def invalidate_cache_key(key: str, namespace: str = "") -> bool:
    """
    Manually invalidate a specific cache key.

    Utility function for programmatic cache invalidation.

    Args:
        key: Cache key to invalidate
        namespace: Cache namespace

    Returns:
        True if key was deleted, False otherwise

    Example:
        >>> await invalidate_cache_key("users:get_user:123", namespace="api")
    """
    settings = get_settings()
    cache_namespace = namespace or settings.cache_key_prefix

    try:
        cache = await get_cache(namespace=cache_namespace)
        return await cache.delete(key)
    except Exception as e:
        logger.error(f"Failed to invalidate cache key {key}: {e}")
        return False


async def invalidate_cache_pattern(pattern: str, namespace: str = "") -> int:
    """
    Manually invalidate cache keys matching a pattern.

    Requires Redis with scan_keys support.

    Args:
        pattern: Key pattern (supports wildcards)
        namespace: Cache namespace

    Returns:
        Number of keys deleted

    Example:
        >>> # Invalidate all user cache entries
        >>> count = await invalidate_cache_pattern("users:*", namespace="api")
        >>> print(f"Invalidated {count} cache entries")
    """
    settings = get_settings()
    cache_namespace = namespace or settings.cache_key_prefix

    try:
        from agent_service.infrastructure.cache.redis import get_redis_manager

        manager = await get_redis_manager()
        redis = manager.get_client()

        if not redis:
            logger.warning("Redis not available, cache invalidation skipped")
            return 0

        # Build full pattern with namespace
        full_pattern = f"{cache_namespace}:{pattern}" if cache_namespace else pattern

        # Scan and delete matching keys
        keys = await manager.scan_keys(full_pattern)
        if keys:
            deleted = await redis.delete(*keys)
            logger.info(f"Invalidated {deleted} cache keys matching pattern: {full_pattern}")
            return deleted

        return 0

    except Exception as e:
        logger.error(f"Failed to invalidate cache pattern {pattern}: {e}")
        return 0
