"""
Example usage of enhanced BaseRepository features.

This file demonstrates all the advanced features added to the BaseRepository:
1. Soft delete with hard delete option
2. Pagination helper
3. Sorting helper
4. Advanced filtering with operators
5. Bulk operations
6. Transaction support
7. Query logging
"""

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from agent_service.infrastructure.database.repositories.base import BaseRepository, transactional
from agent_service.infrastructure.database.models.user import User


class UserRepository(BaseRepository[User]):
    """Example user repository extending BaseRepository."""

    def __init__(self, session: AsyncSession, enable_query_logging: bool = False):
        super().__init__(User, session, enable_query_logging)


async def example_soft_delete(repo: UserRepository, user_id):
    """Example: Soft delete functionality."""

    # Soft delete (sets deleted_at timestamp)
    deleted = await repo.delete(user_id)

    # Get will exclude soft-deleted records by default
    user = await repo.get(user_id)  # Returns None

    # Include deleted records
    user = await repo.get(user_id, include_deleted=True)  # Returns user

    # Hard delete (permanent)
    await repo.hard_delete(user_id)

    # Now it's really gone
    user = await repo.get(user_id, include_deleted=True)  # Returns None


async def example_pagination(repo: UserRepository):
    """Example: Pagination with metadata."""

    from sqlalchemy import select

    # Build query
    query = select(User).where(User.is_active == True)

    # Paginate
    result = await repo.paginate(query, page=2, page_size=10)

    # Access results
    print(f"Page {result.page} of {result.total_pages}")
    print(f"Total items: {result.total}")
    print(f"Has next: {result.has_next}")
    print(f"Has previous: {result.has_prev}")

    for user in result.items:
        print(f"- {user.email}")


async def example_sorting(repo: UserRepository):
    """Example: Sorting queries."""

    from sqlalchemy import select

    query = select(User)

    # Sort by created_at descending (default)
    query = repo.apply_sorting(query, "created_at", "desc")

    # Sort by email ascending
    query = repo.apply_sorting(query, "email", "asc")

    # Sort by name descending
    query = repo.apply_sorting(query, "name", "desc")

    result = await repo.session.execute(query)
    users = result.scalars().all()


async def example_filtering(repo: UserRepository):
    """Example: Advanced filtering with operators."""

    from sqlalchemy import select

    query = select(User)

    # Apply filters with operators
    filters = {
        # Equality
        "is_active__eq": True,

        # Greater than or equal
        "created_at__gte": datetime(2024, 1, 1),

        # Case-insensitive LIKE
        "email__ilike": "%@example.com",

        # IN clause
        "provider__in": ["azure_ad", "aws_cognito"],

        # Not equal
        "name__ne": "Admin",

        # IS NOT NULL
        "deleted_at__is_null": True,
    }

    query = repo.apply_filters(query, filters)
    result = await repo.session.execute(query)
    users = result.scalars().all()


async def example_bulk_create(repo: UserRepository):
    """Example: Bulk create operations."""

    users_data = [
        {
            "email": "user1@example.com",
            "name": "User 1",
            "provider": "local",
            "provider_user_id": "user1",
            "roles": ["user"],
            "is_active": True,
        },
        {
            "email": "user2@example.com",
            "name": "User 2",
            "provider": "local",
            "provider_user_id": "user2",
            "roles": ["user"],
            "is_active": True,
        },
    ]

    # Create multiple users at once
    users = await repo.create_many(users_data)
    print(f"Created {len(users)} users")


async def example_bulk_update(repo: UserRepository):
    """Example: Bulk update operations."""

    # Update all inactive users
    count = await repo.update_many(
        filters={"is_active__eq": False},
        updates={"deleted_at": datetime.utcnow()}
    )
    print(f"Soft deleted {count} inactive users")

    # Update users created before a date
    count = await repo.update_many(
        filters={"created_at__lt": datetime(2024, 1, 1)},
        updates={"is_active": False}
    )
    print(f"Deactivated {count} old users")


async def example_bulk_delete(repo: UserRepository):
    """Example: Bulk delete operations."""

    # Soft delete all inactive users
    count = await repo.delete_many({"is_active__eq": False})
    print(f"Soft deleted {count} inactive users")

    # Soft delete users from specific provider
    count = await repo.delete_many({"provider__eq": "local"})
    print(f"Soft deleted {count} local users")


async def example_transaction_decorator(repo: UserRepository):
    """Example: Transaction decorator."""

    @transactional
    async def create_user_with_related_data(user_data: dict):
        """Create user and related data in a transaction."""
        user = User(**user_data)
        user = await repo.create(user)

        # If this fails, the user creation is rolled back
        # ... create related data ...

        return user

    user_data = {
        "email": "test@example.com",
        "name": "Test User",
        "provider": "local",
        "provider_user_id": "test",
        "roles": ["user"],
        "is_active": True,
    }

    try:
        user = await create_user_with_related_data(user_data)
        print(f"Created user: {user.email}")
    except Exception as e:
        print(f"Transaction rolled back: {e}")


async def example_transaction_context_manager(repo: UserRepository):
    """Example: Transaction context manager."""

    user_data = {
        "email": "test@example.com",
        "name": "Test User",
        "provider": "local",
        "provider_user_id": "test",
        "roles": ["user"],
        "is_active": True,
    }

    try:
        async with repo.transaction():
            user = User(**user_data)
            user = await repo.create(user)

            # If this fails, the user creation is rolled back
            # ... create related data ...

            print(f"Created user: {user.email}")
    except Exception as e:
        print(f"Transaction rolled back: {e}")


async def example_query_logging(session: AsyncSession):
    """Example: Query logging for debugging."""

    # Enable query logging
    repo = UserRepository(session, enable_query_logging=True)

    # All queries will be logged
    users = await repo.get_many(is_active=True)

    # Pagination also logs queries
    from sqlalchemy import select
    query = select(User)
    result = await repo.paginate(query, page=1, page_size=10)


async def example_combined_features(repo: UserRepository):
    """Example: Combining multiple features."""

    from sqlalchemy import select

    # Build base query
    query = select(User)

    # Apply filters
    filters = {
        "is_active__eq": True,
        "created_at__gte": datetime(2024, 1, 1),
        "email__ilike": "%@example.com",
    }
    query = repo.apply_filters(query, filters)

    # Apply sorting
    query = repo.apply_sorting(query, "created_at", "desc")

    # Paginate
    result = await repo.paginate(query, page=1, page_size=20)

    print(f"Found {result.total} active users from example.com")
    print(f"Showing page {result.page} of {result.total_pages}")

    for user in result.items:
        print(f"- {user.email} (created: {user.created_at})")


async def example_soft_delete_queries(repo: UserRepository):
    """Example: Working with soft-deleted records."""

    # Get only active (non-deleted) records
    active_users = await repo.get_many(is_active=True)

    # Get all records including deleted
    all_users = await repo.get_many(include_deleted=True)

    # Combine with filters
    from sqlalchemy import select

    # Query for deleted records
    query = select(User)
    query = repo.apply_filters(query, {"deleted_at__is_not_null": True})
    result = await repo.session.execute(query)
    deleted_users = result.scalars().all()

    print(f"Active users: {len(active_users)}")
    print(f"All users: {len(all_users)}")
    print(f"Deleted users: {len(deleted_users)}")
