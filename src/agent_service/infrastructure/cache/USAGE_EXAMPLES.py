# src/agent_service/infrastructure/cache/USAGE_EXAMPLES.py
"""
Usage examples for the cache layer and session repository.

This file demonstrates how to use the cache abstraction, decorators,
and session repository in your application.
"""

from datetime import datetime, timedelta
from uuid import UUID, uuid4

# Example 1: Basic cache usage
async def example_basic_cache():
    """Demonstrate basic cache operations."""
    from agent_service.infrastructure.cache import get_cache

    # Get cache instance (automatically uses Redis or falls back to in-memory)
    cache = await get_cache(namespace="examples")

    # Set a value with TTL
    await cache.set("user:123", {"name": "John", "email": "john@example.com"}, ttl=300)

    # Get the value
    user = await cache.get("user:123")
    print(f"User: {user}")

    # Check if key exists
    exists = await cache.exists("user:123")
    print(f"Key exists: {exists}")

    # Delete the key
    deleted = await cache.delete("user:123")
    print(f"Deleted: {deleted}")

    # Increment counter
    count = await cache.increment("page_views", amount=1)
    print(f"Page views: {count}")


# Example 2: Using cache decorators
async def example_cache_decorators():
    """Demonstrate cache decorators."""
    from agent_service.infrastructure.cache import cached, cache_invalidate

    # Cache function results
    @cached(ttl=300, key_prefix="users")
    async def get_user_by_id(user_id: str):
        """Expensive database query (simulated)."""
        print(f"Fetching user {user_id} from database...")
        # Simulate database query
        return {"id": user_id, "name": "John Doe", "email": "john@example.com"}

    # First call - fetches from database
    user1 = await get_user_by_id("123")
    print(f"First call: {user1}")

    # Second call - returns cached result
    user2 = await get_user_by_id("123")
    print(f"Second call (cached): {user2}")

    # Invalidate cache on mutation
    @cache_invalidate(key_pattern="users:get_user_by_id:*")
    async def update_user(user_id: str, data: dict):
        """Update user and invalidate cache."""
        print(f"Updating user {user_id}...")
        # Update database
        # Cache will be invalidated after successful update

    # Update user - this will invalidate all cached get_user_by_id results
    await update_user("123", {"name": "Jane Doe"})


# Example 3: Using CacheContext
async def example_cache_context():
    """Demonstrate CacheContext for manual cache operations."""
    from agent_service.infrastructure.cache import CacheContext

    async with CacheContext(namespace="sessions") as cache:
        # Set multiple session values
        await cache.set("session:abc", {"user_id": "123", "expires": "2024-12-31"}, ttl=3600)
        await cache.set("session:def", {"user_id": "456", "expires": "2024-12-31"}, ttl=3600)

        # Get session
        session = await cache.get("session:abc")
        print(f"Session: {session}")


# Example 4: SessionRepository usage
async def example_session_repository():
    """Demonstrate SessionRepository operations."""
    from agent_service.infrastructure.database.connection import get_session
    from agent_service.infrastructure.database.repositories import SessionRepository
    from agent_service.infrastructure.database.models.session import Session, SessionStatus

    async with get_session() as db:
        repo = SessionRepository(db)

        # Create a new session
        user_id = uuid4()
        session = Session(
            user_id=user_id,
            agent_id="code_agent",
            title="Debug Python Script",
            status=SessionStatus.ACTIVE,
            context={"language": "python", "file": "main.py"}
        )
        session = await repo.create(session)
        print(f"Created session: {session.id}")

        # Add messages to session
        await repo.add_message_to_session(
            session_id=session.id,
            message={
                "role": "user",
                "content": "Help me debug this code",
                "metadata": {"source": "web"}
            }
        )

        await repo.add_message_to_session(
            session_id=session.id,
            message={
                "role": "assistant",
                "content": "I'll help you debug that. What's the error?",
                "metadata": {"model": "gpt-4"}
            }
        )

        # Update session context
        await repo.update_session_context(
            session_id=session.id,
            context={"current_line": 42, "error_type": "TypeError"}
        )

        # Get session with messages
        session_with_messages = await repo.get_session_with_messages(session.id)
        print(f"Session has {len(session_with_messages.messages)} messages")

        # Get user's sessions
        user_sessions = await repo.get_user_sessions(user_id, active_only=True)
        print(f"User has {len(user_sessions)} active sessions")

        # Get session statistics
        stats = await repo.get_session_stats(user_id)
        print(f"Total sessions: {stats.total_sessions}")
        print(f"Active sessions: {stats.active_sessions}")
        print(f"Total messages: {stats.total_messages}")
        print(f"Avg messages/session: {stats.avg_messages_per_session:.1f}")

        await db.commit()


