# Redis Cache Layer and Session Storage

This module provides a comprehensive caching solution with Redis and in-memory fallback, along with specialized session management for agent conversations.

## Features

### Cache Layer
- **Abstract cache interface** (`ICache`) for implementation flexibility
- **Redis cache** implementation with automatic serialization
- **In-memory cache** fallback with LRU eviction
- **Namespace support** for key isolation
- **Cache decorators** for easy function result memoization
- **Cache invalidation** patterns for mutation operations
- **Metrics collection** for cache performance monitoring

### Session Storage
- **SessionRepository** with specialized methods for conversation management
- **Message history** with automatic tracking
- **Session context** and metadata management
- **Pagination** support for session queries
- **Session analytics** and statistics
- **Automatic cleanup** of expired sessions
- **Search** capabilities by title and content

## Installation

Ensure you have the required dependencies:

```bash
pip install redis asyncio sqlalchemy
```

## Configuration

Add the following settings to your `.env` file:

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

## Quick Start

### Basic Cache Usage

```python
from agent_service.infrastructure.cache import get_cache

# Get cache instance
cache = await get_cache(namespace="users")

# Set value with TTL
await cache.set("user:123", {"name": "John"}, ttl=300)

# Get value
user = await cache.get("user:123")

# Delete value
await cache.delete("user:123")
```

### Using Cache Decorators

```python
from agent_service.infrastructure.cache import cached, cache_invalidate

# Cache function results
@cached(ttl=300, key_prefix="users")
async def get_user(user_id: str):
    # Expensive operation
    return await db.query_user(user_id)

# Invalidate cache on mutation
@cache_invalidate(key_pattern="users:get_user:*")
async def update_user(user_id: str, data: dict):
    await db.update_user(user_id, data)
```

### Session Repository

```python
from agent_service.infrastructure.database.repositories import SessionRepository
from agent_service.infrastructure.database.models.session import Session, SessionStatus

async with get_session() as db:
    repo = SessionRepository(db)

    # Create session
    session = Session(
        user_id=user_id,
        agent_id="code_agent",
        title="Debug Python Script",
        status=SessionStatus.ACTIVE
    )
    session = await repo.create(session)

    # Add message
    await repo.add_message_to_session(
        session_id=session.id,
        message={
            "role": "user",
            "content": "Help me debug this code"
        }
    )

    # Get user sessions
    sessions = await repo.get_user_sessions(user_id)

    # Get statistics
    stats = await repo.get_session_stats(user_id)
    print(f"Total messages: {stats.total_messages}")
```

## API Reference

### Cache Interface (`ICache`)

All cache implementations support the following methods:

#### `get(key: str) -> T | None`
Get value from cache.

```python
value = await cache.get("my_key")
```

#### `set(key: str, value: T, ttl: int | None = None) -> bool`
Set value in cache with optional TTL.

```python
await cache.set("my_key", {"data": "value"}, ttl=300)
```

#### `delete(key: str) -> bool`
Delete key from cache.

```python
deleted = await cache.delete("my_key")
```

#### `exists(key: str) -> bool`
Check if key exists.

```python
exists = await cache.exists("my_key")
```

#### `increment(key: str, amount: int = 1) -> int`
Increment numeric value.

```python
count = await cache.increment("counter", amount=1)
```

#### `expire(key: str, ttl: int) -> bool`
Set expiration on existing key.

```python
await cache.expire("my_key", ttl=60)
```

### Cache Decorators

#### `@cached(ttl=None, key_prefix="", namespace="", include_args=True, cache_none=False)`

Cache async function results.

**Parameters:**
- `ttl`: Time to live in seconds (None = use default)
- `key_prefix`: Prefix for cache keys
- `namespace`: Cache namespace
- `include_args`: Include function arguments in cache key
- `cache_none`: Whether to cache None results

**Example:**
```python
@cached(ttl=300, key_prefix="users")
async def get_user(user_id: str):
    return await fetch_user(user_id)
```

