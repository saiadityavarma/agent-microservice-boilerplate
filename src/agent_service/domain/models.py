# src/agent_service/domain/models.py
"""
Domain entities for the agent service.

Claude Code: Add domain models here extending BaseModel.

Example:
    from agent_service.infrastructure.database.base_model import BaseModel
    from sqlalchemy import Column
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlmodel import Field

    class Session(BaseModel, table=True):
        __tablename__ = "sessions"
        user_id: str
        data: dict = Field(default_factory=dict, sa_column=Column(JSONB))
"""