# Example 5: Paginated session queries
async def example_paginated_sessions():
    """Demonstrate paginated session queries."""
    from agent_service.infrastructure.database.connection import get_session
    from agent_service.infrastructure.database.repositories import SessionRepository
    from agent_service.infrastructure.database.models.session import SessionStatus

    async with get_session() as db:
        repo = SessionRepository(db)
        user_id = uuid4()  # Replace with actual user ID

        # Get first page of sessions
        result = await repo.get_paginated_user_sessions(
            user_id=user_id,
            page=1,
            page_size=10,
            status=SessionStatus.ACTIVE
        )

        print(f"Page {result.page} of {result.total_pages}")
        print(f"Total sessions: {result.total}")
        print(f"Has next page: {result.has_next}")
        print(f"Has previous page: {result.has_prev}")

        for session in result.items:
            print(f"- {session.title} ({session.total_messages} messages)")


# Example 6: Scheduled session cleanup
async def example_cleanup_expired_sessions():
    """Demonstrate scheduled cleanup of expired sessions."""
    from agent_service.infrastructure.database.connection import get_session
    from agent_service.infrastructure.database.repositories import SessionRepository

    async with get_session() as db:
        repo = SessionRepository(db)

        # Clean up expired sessions
        # This should be called periodically (e.g., via cron job or scheduler)
        cleaned = await repo.cleanup_expired_sessions()
        print(f"Cleaned up {cleaned} expired sessions")

        await db.commit()


# Example 7: Cache with Redis metrics
async def example_cache_metrics():
    """Demonstrate cache metrics collection."""
    from agent_service.infrastructure.cache import get_redis_manager

    manager = await get_redis_manager()

    if manager.is_available:
        # Get cache metrics
        metrics = manager.get_metrics()
        print(f"Cache metrics: {metrics}")

        # Get hit rate for specific namespace
        hit_rate = manager.get_hit_rate(namespace="users")
        print(f"Cache hit rate for 'users' namespace: {hit_rate:.2f}%")

        # Reset metrics
        manager.reset_metrics()


# Example 8: Advanced cache operations
async def example_advanced_cache():
    """Demonstrate advanced cache operations."""
    from agent_service.infrastructure.cache import get_redis_manager

    manager = await get_redis_manager()

    if manager.is_available:
        # Scan for keys matching pattern
        keys = await manager.scan_keys("users:*")
        print(f"Found {len(keys)} user keys")

        # Multi-get
        values = await manager.mget(["key1", "key2", "key3"])
        print(f"Retrieved {len(values)} values")

        # Multi-set
        await manager.mset({
            "temp:key1": "value1",
            "temp:key2": "value2",
            "temp:key3": "value3"
        })

        # Delete by pattern
        deleted = await manager.delete_by_pattern("temp:*")
        print(f"Deleted {deleted} temporary keys")


# Example 9: Session search
async def example_session_search():
    """Demonstrate session search functionality."""
    from agent_service.infrastructure.database.connection import get_session
    from agent_service.infrastructure.database.repositories import SessionRepository

    async with get_session() as db:
        repo = SessionRepository(db)
        user_id = uuid4()  # Replace with actual user ID

        # Search sessions by title
        sessions = await repo.search_sessions(
            user_id=user_id,
            search_term="python",
            limit=10
        )

        print(f"Found {len(sessions)} sessions matching 'python'")
        for session in sessions:
            print(f"- {session.title}")


