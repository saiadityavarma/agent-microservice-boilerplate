# src/agent_service/infrastructure/database/repositories/base.py
from typing import TypeVar, Generic, Sequence, Any, Literal, Optional, NamedTuple
from uuid import UUID
from datetime import datetime
from contextlib import asynccontextmanager
from functools import wraps
import logging

from sqlalchemy import select, Select, func, asc, desc, or_, and_, delete as sql_delete, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

from agent_service.interfaces import IRepository

T = TypeVar("T", bound=SQLModel)

logger = logging.getLogger(__name__)


class PaginatedResult(NamedTuple):
    """Result of a paginated query."""
    items: Sequence[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


def transactional(func):
    """
    Decorator to wrap repository method in a transaction.

    Commits on success, rolls back on exception.

    Example:
        @transactional
        async def create_user_and_session(self, user_data, session_data):
            user = await self.create(user_data)
            session = await self.session_repo.create(session_data)
            return user, session
    """
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        try:
            result = await func(self, *args, **kwargs)
            await self.session.commit()
            return result
        except Exception:
            await self.session.rollback()
            raise
    return wrapper


class BaseRepository(IRepository[T], Generic[T]):
    """
    Enhanced base repository implementing IRepository with advanced features.

    Features:
    - Soft delete by default with hard delete option
    - Pagination helper with metadata
    - Sorting with support for nested fields
    - Advanced filtering with operators
    - Bulk operations (create, update, delete)
    - Transaction support via decorator and context manager
    - Query logging for debugging

    Claude Code: Extend this for entity-specific repositories.

    Example:
        class SessionRepository(BaseRepository[Session]):
            def __init__(self, session: AsyncSession):
                super().__init__(Session, session)

            async def get_by_user(self, user_id: str) -> Sequence[Session]:
                query = select(self.model).where(self.model.user_id == user_id)
                query = self._exclude_deleted(query)  # Respect soft delete
                result = await self.session.execute(query)
                return result.scalars().all()
    """

    def __init__(self, model: type[T], session: AsyncSession, enable_query_logging: bool = False):
        self.model = model
        self.session = session
        self.enable_query_logging = enable_query_logging

    def _has_soft_delete(self) -> bool:
        """Check if model supports soft delete."""
        return hasattr(self.model, "deleted_at")

    def _exclude_deleted(self, query: Select, include_deleted: bool = False) -> Select:
        """Exclude soft-deleted records from query unless include_deleted=True."""
        if not include_deleted and self._has_soft_delete():
            query = query.where(self.model.deleted_at.is_(None))
        return query

    def _log_query(self, query: Select, params: dict = None) -> None:
        """Log SQL query with parameters for debugging."""
        if self.enable_query_logging:
            logger.debug(f"Query: {query}")
            if params:
                logger.debug(f"Params: {params}")

    async def get(self, id: UUID, include_deleted: bool = False) -> T | None:
        """
        Get entity by ID.

        Args:
            id: Entity UUID
            include_deleted: Include soft-deleted records

        Returns:
            Entity or None if not found
        """
        entity = await self.session.get(self.model, id)
        if entity and not include_deleted and self._has_soft_delete():
            if getattr(entity, "deleted_at", None) is not None:
                return None
        return entity

    async def get_many(
        self,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
        **filters
    ) -> Sequence[T]:
        """
        Get multiple entities with filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: Include soft-deleted records
            **filters: Simple equality filters (field=value)

        Returns:
            Sequence of entities
        """
        query = select(self.model)
        query = self._exclude_deleted(query, include_deleted)

        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)

        query = query.offset(skip).limit(limit)
        self._log_query(query, filters)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def create(self, entity: T) -> T:
        """
        Create new entity.

        Args:
            entity: Entity to create

        Returns:
            Created entity with generated ID and timestamps
        """
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def create_many(self, items: list[dict]) -> list[T]:
        """
        Create multiple entities in bulk.

        Args:
            items: List of dictionaries with entity data

        Returns:
            List of created entities

        Example:
            users = await repo.create_many([
                {"email": "user1@example.com", "name": "User 1"},
                {"email": "user2@example.com", "name": "User 2"},
            ])
        """
        entities = [self.model(**item) for item in items]
        self.session.add_all(entities)
        await self.session.flush()

        for entity in entities:
            await self.session.refresh(entity)

        return entities

    async def update(self, id: UUID, **values) -> T | None:
        """
        Update entity by ID.

        Args:
            id: Entity UUID
            **values: Fields to update

        Returns:
            Updated entity or None if not found
        """
        entity = await self.get(id)
        if entity:
            for key, value in values.items():
                setattr(entity, key, value)
            await self.session.flush()
            await self.session.refresh(entity)
        return entity

    async def update_many(self, filters: dict, updates: dict) -> int:
        """
        Update multiple entities matching filters.

        Args:
            filters: Filter criteria (field__operator: value)
            updates: Fields to update

        Returns:
            Number of updated records

        Example:
            count = await repo.update_many(
                {"is_active__eq": False},
                {"deleted_at": datetime.utcnow()}
            )
        """
        query = select(self.model)
        query = self._exclude_deleted(query)
        query = self.apply_filters(query, filters)

        # Get IDs of matching records
        result = await self.session.execute(query)
        entities = result.scalars().all()

        if not entities:
            return 0

        # Update entities
        ids = [entity.id for entity in entities]
        update_stmt = (
            sql_update(self.model)
            .where(self.model.id.in_(ids))
            .values(**updates)
        )

        result = await self.session.execute(update_stmt)
        await self.session.flush()

        return result.rowcount

    async def delete(self, id: UUID) -> bool:
        """
        Soft delete entity by ID (sets deleted_at timestamp).

        For hard delete, use hard_delete() method.

        Args:
            id: Entity UUID

        Returns:
            True if deleted, False if not found
        """
        entity = await self.get(id)
        if not entity:
            return False

        if self._has_soft_delete():
            entity.deleted_at = datetime.utcnow()
            await self.session.flush()
        else:
            # Fall back to hard delete if model doesn't support soft delete
            await self.session.delete(entity)

        return True

    async def hard_delete(self, id: UUID) -> bool:
        """
        Permanently delete entity by ID.

        Warning: This operation cannot be undone.

        Args:
            id: Entity UUID

        Returns:
            True if deleted, False if not found
        """
        entity = await self.get(id, include_deleted=True)
        if entity:
            await self.session.delete(entity)
            await self.session.flush()
            return True
        return False

    async def delete_many(self, filters: dict) -> int:
        """
        Soft delete multiple entities matching filters.

        Args:
            filters: Filter criteria (field__operator: value)

        Returns:
            Number of deleted records

        Example:
            count = await repo.delete_many({"is_active__eq": False})
        """
        if self._has_soft_delete():
            return await self.update_many(filters, {"deleted_at": datetime.utcnow()})
        else:
            # Hard delete if soft delete not supported
            query = select(self.model)
            query = self.apply_filters(query, filters)

            result = await self.session.execute(query)
            entities = result.scalars().all()

            for entity in entities:
                await self.session.delete(entity)

            await self.session.flush()
            return len(entities)

    def apply_filters(self, query: Select, filters: dict) -> Select:
        """
        Apply advanced filters to query with operator support.

        Supported operators:
        - eq: Equal (field__eq=value)
        - ne: Not equal (field__ne=value)
        - gt: Greater than (field__gt=value)
        - gte: Greater than or equal (field__gte=value)
        - lt: Less than (field__lt=value)
        - lte: Less than or equal (field__lte=value)
        - like: SQL LIKE (field__like="%value%")
        - ilike: Case-insensitive LIKE (field__ilike="%value%")
        - in: IN clause (field__in=[value1, value2])
        - not_in: NOT IN clause (field__not_in=[value1, value2])
        - is_null: IS NULL (field__is_null=True)
        - is_not_null: IS NOT NULL (field__is_not_null=True)

        Args:
            query: SQLAlchemy select query
            filters: Dictionary of filters with operators

        Returns:
            Modified query

        Example:
            query = apply_filters(query, {
                "created_at__gte": datetime(2024, 1, 1),
                "email__ilike": "%@example.com",
                "is_active__eq": True,
            })
        """
        for key, value in filters.items():
            if "__" in key:
                field_name, operator = key.rsplit("__", 1)
            else:
                field_name, operator = key, "eq"

            if not hasattr(self.model, field_name):
                continue

            field = getattr(self.model, field_name)

            if operator == "eq":
                query = query.where(field == value)
            elif operator == "ne":
                query = query.where(field != value)
            elif operator == "gt":
                query = query.where(field > value)
            elif operator == "gte":
                query = query.where(field >= value)
            elif operator == "lt":
                query = query.where(field < value)
            elif operator == "lte":
                query = query.where(field <= value)
            elif operator == "like":
                query = query.where(field.like(value))
            elif operator == "ilike":
                query = query.where(field.ilike(value))
            elif operator == "in":
                query = query.where(field.in_(value))
            elif operator == "not_in":
                query = query.where(field.not_in(value))
            elif operator == "is_null":
                if value:
                    query = query.where(field.is_(None))
                else:
                    query = query.where(field.is_not(None))
            elif operator == "is_not_null":
                if value:
                    query = query.where(field.is_not(None))
                else:
                    query = query.where(field.is_(None))

        return query

    def apply_sorting(
        self,
        query: Select,
        sort_by: str = "created_at",
        order: Literal["asc", "desc"] = "desc"
    ) -> Select:
        """
        Apply sorting to query with support for nested fields.

        Args:
            query: SQLAlchemy select query
            sort_by: Field name to sort by (supports nested: "user.email")
            order: Sort order ("asc" or "desc")

        Returns:
            Modified query

        Example:
            query = apply_sorting(query, "created_at", "desc")
            query = apply_sorting(query, "user.email", "asc")
        """
        # Handle nested fields (e.g., "user.email")
        if "." in sort_by:
            # For nested fields, we need to join tables
            # This is a simplified implementation - extend as needed
            parts = sort_by.split(".")
            field_name = parts[-1]
            # For now, just use the field name without join
            # A full implementation would handle joins
            if hasattr(self.model, field_name):
                field = getattr(self.model, field_name)
            else:
                # Fall back to created_at if field doesn't exist
                field = self.model.created_at
        else:
            if hasattr(self.model, sort_by):
                field = getattr(self.model, sort_by)
            else:
                # Fall back to created_at if field doesn't exist
                field = self.model.created_at

        if order == "asc":
            query = query.order_by(asc(field))
        else:
            query = query.order_by(desc(field))

        return query

    async def paginate(
        self,
        query: Select,
        page: int = 1,
        page_size: int = 20
    ) -> PaginatedResult:
        """
        Paginate query results with metadata.

        Args:
            query: SQLAlchemy select query (before pagination)
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            PaginatedResult with items and pagination metadata

        Example:
            query = select(User).where(User.is_active == True)
            result = await repo.paginate(query, page=2, page_size=10)
            print(f"Page {result.page} of {result.total_pages}")
            for user in result.items:
                print(user.email)
        """
        # Ensure page is at least 1
        page = max(1, page)

        # Count total items
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        # Calculate pagination
        total_pages = (total + page_size - 1) // page_size  # Ceiling division
        has_next = page < total_pages
        has_prev = page > 1

        # Apply pagination to query
        offset = (page - 1) * page_size
        paginated_query = query.offset(offset).limit(page_size)

        self._log_query(paginated_query, {"page": page, "page_size": page_size})

        # Execute query
        result = await self.session.execute(paginated_query)
        items = result.scalars().all()

        return PaginatedResult(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
        )

    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for explicit transaction handling.

        Example:
            async with repo.transaction():
                user = await repo.create(user_data)
                await other_repo.create(related_data)
                # Commits on success, rolls back on exception
        """
        try:
            yield
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
