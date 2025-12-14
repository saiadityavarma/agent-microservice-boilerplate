"""
Tests for enhanced BaseRepository features.

This file tests all the advanced features:
1. Soft delete with hard delete
2. Pagination
3. Sorting
4. Advanced filtering
5. Bulk operations
6. Transaction support
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_service.infrastructure.database.repositories.base import BaseRepository, PaginatedResult, transactional
from agent_service.infrastructure.database.models.user import User, AuthProvider


class TestUserRepository(BaseRepository[User]):
    """Test repository for User model."""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session, enable_query_logging=True)


@pytest.fixture
async def user_repo(db_session: AsyncSession):
    """Create user repository for testing."""
    return TestUserRepository(db_session)


@pytest.fixture
async def sample_users(user_repo: TestUserRepository):
    """Create sample users for testing."""
    users_data = [
        {
            "email": f"user{i}@example.com",
            "name": f"User {i}",
            "provider": AuthProvider.LOCAL,
            "provider_user_id": f"user{i}",
            "roles": ["user"],
            "is_active": i % 2 == 0,  # Every other user is active
        }
        for i in range(1, 11)
    ]

    users = await user_repo.create_many(users_data)
    await user_repo.session.commit()
    return users


class TestSoftDelete:
    """Test soft delete functionality."""

    async def test_soft_delete_sets_deleted_at(self, user_repo, sample_users):
        """Test that delete() sets deleted_at timestamp."""
        user = sample_users[0]

        # Soft delete
        deleted = await user_repo.delete(user.id)
        assert deleted is True

        # User is marked as deleted
        await user_repo.session.refresh(user)
        assert user.deleted_at is not None

    async def test_get_excludes_soft_deleted(self, user_repo, sample_users):
        """Test that get() excludes soft-deleted records by default."""
        user = sample_users[0]

        # Soft delete
        await user_repo.delete(user.id)

        # Get should return None
        result = await user_repo.get(user.id)
        assert result is None

        # Get with include_deleted=True should return user
        result = await user_repo.get(user.id, include_deleted=True)
        assert result is not None
        assert result.id == user.id

    async def test_get_many_excludes_soft_deleted(self, user_repo, sample_users):
        """Test that get_many() excludes soft-deleted records by default."""
        # Soft delete first user
        await user_repo.delete(sample_users[0].id)

        # Get many should exclude deleted user
        users = await user_repo.get_many()
        assert len(users) == 9

        # Get many with include_deleted=True
        users = await user_repo.get_many(include_deleted=True)
        assert len(users) == 10

    async def test_hard_delete_permanent(self, user_repo, sample_users):
        """Test that hard_delete() permanently removes record."""
        user = sample_users[0]

        # Hard delete
        deleted = await user_repo.hard_delete(user.id)
        assert deleted is True

        # User is gone even with include_deleted=True
        result = await user_repo.get(user.id, include_deleted=True)
        assert result is None

    async def test_hard_delete_soft_deleted_record(self, user_repo, sample_users):
        """Test that hard_delete() works on soft-deleted records."""
        user = sample_users[0]

        # Soft delete first
        await user_repo.delete(user.id)

        # Then hard delete
        deleted = await user_repo.hard_delete(user.id)
        assert deleted is True

        # User is gone
        result = await user_repo.get(user.id, include_deleted=True)
        assert result is None


class TestPagination:
    """Test pagination functionality."""

    async def test_paginate_returns_correct_structure(self, user_repo, sample_users):
        """Test that paginate() returns PaginatedResult with correct fields."""
        query = select(User)
        result = await user_repo.paginate(query, page=1, page_size=5)

        assert isinstance(result, PaginatedResult)
        assert len(result.items) == 5
        assert result.total == 10
        assert result.page == 1
        assert result.page_size == 5
        assert result.total_pages == 2
        assert result.has_next is True
        assert result.has_prev is False

    async def test_paginate_second_page(self, user_repo, sample_users):
        """Test pagination on second page."""
        query = select(User)
        result = await user_repo.paginate(query, page=2, page_size=5)

        assert len(result.items) == 5
        assert result.page == 2
        assert result.has_next is False
        assert result.has_prev is True

    async def test_paginate_last_page_partial(self, user_repo, sample_users):
        """Test pagination when last page is partial."""
        query = select(User)
        result = await user_repo.paginate(query, page=2, page_size=7)

        assert len(result.items) == 3
        assert result.total_pages == 2
        assert result.has_next is False

    async def test_paginate_with_filters(self, user_repo, sample_users):
        """Test pagination with filtered query."""
        query = select(User).where(User.is_active == True)
        result = await user_repo.paginate(query, page=1, page_size=3)

        # Only 5 active users (even numbers)
        assert result.total == 5
        assert len(result.items) == 3


class TestSorting:
    """Test sorting functionality."""

    async def test_sort_by_created_at_desc(self, user_repo, sample_users):
        """Test sorting by created_at descending (default)."""
        query = select(User)
        query = user_repo.apply_sorting(query, "created_at", "desc")

        result = await user_repo.session.execute(query)
        users = result.scalars().all()

        # Check descending order
        for i in range(len(users) - 1):
            assert users[i].created_at >= users[i + 1].created_at

    async def test_sort_by_email_asc(self, user_repo, sample_users):
        """Test sorting by email ascending."""
        query = select(User)
        query = user_repo.apply_sorting(query, "email", "asc")

        result = await user_repo.session.execute(query)
        users = result.scalars().all()

        # Check ascending order
        for i in range(len(users) - 1):
            assert users[i].email <= users[i + 1].email

    async def test_sort_by_name_desc(self, user_repo, sample_users):
        """Test sorting by name descending."""
        query = select(User)
        query = user_repo.apply_sorting(query, "name", "desc")

        result = await user_repo.session.execute(query)
        users = result.scalars().all()

        # Check descending order
        for i in range(len(users) - 1):
            assert users[i].name >= users[i + 1].name

    async def test_sort_invalid_field_fallback(self, user_repo, sample_users):
        """Test that invalid field falls back to created_at."""
        query = select(User)
        query = user_repo.apply_sorting(query, "invalid_field", "desc")

        # Should not raise error, falls back to created_at
        result = await user_repo.session.execute(query)
        users = result.scalars().all()
        assert len(users) == 10


class TestFiltering:
    """Test advanced filtering functionality."""

    async def test_filter_eq(self, user_repo, sample_users):
        """Test equality filter."""
        query = select(User)
        query = user_repo.apply_filters(query, {"is_active__eq": True})

        result = await user_repo.session.execute(query)
        users = result.scalars().all()

        assert all(user.is_active for user in users)
        assert len(users) == 5

    async def test_filter_ne(self, user_repo, sample_users):
        """Test not equal filter."""
        query = select(User)
        query = user_repo.apply_filters(query, {"provider__ne": AuthProvider.AZURE_AD})

        result = await user_repo.session.execute(query)
        users = result.scalars().all()

        assert all(user.provider != AuthProvider.AZURE_AD for user in users)

    async def test_filter_ilike(self, user_repo, sample_users):
        """Test case-insensitive LIKE filter."""
        query = select(User)
        query = user_repo.apply_filters(query, {"email__ilike": "%example.com"})

        result = await user_repo.session.execute(query)
        users = result.scalars().all()

        assert all("example.com" in user.email for user in users)

    async def test_filter_in(self, user_repo, sample_users):
        """Test IN clause filter."""
        emails = ["user1@example.com", "user2@example.com", "user3@example.com"]
        query = select(User)
        query = user_repo.apply_filters(query, {"email__in": emails})

        result = await user_repo.session.execute(query)
        users = result.scalars().all()

        assert len(users) == 3
        assert all(user.email in emails for user in users)

    async def test_filter_is_null(self, user_repo, sample_users):
        """Test IS NULL filter."""
        query = select(User)
        query = user_repo.apply_filters(query, {"deleted_at__is_null": True})

        result = await user_repo.session.execute(query)
        users = result.scalars().all()

        assert all(user.deleted_at is None for user in users)

    async def test_filter_is_not_null(self, user_repo, sample_users):
        """Test IS NOT NULL filter."""
        # Soft delete one user
        await user_repo.delete(sample_users[0].id)
        await user_repo.session.commit()

        query = select(User)
        query = user_repo.apply_filters(query, {"deleted_at__is_not_null": True})

        result = await user_repo.session.execute(query)
        users = result.scalars().all()

        assert len(users) == 1
        assert all(user.deleted_at is not None for user in users)

    async def test_filter_combined(self, user_repo, sample_users):
        """Test multiple filters combined."""
        query = select(User)
        query = user_repo.apply_filters(query, {
            "is_active__eq": True,
            "email__ilike": "%example.com",
            "provider__eq": AuthProvider.LOCAL,
        })

        result = await user_repo.session.execute(query)
        users = result.scalars().all()

        assert all(
            user.is_active and
            "example.com" in user.email and
            user.provider == AuthProvider.LOCAL
            for user in users
        )


class TestBulkOperations:
    """Test bulk operation functionality."""

    async def test_create_many(self, user_repo):
        """Test bulk create."""
        users_data = [
            {
                "email": f"bulk{i}@example.com",
                "name": f"Bulk User {i}",
                "provider": AuthProvider.LOCAL,
                "provider_user_id": f"bulk{i}",
                "roles": ["user"],
            }
            for i in range(5)
        ]

        users = await user_repo.create_many(users_data)

        assert len(users) == 5
        assert all(user.id is not None for user in users)
        assert all(user.created_at is not None for user in users)

    async def test_update_many(self, user_repo, sample_users):
        """Test bulk update."""
        count = await user_repo.update_many(
            {"is_active__eq": False},
            {"is_active": True}
        )

        assert count == 5

        # Verify updates
        users = await user_repo.get_many(is_active=True)
        assert len(users) == 10

    async def test_delete_many(self, user_repo, sample_users):
        """Test bulk soft delete."""
        count = await user_repo.delete_many({"is_active__eq": False})

        assert count == 5

        # Verify soft deletes
        users = await user_repo.get_many()
        assert len(users) == 5

        users_with_deleted = await user_repo.get_many(include_deleted=True)
        assert len(users_with_deleted) == 10


class TestTransactions:
    """Test transaction functionality."""

    async def test_transaction_context_manager_commit(self, user_repo):
        """Test transaction context manager commits on success."""
        user_data = {
            "email": "tx@example.com",
            "name": "TX User",
            "provider": AuthProvider.LOCAL,
            "provider_user_id": "tx",
            "roles": ["user"],
        }

        async with user_repo.transaction():
            user = User(**user_data)
            user = await user_repo.create(user)
            user_id = user.id

        # Verify commit
        user = await user_repo.get(user_id)
        assert user is not None
        assert user.email == "tx@example.com"

    async def test_transaction_context_manager_rollback(self, user_repo):
        """Test transaction context manager rolls back on error."""
        user_data = {
            "email": "tx@example.com",
            "name": "TX User",
            "provider": AuthProvider.LOCAL,
            "provider_user_id": "tx",
            "roles": ["user"],
        }

        user_id = None
        try:
            async with user_repo.transaction():
                user = User(**user_data)
                user = await user_repo.create(user)
                user_id = user.id

                # Force error
                raise ValueError("Test error")
        except ValueError:
            pass

        # Verify rollback
        if user_id:
            user = await user_repo.get(user_id)
            assert user is None

    async def test_transactional_decorator(self, user_repo):
        """Test transactional decorator."""

        @transactional
        async def create_user(repo: TestUserRepository, data: dict):
            user = User(**data)
            return await repo.create(user)

        user_data = {
            "email": "decorator@example.com",
            "name": "Decorator User",
            "provider": AuthProvider.LOCAL,
            "provider_user_id": "decorator",
            "roles": ["user"],
        }

        user = await create_user(user_repo, user_data)
        assert user.id is not None


class TestCombinedFeatures:
    """Test combining multiple features."""

    async def test_filter_sort_paginate(self, user_repo, sample_users):
        """Test combining filters, sorting, and pagination."""
        # Build query
        query = select(User)

        # Apply filters
        query = user_repo.apply_filters(query, {"is_active__eq": True})

        # Apply sorting
        query = user_repo.apply_sorting(query, "email", "asc")

        # Paginate
        result = await user_repo.paginate(query, page=1, page_size=3)

        assert len(result.items) == 3
        assert result.total == 5
        assert result.total_pages == 2

        # Verify sorting
        emails = [user.email for user in result.items]
        assert emails == sorted(emails)
