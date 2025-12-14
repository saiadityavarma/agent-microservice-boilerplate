# Cache & Session Quick Reference

Quick reference for common cache and session operations.

## Cache Operations

### Get Cache Instance

```python
from agent_service.infrastructure.cache import get_cache

# Default namespace
cache = await get_cache()

# Custom namespace
cache = await get_cache(namespace="users")
```

### Basic Operations

```python
# Set with TTL (5 minutes)
await cache.set("key", {"data": "value"}, ttl=300)

# Get value
value = await cache.get("key")

# Delete
await cache.delete("key")

# Check existence
exists = await cache.exists("key")

# Increment counter
count = await cache.increment("counter", amount=1)

# Set expiration
await cache.expire("key", ttl=60)
```

### Decorators

```python
from agent_service.infrastructure.cache import cached, cache_invalidate

# Cache function results
@cached(ttl=300, key_prefix="users")
async def get_user(user_id: str):
    return await db.query_user(user_id)

# Invalidate on mutation
@cache_invalidate(key_pattern="users:*")
async def update_user(user_id: str, data: dict):
    await db.update_user(user_id, data)
```

### Context Manager

```python
from agent_service.infrastructure.cache import CacheContext

async with CacheContext(namespace="sessions") as cache:
    await cache.set("session:abc", {"user_id": "123"}, ttl=3600)
    session = await cache.get("session:abc")
```

### Manual Invalidation

```python
from agent_service.infrastructure.cache import invalidate_cache_key, invalidate_cache_pattern

# Invalidate single key
await invalidate_cache_key("users:123")

# Invalidate pattern
count = await invalidate_cache_pattern("users:*")
```

## Session Operations

### Setup

```python
from agent_service.infrastructure.database.connection import get_session
from agent_service.infrastructure.database.repositories import SessionRepository
from agent_service.infrastructure.database.models.session import Session, SessionStatus
```

### Create Session

```python
async with get_session() as db:
    repo = SessionRepository(db)

    session = Session(
        user_id=user_id,
        agent_id="code_agent",
        title="Debug Python Script",
        status=SessionStatus.ACTIVE,
        context={"language": "python"}
    )
    session = await repo.create(session)
    await db.commit()
```

### Add Messages

```python
await repo.add_message_to_session(
    session_id=session.id,
    message={
        "role": "user",
        "content": "Help me debug this",
        "metadata": {"source": "web"}
    }
)
```

### Update Context

```python
await repo.update_session_context(
    session_id=session.id,
    context={"current_file": "main.py", "line": 42}
)
```

### Query Sessions

```python
# Get user sessions
sessions = await repo.get_user_sessions(user_id, active_only=True)

# Get with messages
session = await repo.get_session_with_messages(session_id)

# Paginated
result = await repo.get_paginated_user_sessions(
    user_id=user_id,
    page=1,
    page_size=10
)

# Search
sessions = await repo.search_sessions(user_id, "python")

# Recent
recent = await repo.get_recent_sessions(user_id, hours=24)

# By agent
agent_sessions = await repo.get_sessions_by_agent("code_agent")
```

### Statistics

```python
stats = await repo.get_session_stats(user_id)
print(f"Total: {stats.total_sessions}")
print(f"Active: {stats.active_sessions}")
print(f"Messages: {stats.total_messages}")
print(f"Avg: {stats.avg_messages_per_session:.1f}")
```

### Cleanup

```python
# Run in scheduled job
cleaned = await repo.cleanup_expired_sessions()
await db.commit()
```

## Redis Manager

### Advanced Operations

```python
from agent_service.infrastructure.cache import get_redis_manager

manager = await get_redis_manager()

# Scan keys
keys = await manager.scan_keys("users:*")

# Multi-get
values = await manager.mget(["key1", "key2", "key3"])

# Multi-set
await manager.mset({"key1": "val1", "key2": "val2"})

# Delete by pattern
deleted = await manager.delete_by_pattern("temp:*")

# Metrics
metrics = manager.get_metrics()
hit_rate = manager.get_hit_rate(namespace="users")
```

