# Redis Cache Layer and Session Storage Implementation

## Summary

This document provides an overview of the Redis cache layer and session storage implementation added to the agent service.

## Created Files

### 1. Cache Infrastructure

#### `/src/agent_service/infrastructure/cache/cache.py`
- **ICache**: Abstract cache interface defining the contract for all cache implementations
- **RedisCache**: Redis-based cache with JSON serialization and namespace support
- **InMemoryCache**: LRU-based in-memory fallback cache
- **get_cache()**: Factory function that returns Redis cache with automatic fallback to in-memory

**Key Features:**
- Generic type support for type safety
- Namespace isolation for different domains
- Automatic serialization/deserialization
- TTL support on all operations
- Graceful degradation when Redis is unavailable

#### `/src/agent_service/infrastructure/cache/decorators.py`
- **@cached**: Decorator for caching function results with automatic key generation
- **@cache_invalidate**: Decorator for invalidating cache entries after mutations
- **@cached_property**: Decorator for caching class property values
- **CacheContext**: Context manager for manual cache operations
- **invalidate_cache_key()**: Utility for programmatic cache invalidation
- **invalidate_cache_pattern()**: Utility for pattern-based cache invalidation

**Key Features:**
- Automatic key generation from function name and arguments
- Support for async functions
- Configurable TTL and namespaces
- Pattern-based invalidation with wildcards
- Custom key prefixes for organization

#### `/src/agent_service/infrastructure/cache/redis.py` (Enhanced)
Added the following enhancements to the existing RedisManager:

- **CacheMetrics**: Class for tracking cache performance metrics
  - Hit/miss tracking
  - Error tracking
  - Hit rate calculation
  - Per-namespace metrics

- **RedisManager** enhancements:
  - `scan_keys(pattern)`: Scan for keys matching a pattern
  - `mget(keys)`: Get multiple values at once
  - `mset(mapping)`: Set multiple key-value pairs at once
  - `make_namespaced_key(namespace, key)`: Create namespaced keys
  - `delete_by_pattern(pattern)`: Delete keys matching a pattern
  - `get_metrics()`: Get cache performance metrics
  - `get_hit_rate(namespace)`: Get hit rate for a namespace
  - `reset_metrics()`: Reset metrics

### 2. Session Repository

#### `/src/agent_service/infrastructure/database/repositories/session.py`
Comprehensive repository for managing conversation sessions with specialized methods:

**Core Methods:**
- `get_user_sessions()`: Get all sessions for a user
- `get_session_with_messages()`: Get session by ID with messages loaded
- `add_message_to_session()`: Add a message to a session
- `update_session_context()`: Update session context variables
- `cleanup_expired_sessions()`: Mark expired sessions as completed
- `get_session_stats()`: Get aggregated session statistics

**Query Methods:**
- `get_recent_sessions()`: Get sessions within a time window
- `get_sessions_by_agent()`: Get sessions for a specific agent
- `search_sessions()`: Search sessions by title
- `get_paginated_user_sessions()`: Get paginated sessions with filters
- `count_active_sessions()`: Count active sessions for a user
- `get_session_by_title()`: Get session by exact title match

**Bulk Operations:**
- `bulk_update_session_status()`: Update status for multiple sessions

**Analytics:**
- `SessionStats`: Named dict with session statistics
  - total_sessions
  - active_sessions
  - total_messages
  - total_tokens
  - avg_messages_per_session

### 3. Configuration

#### `/src/agent_service/config/settings.py` (Updated)
Added the following settings:

```python
# Cache Settings
cache_default_ttl: int = 300  # Default TTL in seconds (5 minutes)
cache_key_prefix: str = "agent_service"  # Prefix for all cache keys

# Session Settings
session_max_messages: int = 100  # Maximum messages per session
session_expiry_hours: int = 24  # Session expiry time in hours
```

### 4. Documentation and Examples

#### `/src/agent_service/infrastructure/cache/README.md`
Comprehensive documentation including:
- Feature overview
- Installation and configuration
- Quick start guide
- Complete API reference
- Cache strategies
- Best practices
- Monitoring and debugging
- Performance considerations
- Troubleshooting guide

#### `/src/agent_service/infrastructure/cache/USAGE_EXAMPLES.py`
12 complete working examples demonstrating:
1. Basic cache operations
2. Cache decorators
3. Cache context manager
4. Session repository operations
5. Paginated session queries
6. Scheduled session cleanup
7. Cache metrics
8. Advanced cache operations
9. Session search
10. Bulk session operations
11. Integration with caching
12. In-memory cache usage

## Architecture

### Cache Layer Architecture

```
┌─────────────────────────────────────────┐
│          Application Code               │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│       Cache Decorators Layer            │
│  (@cached, @cache_invalidate, etc.)     │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│          ICache Interface               │
└───────────────┬─────────────────────────┘
                │
        ┌───────┴───────┐
        │               │
┌───────▼──────┐  ┌────▼────────────┐
│ RedisCache   │  │ InMemoryCache   │
│ (Primary)    │  │ (Fallback)      │
└───────┬──────┘  └─────────────────┘
        │
┌───────▼──────────┐
│  RedisManager    │
│  + Metrics       │
└──────────────────┘
```

### Session Repository Architecture

```
┌─────────────────────────────────────────┐
│          Application Code               │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│       SessionRepository                 │
│  (Specialized session operations)       │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│        BaseRepository                   │
│  (Generic CRUD + pagination)            │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│        SQLAlchemy Session               │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│        PostgreSQL Database              │
│  (sessions table with JSONB fields)     │
└─────────────────────────────────────────┘
```

## Usage Patterns