#### `@cache_invalidate(key_pattern="", namespace="")`

Invalidate cache entries after function execution.

**Parameters:**
- `key_pattern`: Pattern for keys to invalidate (supports wildcards)
- `namespace`: Cache namespace

**Example:**
```python
@cache_invalidate(key_pattern="users:*")
async def update_user(user_id: str, data: dict):
    await save_user(user_id, data)
```

### SessionRepository Methods

#### `get_user_sessions(user_id: UUID, active_only: bool = True, limit: int = 50)`
Get all sessions for a user.

```python
sessions = await repo.get_user_sessions(user_id, active_only=True)
```

#### `get_session_with_messages(session_id: UUID)`
Get session by ID with all messages loaded.

```python
session = await repo.get_session_with_messages(session_id)
print(f"Messages: {len(session.messages)}")
```

#### `add_message_to_session(session_id: UUID, message: dict)`
Add a message to a session.

```python
await repo.add_message_to_session(
    session_id=session.id,
    message={
        "role": "user",
        "content": "Hello!",
        "metadata": {"source": "web"}
    }
)
```

#### `update_session_context(session_id: UUID, context: dict)`
Update session context variables.

```python
await repo.update_session_context(
    session_id=session.id,
    context={"language": "python", "mode": "debug"}
)
```

#### `cleanup_expired_sessions() -> int`
Mark expired sessions as completed.

```python
# Run periodically (e.g., via cron)
cleaned = await repo.cleanup_expired_sessions()
```

#### `get_session_stats(user_id: UUID) -> SessionStats`
Get session statistics for a user.

```python
stats = await repo.get_session_stats(user_id)
print(f"Total sessions: {stats.total_sessions}")
print(f"Active sessions: {stats.active_sessions}")
print(f"Total messages: {stats.total_messages}")
print(f"Hit rate: {stats.avg_messages_per_session:.1f}")
```

#### `get_paginated_user_sessions(user_id: UUID, page: int, page_size: int)`
Get paginated sessions with metadata.

```python
result = await repo.get_paginated_user_sessions(
    user_id=user_id,
    page=1,
    page_size=10
)
print(f"Page {result.page} of {result.total_pages}")
```

#### `search_sessions(user_id: UUID, search_term: str, limit: int = 20)`
Search user's sessions by title.

```python
sessions = await repo.search_sessions(user_id, "python")
```

#### `bulk_update_session_status(session_ids: List[UUID], status: str) -> int`
Update status for multiple sessions.

```python
count = await repo.bulk_update_session_status(
    session_ids=[id1, id2, id3],
    status=SessionStatus.COMPLETED
)
```

### Redis Manager Extensions

#### `scan_keys(pattern: str, count: int = 100) -> List[str]`
Scan for keys matching a pattern.

```python
manager = await get_redis_manager()
keys = await manager.scan_keys("users:*")
```

#### `mget(keys: List[str]) -> List[Optional[str]]`
Get multiple values at once.

```python
values = await manager.mget(["key1", "key2", "key3"])
```

#### `mset(mapping: Dict[str, str]) -> bool`
Set multiple key-value pairs at once.

```python
await manager.mset({"key1": "value1", "key2": "value2"})
```

#### `delete_by_pattern(pattern: str) -> int`
Delete all keys matching a pattern.

```python
deleted = await manager.delete_by_pattern("temp:*")
```

#### `get_metrics() -> Dict[str, Any]`
Get cache performance metrics.

```python
metrics = manager.get_metrics()
print(f"Hit rate: {metrics['hit_rate']}%")
```

## Cache Strategies

### Time-Based Expiration
Set TTL on cache entries to automatically expire them:

```python
# Cache for 5 minutes
@cached(ttl=300)
async def get_data():
    return await fetch_data()
```

### Namespace Isolation
Use namespaces to isolate cache keys by domain:

```python
user_cache = await get_cache(namespace="users")
session_cache = await get_cache(namespace="sessions")
```

