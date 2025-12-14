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
