# tests/factories/base.py
"""
Base factory classes for Factory Boy integration.

Provides base classes that integrate Factory Boy with SQLModel and async database sessions.
"""

from typing import Any, Optional
from uuid import uuid4

import factory
from factory import alchemy
from sqlalchemy.ext.asyncio import AsyncSession


class BaseFactory(factory.Factory):
    """
    Base factory for all model factories.

    This provides common functionality and configuration for all factories.
    For SQLModel/database models, use AsyncSQLModelFactory instead.

    Usage:
        class UserDataFactory(BaseFactory):
            class Meta:
                model = UserData

            id = factory.LazyFunction(uuid4)
            email = factory.Faker("email")
            username = factory.Faker("user_name")
    """

    class Meta:
        abstract = True

    id = factory.LazyFunction(uuid4)


class AsyncSQLModelFactory(alchemy.SQLAlchemyModelFactory):
    """
    Base factory for SQLModel database models with async session support.

    This factory integrates with async SQLAlchemy sessions and provides
    automatic session management for creating database records.

    Usage:
        class UserFactory(AsyncSQLModelFactory):
            class Meta:
                model = User
                sqlalchemy_session = None  # Will be set by fixture

            email = factory.Faker("email")
            username = factory.Faker("user_name")
            is_active = True

        # In tests:
        async def test_user(db_session):
            user = await UserFactory.create_async(session=db_session)
            assert user.id is not None
    """

    class Meta:
        abstract = True
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    @classmethod
    async def create_async(cls, session: AsyncSession, **kwargs: Any):
        """
        Asynchronously create a model instance and save to database.

        Args:
            session: Async database session to use
            **kwargs: Attributes to override on the model

        Returns:
            Created and committed model instance

        Usage:
            user = await UserFactory.create_async(
                session=db_session,
                email="custom@example.com"
            )
        """
        # Temporarily set session
        original_session = cls._meta.sqlalchemy_session
        cls._meta.sqlalchemy_session = session

        try:
            # Create instance
            instance = cls.build(**kwargs)

            # Add to session and commit
            session.add(instance)
            await session.commit()
            await session.refresh(instance)

            return instance
        finally:
            # Restore original session
            cls._meta.sqlalchemy_session = original_session

    @classmethod
    async def create_batch_async(
        cls,
        session: AsyncSession,
        size: int,
        **kwargs: Any
    ):
        """
        Asynchronously create multiple model instances.

        Args:
            session: Async database session to use
            size: Number of instances to create
            **kwargs: Attributes to override on all models

        Returns:
            List of created model instances

        Usage:
            users = await UserFactory.create_batch_async(
                session=db_session,
                size=5,
                is_active=True
            )
        """
        original_session = cls._meta.sqlalchemy_session
        cls._meta.sqlalchemy_session = session

        try:
            instances = []
            for _ in range(size):
                instance = cls.build(**kwargs)
                session.add(instance)
                instances.append(instance)

            await session.commit()

            # Refresh all instances
            for instance in instances:
                await session.refresh(instance)

            return instances
        finally:
            cls._meta.sqlalchemy_session = original_session

    @classmethod
    def build_async(cls, **kwargs: Any):
        """
        Build a model instance without saving to database.

        This is synchronous but returns an instance that can be used
        with async sessions.

        Args:
            **kwargs: Attributes to override on the model

        Returns:
            Built model instance (not yet saved)

        Usage:
            user = UserFactory.build_async(email="test@example.com")
            db_session.add(user)
            await db_session.commit()
        """
        return cls.build(**kwargs)


class FactoryManager:
    """
    Manages factory session configuration for tests.

    This helper class makes it easier to configure all factories
    with the correct database session in test fixtures.

    Usage in conftest.py:
        @pytest.fixture
        def factory_manager(db_session):
            manager = FactoryManager(db_session)
            manager.configure_factories()
            yield manager
            manager.reset_factories()
    """

    def __init__(self, session: Optional[AsyncSession] = None):
        """
        Initialize factory manager.

        Args:
            session: Async database session to use for all factories
        """
        self.session = session
        self._original_sessions = {}

    def configure_factories(self, *factories):
        """
        Configure multiple factories with the session.

        Args:
            *factories: Factory classes to configure

        Usage:
            manager.configure_factories(UserFactory, PostFactory, CommentFactory)
        """
        for factory_class in factories:
            if hasattr(factory_class._meta, "sqlalchemy_session"):
                self._original_sessions[factory_class] = (
                    factory_class._meta.sqlalchemy_session
                )
                factory_class._meta.sqlalchemy_session = self.session

    def reset_factories(self, *factories):
        """
        Reset factories to their original session configuration.

        Args:
            *factories: Factory classes to reset
        """
        for factory_class in factories:
            if factory_class in self._original_sessions:
                factory_class._meta.sqlalchemy_session = (
                    self._original_sessions[factory_class]
                )

    def __enter__(self):
        """Context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up on context exit."""
        self.reset_factories()


# Example factory for demonstration (can be removed or extended)
class ExampleModelFactory(BaseFactory):
    """
    Example factory demonstrating usage.

    This can be used as a template for creating new factories.
    """

    class Meta:
        model = dict  # Replace with actual model

    id = factory.LazyFunction(uuid4)
    name = factory.Faker("name")
    email = factory.Faker("email")
    created_at = factory.Faker("date_time")