### Pattern-Based Invalidation
Invalidate related cache entries using patterns:

```python
@cache_invalidate(key_pattern="users:get_user:*")
async def update_user_profile(user_id: str):
    # All cached user queries will be invalidated
    pass
```

### Selective Caching
Choose what to cache based on business logic:

```python
@cached(ttl=300, cache_none=False)  # Don't cache None results
async def get_optional_data(key: str):
    return await fetch_data_or_none(key)
```

## Best Practices

### 1. Use Appropriate TTLs
- **Short TTL (30-60s)**: Frequently changing data
- **Medium TTL (5-15m)**: Semi-static data
- **Long TTL (1h+)**: Rarely changing data

### 2. Namespace Your Keys
Always use namespaces to avoid key collisions:

```python
cache = await get_cache(namespace="users")
```

### 3. Handle Cache Misses Gracefully
Cache operations can fail - always have fallback logic:

```python
@cached(ttl=300)
async def get_user(user_id: str):
    # Cache decorator handles failures automatically
    # Function executes normally on cache miss
    return await db.query_user(user_id)
```

### 4. Invalidate on Mutations
Always invalidate cache when data changes:

```python
@cache_invalidate(key_pattern="users:*")
async def update_user(user_id: str, data: dict):
    await db.update_user(user_id, data)
```

### 5. Monitor Cache Performance
Use metrics to optimize cache strategy:

```python
manager = await get_redis_manager()
hit_rate = manager.get_hit_rate(namespace="users")
if hit_rate < 50:
    # Consider increasing TTL or caching more data
    pass
```

### 6. Clean Up Expired Sessions
Run cleanup regularly to maintain database health:

```python
# In a scheduled task (cron, celery, etc.)
async def cleanup_task():
    async with get_session() as db:
        repo = SessionRepository(db)
        await repo.cleanup_expired_sessions()
        await db.commit()
```

## Monitoring and Debugging

### Cache Metrics
```python
manager = await get_redis_manager()
metrics = manager.get_metrics()
print(f"Hits: {metrics['metrics']['default:hits']}")
print(f"Misses: {metrics['metrics']['default:misses']}")
print(f"Hit rate: {manager.get_hit_rate():.2f}%")
```

### Session Analytics
```python
stats = await repo.get_session_stats(user_id)
print(f"Total sessions: {stats.total_sessions}")
print(f"Active sessions: {stats.active_sessions}")
print(f"Avg messages/session: {stats.avg_messages_per_session}")
```

## Troubleshooting

### Redis Connection Issues
If Redis is unavailable, the system automatically falls back to in-memory cache:

```python
# This works even if Redis is down
cache = await get_cache()
await cache.set("key", "value")
```

### Session Message Limit
If a session reaches max messages (default: 100), a warning is logged but messages are still added. Configure via:

```env
SESSION_MAX_MESSAGES=200
```

### Cache Serialization Errors
Complex objects may fail to serialize. Use simple types or implement custom serialization:

```python
# Good: Simple types
await cache.set("key", {"name": "John", "age": 30})

# Bad: Complex objects
# await cache.set("key", some_complex_object)

# Solution: Serialize manually
await cache.set("key", some_complex_object.to_dict())
```

## Performance Considerations

### Redis vs In-Memory
- **Redis**: Distributed, persistent, shared across processes
- **In-Memory**: Fast, local, lost on restart

### Batch Operations
Use batch operations for efficiency:

```python
# Instead of multiple get calls
values = await manager.mget(["key1", "key2", "key3"])

# Instead of multiple set calls
await manager.mset({"key1": "value1", "key2": "value2"})
```

### Pagination
Always use pagination for large datasets:

```python
result = await repo.get_paginated_user_sessions(
    user_id=user_id,
    page=1,
    page_size=20
)
```

## Examples

See `USAGE_EXAMPLES.py` for comprehensive examples of all features.

## License

Part of the Agent Service codebase.
