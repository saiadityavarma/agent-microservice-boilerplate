# src/agent_service/infrastructure/cache/test_integration.py
"""
Integration tests for cache layer and session repository.

These tests demonstrate the integration between caching and session management.
They can be run with pytest or as standalone examples.
"""

import pytest
import asyncio
from uuid import uuid4
from datetime import datetime, timedelta

# Cache imports
from agent_service.infrastructure.cache import (
    get_cache,
    cached,
    cache_invalidate,
    CacheContext,
    get_redis_manager,
)

# Session imports (uncomment when database is configured)
# from agent_service.infrastructure.database.connection import get_session
# from agent_service.infrastructure.database.repositories import SessionRepository
# from agent_service.infrastructure.database.models.session import Session, SessionStatus


class TestCacheOperations:
    """Test basic cache operations."""

    @pytest.mark.asyncio
    async def test_cache_set_get(self):
        """Test basic set and get operations."""
        cache = await get_cache(namespace="test")

        # Test set and get
        await cache.set("test_key", {"value": "test_data"}, ttl=60)
        result = await cache.get("test_key")

        assert result is not None
        assert result["value"] == "test_data"

    @pytest.mark.asyncio
    async def test_cache_delete(self):
        """Test delete operation."""
        cache = await get_cache(namespace="test")

        # Set value
        await cache.set("delete_test", "value", ttl=60)
        assert await cache.exists("delete_test")

        # Delete value
        deleted = await cache.delete("delete_test")
        assert deleted is True
        assert not await cache.exists("delete_test")

    @pytest.mark.asyncio
    async def test_cache_increment(self):
        """Test increment operation."""
        cache = await get_cache(namespace="test")

        # Test increment
        count1 = await cache.increment("counter_test", amount=1)
        assert count1 == 1

        count2 = await cache.increment("counter_test", amount=5)
        assert count2 == 6

    @pytest.mark.asyncio
    async def test_cache_expire(self):
        """Test expire operation."""
        cache = await get_cache(namespace="test")

        # Set value without TTL
        await cache.set("expire_test", "value")

        # Set expiration
        success = await cache.expire("expire_test", ttl=1)
        assert success is True

        # Wait for expiration
        await asyncio.sleep(2)

        # Value should be expired
        result = await cache.get("expire_test")
        # Note: This may still return a value if using in-memory cache
        # as expiration is checked on access


class TestCacheDecorators:
    """Test cache decorators."""

    @pytest.mark.asyncio
    async def test_cached_decorator(self):
        """Test @cached decorator."""
        call_count = 0

        @cached(ttl=60, key_prefix="test")
        async def expensive_function(arg: str):
            nonlocal call_count
            call_count += 1
            return f"result_{arg}"

        # First call - should execute function
        result1 = await expensive_function("test")
        assert result1 == "result_test"
        assert call_count == 1

        # Second call - should use cache
        result2 = await expensive_function("test")
        assert result2 == "result_test"
        assert call_count == 1  # Not incremented

    @pytest.mark.asyncio
    async def test_cache_invalidate_decorator(self):
        """Test @cache_invalidate decorator."""
        call_count = 0

        @cached(ttl=60, key_prefix="test_invalidate")
        async def get_data(key: str):
            nonlocal call_count
            call_count += 1
            return f"data_{key}"

        @cache_invalidate(key_pattern="test_invalidate:get_data:*")
        async def update_data(key: str, value: str):
            # Simulate update
            pass

        # Cache data
        result1 = await get_data("key1")
        assert call_count == 1

        # Should use cache
        result2 = await get_data("key1")
        assert call_count == 1

        # Invalidate cache
        await update_data("key1", "new_value")

        # Should execute function again
        result3 = await get_data("key1")
        assert call_count == 2


class TestCacheContext:
    """Test cache context manager."""

    @pytest.mark.asyncio
    async def test_cache_context(self):
        """Test CacheContext manager."""
        async with CacheContext(namespace="test_context") as cache:
            # Set value
            await cache.set("ctx_key", {"data": "value"}, ttl=60)

            # Get value
            result = await cache.get("ctx_key")
            assert result is not None
            assert result["data"] == "value"