# Example 10: Bulk session operations
async def example_bulk_session_operations():
    """Demonstrate bulk session operations."""
    from agent_service.infrastructure.database.connection import get_session
    from agent_service.infrastructure.database.repositories import SessionRepository
    from agent_service.infrastructure.database.models.session import SessionStatus

    async with get_session() as db:
        repo = SessionRepository(db)

        # Create multiple sessions
        sessions_data = [
            {
                "user_id": uuid4(),
                "agent_id": "code_agent",
                "title": f"Session {i}",
                "status": SessionStatus.ACTIVE
            }
            for i in range(5)
        ]
        sessions = await repo.create_many(sessions_data)
        print(f"Created {len(sessions)} sessions")

        # Bulk update status
        session_ids = [s.id for s in sessions]
        updated = await repo.bulk_update_session_status(
            session_ids=session_ids,
            status=SessionStatus.COMPLETED
        )
        print(f"Updated {updated} sessions to COMPLETED")

        await db.commit()


# Example 11: Integration with caching
async def example_cached_session_queries():
    """Demonstrate caching session repository queries."""
    from agent_service.infrastructure.database.connection import get_session
    from agent_service.infrastructure.database.repositories import SessionRepository
    from agent_service.infrastructure.cache import cached, cache_invalidate
    from uuid import UUID

    # Cache expensive session queries
    @cached(ttl=60, key_prefix="sessions")
    async def get_cached_user_sessions(user_id: UUID):
        """Get user sessions with caching."""
        async with get_session() as db:
            repo = SessionRepository(db)
            sessions = await repo.get_user_sessions(user_id, active_only=True)
            # Convert to dict for serialization
            return [
                {
                    "id": str(s.id),
                    "title": s.title,
                    "total_messages": s.total_messages,
                    "last_activity_at": s.last_activity_at.isoformat()
                }
                for s in sessions
            ]

    # Invalidate cache when session is updated
    @cache_invalidate(key_pattern="sessions:get_cached_user_sessions:*")
    async def invalidate_user_sessions_cache():
        """Invalidate all cached user sessions."""
        pass

    # Usage
    user_id = uuid4()
    sessions = await get_cached_user_sessions(user_id)
    print(f"Retrieved {len(sessions)} sessions (cached)")

    # After updating sessions
    await invalidate_user_sessions_cache()


# Example 12: Using InMemoryCache directly
async def example_in_memory_cache():
    """Demonstrate in-memory cache usage."""
    from agent_service.infrastructure.cache.cache import InMemoryCache

    # Create in-memory cache with custom size
    cache = InMemoryCache(max_size=1000, namespace="temp")

    # Use like any other cache
    await cache.set("key1", {"data": "value1"}, ttl=60)
    value = await cache.get("key1")
    print(f"Cached value: {value}")

    # Check cache size
    size = cache.size()
    print(f"Cache size: {size}")

    # Clear cache
    cache.clear()


if __name__ == "__main__":
    """
    To run these examples:

    python -m agent_service.infrastructure.cache.USAGE_EXAMPLES
    """
    import asyncio

    async def main():
        print("=== Cache Usage Examples ===\n")

        print("1. Basic cache operations:")
        await example_basic_cache()

        print("\n2. Cache decorators:")
        await example_cache_decorators()

        print("\n3. Cache context:")
        await example_cache_context()

        # Session examples require database setup
        # Uncomment when database is configured

        # print("\n4. Session repository:")
        # await example_session_repository()

        # print("\n5. Paginated sessions:")
        # await example_paginated_sessions()

        # print("\n6. Cleanup expired sessions:")
        # await example_cleanup_expired_sessions()

        print("\n7. Cache metrics:")
        await example_cache_metrics()

        print("\n8. Advanced cache operations:")
        await example_advanced_cache()

        # print("\n9. Session search:")
        # await example_session_search()

        # print("\n10. Bulk session operations:")
        # await example_bulk_session_operations()

        # print("\n11. Cached session queries:")
        # await example_cached_session_queries()

        print("\n12. In-memory cache:")
        await example_in_memory_cache()

    asyncio.run(main())