## Common Patterns

### Cached Database Query

```python
@cached(ttl=300, key_prefix="users")
async def get_user_profile(user_id: str):
    async with get_session() as db:
        return await db.query_user(user_id)
```

### Update with Cache Invalidation

```python
@cache_invalidate(key_pattern="users:get_user_profile:*")
async def update_user_profile(user_id: str, data: dict):
    async with get_session() as db:
        await db.update_user(user_id, data)
        await db.commit()
```

### Session with Cached Queries

```python
@cached(ttl=60, key_prefix="sessions")
async def get_cached_sessions(user_id: UUID):
    async with get_session() as db:
        repo = SessionRepository(db)
        sessions = await repo.get_user_sessions(user_id)
        return [s.dict() for s in sessions]
```

### Bulk Session Update

```python
async with get_session() as db:
    repo = SessionRepository(db)

    # Get session IDs
    sessions = await repo.get_user_sessions(user_id)
    session_ids = [s.id for s in sessions]

    # Bulk update
    count = await repo.bulk_update_session_status(
        session_ids=session_ids,
        status=SessionStatus.COMPLETED
    )
    await db.commit()
```

## Configuration

```env
# .env file
REDIS_URL=redis://localhost:6379/0
CACHE_DEFAULT_TTL=300
CACHE_KEY_PREFIX=agent_service
SESSION_MAX_MESSAGES=100
SESSION_EXPIRY_HOURS=24
```

## Error Handling

### Cache Failures

```python
# Decorators handle failures automatically
@cached(ttl=300)
async def safe_function():
    # If cache fails, function executes normally
    return await expensive_operation()
```

### Manual Error Handling

```python
try:
    cache = await get_cache()
    await cache.set("key", "value")
except Exception as e:
    logger.error(f"Cache error: {e}")
    # Continue without cache
```

## Performance Tips

1. **Use appropriate TTLs**: Short (60s) for volatile, Long (3600s) for static
2. **Namespace everything**: Avoid key collisions
3. **Batch operations**: Use mget/mset for multiple keys
4. **Paginate queries**: Always use pagination for lists
5. **Monitor metrics**: Track hit rates and adjust strategy
6. **Clean up regularly**: Schedule cleanup jobs for sessions

## Common Issues

### Cache Not Working
```python
# Check Redis connection
manager = await get_redis_manager()
if manager.is_available:
    print("Redis connected")
else:
    print("Using in-memory cache (fallback)")
```

### Session Not Found
```python
# Include deleted sessions if needed
session = await repo.get(session_id, include_deleted=True)
```

### Message Limit Reached
```python
# Check current message count
if session.total_messages >= settings.session_max_messages:
    # Create new session or increase limit in settings
    pass
```

## Monitoring

### Cache Health
```python
manager = await get_redis_manager()
healthy = await manager.health_check()
print(f"Redis healthy: {healthy}")
```

### Cache Performance
```python
metrics = manager.get_metrics()
print(f"Hit rate: {manager.get_hit_rate():.2f}%")
```

### Session Analytics
```python
stats = await repo.get_session_stats(user_id)
print(f"Active sessions: {stats.active_sessions}")
print(f"Total messages: {stats.total_messages}")
```

## Testing

### Mock Cache
```python
from agent_service.infrastructure.cache.cache import InMemoryCache

# Use in-memory cache for tests
cache = InMemoryCache(namespace="test")
```

### Test Session Repository
```python
async with get_session() as db:
    repo = SessionRepository(db)
    session = await repo.create(Session(...))
    # Test operations
    await db.rollback()  # Don't commit in tests
```

## Links

- Full Documentation: `README.md`
- Examples: `USAGE_EXAMPLES.py`
- Implementation Details: `CACHE_SESSION_IMPLEMENTATION.md`