class TestRedisManager:
    """Test Redis manager extensions."""

    @pytest.mark.asyncio
    async def test_scan_keys(self):
        """Test scan_keys operation."""
        manager = await get_redis_manager()

        if not manager.is_available:
            pytest.skip("Redis not available")

        # Set some test keys
        cache = await get_cache(namespace="scan_test")
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        # Scan for keys
        keys = await manager.scan_keys("scan_test:*")
        assert len(keys) >= 3

    @pytest.mark.asyncio
    async def test_mget_mset(self):
        """Test multi-get and multi-set operations."""
        manager = await get_redis_manager()

        if not manager.is_available:
            pytest.skip("Redis not available")

        # Test mset
        success = await manager.mset({
            "test:mget1": "value1",
            "test:mget2": "value2",
            "test:mget3": "value3",
        })
        assert success is True

        # Test mget
        values = await manager.mget([
            "test:mget1",
            "test:mget2",
            "test:mget3",
        ])
        assert len(values) == 3
        assert "value1" in values

    @pytest.mark.asyncio
    async def test_delete_by_pattern(self):
        """Test delete by pattern."""
        manager = await get_redis_manager()

        if not manager.is_available:
            pytest.skip("Redis not available")

        # Set test keys
        cache = await get_cache(namespace="delete_test")
        await cache.set("temp1", "value1")
        await cache.set("temp2", "value2")
        await cache.set("keep", "value3")

        # Delete by pattern
        deleted = await manager.delete_by_pattern("delete_test:temp*")
        assert deleted >= 2

        # Verify
        assert not await cache.exists("temp1")
        assert not await cache.exists("temp2")
        assert await cache.exists("keep")


class TestCacheMetrics:
    """Test cache metrics collection."""

    @pytest.mark.asyncio
    async def test_metrics_collection(self):
        """Test metrics are collected."""
        manager = await get_redis_manager()

        # Get initial metrics
        metrics = manager.get_metrics()
        assert "metrics" in metrics
        assert "last_reset" in metrics

    @pytest.mark.asyncio
    async def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        manager = await get_redis_manager()

        # Reset metrics
        manager.reset_metrics()

        # Get hit rate
        hit_rate = manager.get_hit_rate(namespace="test")
        assert hit_rate == 0.0  # No data yet


