"""Caching implementations."""

from agent_service.infrastructure.cache.cache import (
    ICache,
    RedisCache,
    InMemoryCache,
    get_cache,
)
from agent_service.infrastructure.cache.decorators import (
    cached,
    cache_invalidate,
    cached_property,
    CacheContext,
    invalidate_cache_key,
    invalidate_cache_pattern,
)
from agent_service.infrastructure.cache.redis import (
    RedisManager,
    CacheMetrics,
    get_redis_manager,
    get_redis,
    close_redis,
    get_redis_context,
)

__all__ = [
    # Cache abstractions
    "ICache",
    "RedisCache",
    "InMemoryCache",
    "get_cache",
    # Decorators
    "cached",
    "cache_invalidate",
    "cached_property",
    "CacheContext",
    "invalidate_cache_key",
    "invalidate_cache_pattern",
    # Redis manager
    "RedisManager",
    "CacheMetrics",
    "get_redis_manager",
    "get_redis",
    "close_redis",
    "get_redis_context",
]
