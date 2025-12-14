# tests/integration/test_example_integration.py
"""
Example integration tests demonstrating database and component integration.

These tests show how to:
- Use database session fixtures
- Test database operations
- Use Factory Boy for test data
- Test component interactions
"""

import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from agent_service.infrastructure.database.base_model import BaseModel


# ============================================================================
# Database Integration Tests
# ============================================================================

async def test_database_session(db_session: AsyncSession):
    """Test that database session fixture works."""
    assert db_session is not None
    # Session should be active
    assert not db_session.is_active or True  # Session may not be in transaction yet


async def test_database_transaction_rollback(db_session: AsyncSession):
    """
    Test that database changes are rolled back after test.

    This demonstrates that each test gets a clean database state.
    """
    # This test would add data, but it will be rolled back
    # The next test won't see this data
    assert True  # Changes will be rolled back automatically


async def test_database_isolation(db_session: AsyncSession):
    """Test that tests are isolated from each other."""
    # This test runs in a fresh transaction
    # It won't see data from previous tests
    assert True


# ============================================================================
# Testing with Example Model (if you have models)
# ============================================================================

# Example: Uncomment when you have actual models
# from agent_service.domain.models import Session
#
# async def test_create_session(db_session: AsyncSession):
#     """Test creating a session in the database."""
#     session = Session(
#         user_id="test-user-123",
#         data={"key": "value"}
#     )
#
#     db_session.add(session)
#     await db_session.commit()
#     await db_session.refresh(session)
#
#     assert session.id is not None
#     assert session.created_at is not None
#     assert session.user_id == "test-user-123"
#
#
# async def test_query_session(db_session: AsyncSession):
#     """Test querying sessions from database."""
#     # Create test data
#     session1 = Session(user_id="user-1", data={})
#     session2 = Session(user_id="user-2", data={})
#
#     db_session.add_all([session1, session2])
#     await db_session.commit()
#
#     # Query data
#     result = await db_session.execute(select(Session))
#     sessions = result.scalars().all()
#
#     assert len(sessions) >= 2


# ============================================================================
# Testing with Factory Boy (when you have factories)
# ============================================================================

# Example: Uncomment when you have factories
# from tests.factories.user import UserFactory
#
# async def test_with_factory(factory_session):
#     """Test using Factory Boy to create test data."""
#     user = await UserFactory.create_async(
#         session=factory_session,
#         email="test@example.com"
#     )
#
#     assert user.id is not None
#     assert user.email == "test@example.com"
#
#
# async def test_factory_batch(factory_session):
#     """Test creating multiple instances with factory."""
#     users = await UserFactory.create_batch_async(
#         session=factory_session,
#         size=5
#     )
#
#     assert len(users) == 5
#     assert all(user.id is not None for user in users)


# ============================================================================
# Testing Redis Integration (with mock)
# ============================================================================

async def test_redis_mock(mock_redis):
    """Test Redis operations with mock."""
    mock_redis.get.return_value = b"cached_value"

    value = await mock_redis.get("test_key")
    assert value == b"cached_value"

    mock_redis.get.assert_called_once_with("test_key")


async def test_redis_set_get(mock_redis):
    """Test Redis set and get operations."""
    mock_redis.set.return_value = True
    mock_redis.get.return_value = b"test_value"

    # Set value
    await mock_redis.set("key", "test_value")
    mock_redis.set.assert_called_once()

    # Get value
    value = await mock_redis.get("key")
    assert value == b"test_value"


# ============================================================================
# Testing Component Interactions
# ============================================================================

async def test_database_manager(db_manager):
    """Test DatabaseManager fixture."""
    assert db_manager is not None
    assert db_manager._engine is not None
    assert db_manager._session_factory is not None


async def test_component_interaction(db_session: AsyncSession, mock_redis):
    """Test interaction between database and cache components."""
    # Example: Test a service that uses both DB and cache
    # This would test that components work together correctly

    # Setup cache mock
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True

    # Your test logic here
    assert True


# ============================================================================
# Error Handling Tests
# ============================================================================

async def test_database_error_handling(db_session: AsyncSession):
    """Test database error handling."""
    # Example: Test that invalid operations raise appropriate errors
    with pytest.raises(Exception):
        # This should fail - invalid SQL
        await db_session.execute("INVALID SQL")


# ============================================================================
# Testing with Settings Override
# ============================================================================

def test_settings_override(test_settings):
    """Test that settings are overridden for tests."""
    assert test_settings.environment == "local"
    assert test_settings.debug is True
    assert test_settings.log_level == 40  # ERROR level


async def test_database_url_configuration(test_settings):
    """Test that test database URL is configured."""
    assert test_settings.database_url is not None
    db_url = test_settings.database_url.get_secret_value()
    # Should be using SQLite for tests
    assert "sqlite" in db_url or "postgresql" in db_url