### 1. Simple Function Caching

```python
from agent_service.infrastructure.cache import cached

@cached(ttl=300, key_prefix="users")
async def get_user(user_id: str):
    return await db.query_user(user_id)
```

### 2. Cache Invalidation on Mutation

```python
from agent_service.infrastructure.cache import cache_invalidate

@cache_invalidate(key_pattern="users:get_user:*")
async def update_user(user_id: str, data: dict):
    await db.update_user(user_id, data)
```

### 3. Session Management

```python
from agent_service.infrastructure.database.repositories import SessionRepository

async with get_session() as db:
    repo = SessionRepository(db)

    # Create session
    session = await repo.create(Session(...))

    # Add messages
    await repo.add_message_to_session(
        session_id=session.id,
        message={"role": "user", "content": "Hello"}
    )

    # Get stats
    stats = await repo.get_session_stats(user_id)
```

### 4. Scheduled Cleanup

```python
# In a cron job or scheduler
async def cleanup_sessions():
    async with get_session() as db:
        repo = SessionRepository(db)
        cleaned = await repo.cleanup_expired_sessions()
        await db.commit()
        logger.info(f"Cleaned {cleaned} expired sessions")
```

## Environment Variables

Add these to your `.env` file:

```env
# Redis
REDIS_URL=redis://localhost:6379/0

# Cache Settings
CACHE_DEFAULT_TTL=300
CACHE_KEY_PREFIX=agent_service

# Session Settings
SESSION_MAX_MESSAGES=100
SESSION_EXPIRY_HOURS=24
```

## Testing

### Cache Layer Testing

```python
# Test cache operations
async def test_cache():
    cache = await get_cache(namespace="test")

    # Test set/get
    await cache.set("key", {"value": "data"}, ttl=60)
    value = await cache.get("key")
    assert value == {"value": "data"}

    # Test delete
    deleted = await cache.delete("key")
    assert deleted is True

    # Test increment
    count = await cache.increment("counter")
    assert count == 1
```

### Session Repository Testing

```python
# Test session operations
async def test_session_repository():
    async with get_session() as db:
        repo = SessionRepository(db)

        # Create session
        session = Session(
            user_id=user_id,
            agent_id="test_agent",
            title="Test Session"
        )
        session = await repo.create(session)

        # Add message
        await repo.add_message_to_session(
            session_id=session.id,
            message={"role": "user", "content": "Test"}
        )

        # Verify
        session = await repo.get(session.id)
        assert len(session.messages) == 1
```

## Performance Considerations

### Cache Performance
- **Redis**: ~1ms latency for get/set operations
- **In-Memory**: <0.1ms latency, limited to process memory
- **Serialization**: JSON serialization adds ~0.1-0.5ms overhead

### Database Performance
- **Indexes**: All session queries use indexes for optimal performance
- **JSONB**: Message array stored as JSONB for efficient querying
- **Pagination**: Always use pagination for large result sets

### Scalability
- **Redis**: Horizontally scalable with Redis Cluster
- **PostgreSQL**: Vertical scaling, consider read replicas for heavy read loads
- **Sessions**: Automatic cleanup prevents database bloat

## Monitoring

### Cache Metrics
```python
manager = await get_redis_manager()
metrics = manager.get_metrics()
hit_rate = manager.get_hit_rate(namespace="users")

# Log metrics
logger.info(f"Cache hit rate: {hit_rate:.2f}%")
```

### Session Metrics
```python
stats = await repo.get_session_stats(user_id)
logger.info(
    f"User {user_id}: "
    f"{stats.total_sessions} sessions, "
    f"{stats.total_messages} messages, "
    f"{stats.avg_messages_per_session:.1f} avg msgs/session"
)
```

## Migration Guide

If you have existing sessions without the new fields:

```sql
-- Add indexes for performance
CREATE INDEX CONCURRENTLY idx_sessions_expires_at ON sessions(expires_at) WHERE expires_at IS NOT NULL;

-- Set default context/metadata for existing sessions
UPDATE sessions
SET context = '{}'::jsonb
WHERE context IS NULL;

UPDATE sessions
SET metadata = '{}'::jsonb
WHERE metadata IS NULL;
```

## Best Practices

1. **Always use namespaces** for cache keys to avoid collisions
2. **Set appropriate TTLs** based on data volatility
3. **Invalidate cache on mutations** to maintain consistency
4. **Monitor cache hit rates** to optimize caching strategy
5. **Use pagination** for large session queries
6. **Run cleanup jobs** regularly to maintain database health
7. **Handle cache failures gracefully** with fallback logic
8. **Use batch operations** when working with multiple keys

## Future Enhancements

Potential improvements to consider:

1. **Cache warming**: Pre-populate cache on startup
2. **Cache compression**: Compress large values before storing
3. **Full-text search**: Add PostgreSQL FTS for session content search
4. **Session archival**: Archive old sessions to cold storage
5. **Cache sharding**: Distribute cache across multiple Redis instances
6. **Rate limiting**: Use cache for distributed rate limiting
7. **Session snapshots**: Save session state at intervals for recovery

## Support

For questions or issues:
1. Check the README.md for detailed API documentation
2. Review USAGE_EXAMPLES.py for implementation examples
3. Check logs for error messages and stack traces
4. Verify Redis connectivity with `redis-cli ping`
5. Check database connectivity and schema

## Version History

- **v1.0.0** (2024-12-13): Initial implementation
  - Cache abstraction with Redis and in-memory implementations
  - Cache decorators for function memoization
  - SessionRepository with comprehensive session management
  - Metrics collection and monitoring
  - Complete documentation and examples