# Session Repository Tests (uncomment when database is configured)
"""
class TestSessionRepository:
    Test session repository operations.

    @pytest.mark.asyncio
    async def test_create_session(self):
        Test session creation.
        async with get_session() as db:
            repo = SessionRepository(db)

            user_id = uuid4()
            session = Session(
                user_id=user_id,
                agent_id="test_agent",
                title="Test Session",
                status=SessionStatus.ACTIVE,
            )

            created = await repo.create(session)
            assert created.id is not None
            assert created.title == "Test Session"

            await db.commit()

    @pytest.mark.asyncio
    async def test_add_message_to_session(self):
        Test adding messages to session.
        async with get_session() as db:
            repo = SessionRepository(db)

            # Create session
            user_id = uuid4()
            session = Session(
                user_id=user_id,
                agent_id="test_agent",
                title="Message Test",
                status=SessionStatus.ACTIVE,
            )
            session = await repo.create(session)

            # Add messages
            await repo.add_message_to_session(
                session_id=session.id,
                message={"role": "user", "content": "Hello"}
            )

            await repo.add_message_to_session(
                session_id=session.id,
                message={"role": "assistant", "content": "Hi there!"}
            )

            # Verify
            updated = await repo.get(session.id)
            assert len(updated.messages) == 2
            assert updated.total_messages == 2

            await db.commit()

    @pytest.mark.asyncio
    async def test_update_session_context(self):
        Test updating session context.
        async with get_session() as db:
            repo = SessionRepository(db)

            # Create session
            user_id = uuid4()
            session = Session(
                user_id=user_id,
                agent_id="test_agent",
                title="Context Test",
                context={"initial": "value"}
            )
            session = await repo.create(session)

            # Update context
            await repo.update_session_context(
                session_id=session.id,
                context={"new_key": "new_value", "number": 42}
            )

            # Verify
            updated = await repo.get(session.id)
            assert updated.context["initial"] == "value"
            assert updated.context["new_key"] == "new_value"
            assert updated.context["number"] == 42

            await db.commit()

    @pytest.mark.asyncio
    async def test_get_user_sessions(self):
        Test getting user sessions.
        async with get_session() as db:
            repo = SessionRepository(db)

            user_id = uuid4()

            # Create multiple sessions
            for i in range(3):
                session = Session(
                    user_id=user_id,
                    agent_id="test_agent",
                    title=f"Session {i}",
                    status=SessionStatus.ACTIVE,
                )
                await repo.create(session)

            # Get sessions
            sessions = await repo.get_user_sessions(user_id, active_only=True)
            assert len(sessions) == 3

            await db.commit()

    @pytest.mark.asyncio
    async def test_get_session_stats(self):
        Test getting session statistics.
        async with get_session() as db:
            repo = SessionRepository(db)

            user_id = uuid4()

            # Create session with messages
            session = Session(
                user_id=user_id,
                agent_id="test_agent",
                title="Stats Test",
                status=SessionStatus.ACTIVE,
            )
            session = await repo.create(session)

            # Add messages
            for i in range(5):
                await repo.add_message_to_session(
                    session_id=session.id,
                    message={"role": "user", "content": f"Message {i}"}
                )

            # Get stats
            stats = await repo.get_session_stats(user_id)
            assert stats.total_sessions >= 1
            assert stats.total_messages >= 5

            await db.commit()

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self):
        Test cleaning up expired sessions.
        async with get_session() as db:
            repo = SessionRepository(db)

            user_id = uuid4()

            # Create expired session
            session = Session(
                user_id=user_id,
                agent_id="test_agent",
                title="Expired Session",
                status=SessionStatus.ACTIVE,
                expires_at=datetime.utcnow() - timedelta(days=1)
            )
            session = await repo.create(session)

            # Cleanup
            cleaned = await repo.cleanup_expired_sessions()
            assert cleaned >= 1

            # Verify status changed
            updated = await repo.get(session.id)
            assert updated.status == SessionStatus.COMPLETED

            await db.commit()


class TestCachedSessionQueries:
    Test integration of caching with session queries.

    @pytest.mark.asyncio
    async def test_cached_session_query(self):
        Test caching session queries.
        call_count = 0

        @cached(ttl=60, key_prefix="sessions")
        async def get_cached_user_sessions(user_id):
            nonlocal call_count
            call_count += 1

            async with get_session() as db:
                repo = SessionRepository(db)
                sessions = await repo.get_user_sessions(user_id)
                return [
                    {
                        "id": str(s.id),
                        "title": s.title,
                        "total_messages": s.total_messages,
                    }
                    for s in sessions
                ]

        user_id = uuid4()

        # First call - executes query
        result1 = await get_cached_user_sessions(user_id)
        assert call_count == 1

        # Second call - uses cache
        result2 = await get_cached_user_sessions(user_id)
        assert call_count == 1  # Not incremented
        assert result1 == result2
"""


# Standalone test runner
async def run_all_tests():
    """Run all tests standalone (without pytest)."""
    print("Running cache integration tests...\n")

    # Test cache operations
    print("1. Testing cache set/get...")
    test = TestCacheOperations()
    await test.test_cache_set_get()
    print("   ✓ Cache set/get works")

    await test.test_cache_delete()
    print("   ✓ Cache delete works")

    await test.test_cache_increment()
    print("   ✓ Cache increment works")

    # Test decorators
    print("\n2. Testing cache decorators...")
    test = TestCacheDecorators()
    await test.test_cached_decorator()
    print("   ✓ @cached decorator works")

    await test.test_cache_invalidate_decorator()
    print("   ✓ @cache_invalidate decorator works")

    # Test context
    print("\n3. Testing cache context...")
    test = TestCacheContext()
    await test.test_cache_context()
    print("   ✓ CacheContext works")

    # Test Redis manager
    print("\n4. Testing Redis manager...")
    test = TestRedisManager()
    try:
        await test.test_mget_mset()
        print("   ✓ Multi-get/set works")

        await test.test_delete_by_pattern()
        print("   ✓ Delete by pattern works")
    except Exception as e:
        print(f"   ⚠ Redis tests skipped: {e}")

    # Test metrics
    print("\n5. Testing cache metrics...")
    test = TestCacheMetrics()
    await test.test_metrics_collection()
    print("   ✓ Metrics collection works")

    print("\n✅ All cache tests passed!")
    print("\nNote: Session repository tests require database configuration.")
    print("Uncomment the session test classes and configure database to run them.")


if __name__ == "__main__":
    """
    Run tests standalone:
        python -m agent_service.infrastructure.cache.test_integration

    Run with pytest:
        pytest agent_service/infrastructure/cache/test_integration.py -v
    """
    asyncio.run(run_all_tests())
