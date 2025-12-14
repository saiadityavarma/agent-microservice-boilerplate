# src/agent_service/interfaces/repository.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Sequence, Any
from uuid import UUID

T = TypeVar("T")


class IRepository(ABC, Generic[T]):
    """
    Generic repository interface for data access.

    Claude Code: Implement this for each domain entity.

    Example:
        class SessionRepository(IRepository[Session]):
            async def get(self, id: UUID) -> Session | None:
                ...
    """

    @abstractmethod
    async def get(self, id: UUID) -> T | None:
        """Get entity by ID."""
        pass

    @abstractmethod
    async def get_many(
        self,
        skip: int = 0,
        limit: int = 100,
        **filters: Any,
    ) -> Sequence[T]:
        """Get multiple entities with filtering."""
        pass

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create new entity."""
        pass

    @abstractmethod
    async def update(self, id: UUID, **values: Any) -> T | None:
        """Update entity by ID."""
        pass

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete entity by ID."""
        pass
