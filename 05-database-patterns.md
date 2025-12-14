# Task 05: Database Patterns

## Objective
Establish database connection, base model, and repository patterns. Claude Code follows these when adding database functionality.

## Deliverables

### Connection Manager
```python
# src/agent_service/infrastructure/database/connection.py
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class DatabaseManager:
    """
    Manages async database connections.
    
    Usage:
        db = DatabaseManager()
        await db.connect("postgresql+asyncpg://...")
        async with db.session() as session:
            # use session
    """
    
    def __init__(self):
        self._engine = None
        self._session_factory = None
    
    async def connect(self, url: str) -> None:
        self._engine = create_async_engine(url, pool_pre_ping=True)
        self._session_factory = async_sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def disconnect(self) -> None:
        if self._engine:
            await self._engine.dispose()
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        if not self._session_factory:
            raise RuntimeError("Database not connected")
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise


# Global instance
db = DatabaseManager()
```

### Base Model Pattern
```python
# src/agent_service/infrastructure/database/base_model.py
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Column, DateTime, text
from sqlmodel import SQLModel, Field


class BaseModel(SQLModel):
    """
    Base for all database models.
    
    Claude Code: Extend this for new models.
    
    Example:
        class Session(BaseModel, table=True):
            __tablename__ = "sessions"
            user_id: str
            data: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"onupdate": text("CURRENT_TIMESTAMP")}
    )


class SoftDeleteMixin(SQLModel):
    """Add soft delete to any model."""
    deleted_at: datetime | None = None
    
    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
```

### Repository Pattern
```python
# src/agent_service/infrastructure/database/repositories/base.py
from typing import TypeVar, Generic, Sequence, Any
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

from agent_service.interfaces import IRepository

T = TypeVar("T", bound=SQLModel)


class BaseRepository(IRepository[T], Generic[T]):
    """
    Base repository implementing IRepository.
    
    Claude Code: Extend this for entity-specific repositories.
    
    Example:
        class SessionRepository(BaseRepository[Session]):
            def __init__(self, session: AsyncSession):
                super().__init__(Session, session)
            
            async def get_by_user(self, user_id: str) -> Sequence[Session]:
                query = select(self.model).where(self.model.user_id == user_id)
                result = await self.session.execute(query)
                return result.scalars().all()
    """
    
    def __init__(self, model: type[T], session: AsyncSession):
        self.model = model
        self.session = session
    
    async def get(self, id: UUID) -> T | None:
        return await self.session.get(self.model, id)
    
    async def get_many(self, skip: int = 0, limit: int = 100, **filters) -> Sequence[T]:
        query = select(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def create(self, entity: T) -> T:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
    
    async def update(self, id: UUID, **values) -> T | None:
        entity = await self.get(id)
        if entity:
            for key, value in values.items():
                setattr(entity, key, value)
            await self.session.flush()
        return entity
    
    async def delete(self, id: UUID) -> bool:
        entity = await self.get(id)
        if entity:
            await self.session.delete(entity)
            return True
        return False
```

## Pattern for Claude Code

When adding a new entity:
```python
# 1. Create model in infrastructure/database/models/
class MyEntity(BaseModel, table=True):
    __tablename__ = "my_entities"
    name: str
    value: int

# 2. Create repository
class MyEntityRepository(BaseRepository[MyEntity]):
    def __init__(self, session: AsyncSession):
        super().__init__(MyEntity, session)
    
    # Add custom queries as needed
    async def get_by_name(self, name: str) -> MyEntity | None:
        ...

# 3. Create migration
# alembic revision --autogenerate -m "add my_entity"
```

## Acceptance Criteria
- [ ] Database manager connects/disconnects cleanly
- [ ] Base model has UUID, timestamps
- [ ] Repository CRUD operations work
- [ ] Pattern is clear for Claude Code to extend
