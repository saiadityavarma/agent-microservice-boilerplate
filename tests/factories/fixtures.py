# tests/factories/fixtures.py
"""
Factory fixtures for pytest integration.

This module provides fixtures that make it easy to use factories in tests.
It's automatically loaded via pytest_plugins in conftest.py.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.base import FactoryManager


@pytest.fixture
def factory_manager(db_session: AsyncSession):
    """
    Factory manager fixture for configuring factories with test database session.

    This fixture can be used to configure multiple factories at once.

    Usage:
        def test_with_factories(factory_manager):
            factory_manager.configure_factories(UserFactory, PostFactory)
            # Now factories will use the test database session
    """
    manager = FactoryManager(db_session)
    yield manager
    # Cleanup happens automatically


@pytest.fixture
async def factory_session(db_session: AsyncSession):
    """
    Direct access to database session for factory usage.

    This is a convenience fixture for using with create_async methods.

    Usage:
        async def test_create_user(factory_session):
            user = await UserFactory.create_async(
                session=factory_session,
                email="test@example.com"
            )
    """
    return db_session
