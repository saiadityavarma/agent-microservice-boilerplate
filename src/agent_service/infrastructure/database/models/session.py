"""
SQLAlchemy model for agent conversation sessions.

This module defines the database schema for conversation sessions with support for:
- Multi-turn agent conversations
- Session state persistence
- Message history
- Session metadata and context
- Soft deletion
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy import Column, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

from agent_service.infrastructure.database.base_model import BaseModel, SoftDeleteMixin


class SessionStatus(str):
    """
    Session status types.

    Defines the possible states of a conversation session.
    """
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Session(BaseModel, SoftDeleteMixin, table=True):
    """
    Session model for agent conversation tracking.

    Stores conversation sessions with message history, state, and metadata.
    Each session represents a multi-turn conversation with an agent.

    Attributes:
        id: Unique identifier (UUID)
        user_id: UUID of the user who owns this session
        agent_id: Identifier of the agent being used
        title: Human-friendly title for the session
        status: Session status (active, completed, failed, cancelled)
        messages: JSON array of conversation messages
        context: JSON object containing session context and variables
        metadata: JSON object for additional session metadata
        total_messages: Count of messages in the session
        total_tokens: Total tokens used in the session (if tracked)
        last_activity_at: Timestamp of last activity in the session
        expires_at: Optional expiration timestamp for the session
        created_at: Timestamp when session was created
        updated_at: Timestamp when session was last modified
        deleted_at: Timestamp when session was soft deleted (None if active)

    Indexes:
        - user_id: Fast retrieval of user's sessions
        - agent_id: Fast retrieval of sessions by agent
        - status: Fast filtering by status
        - last_activity_at: Fast sorting by recent activity
        - created_at: Fast sorting by creation date

    Example:
        >>> session = Session(
        ...     user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
        ...     agent_id="code_agent",
        ...     title="Debug Python Script",
        ...     status=SessionStatus.ACTIVE,
        ...     messages=[
        ...         {
        ...             "role": "user",
        ...             "content": "Help me debug this code",
        ...             "timestamp": "2024-12-13T10:00:00Z"
        ...         },
        ...         {
        ...             "role": "assistant",
        ...             "content": "I'll help you debug that.",
        ...             "timestamp": "2024-12-13T10:00:05Z"
        ...         }
        ...     ],
        ...     context={"language": "python", "file": "script.py"},
        ...     total_messages=2,
        ...     total_tokens=150
        ... )
    """

    __tablename__ = "sessions"

    # User and agent identification
    user_id: UUID = Field(
        nullable=False,
        index=True,
        description="UUID of the user who owns this session",
        sa_column_kwargs={"comment": "User who owns this session"}
    )

    agent_id: str = Field(
        nullable=False,
        max_length=255,
        index=True,
        description="Identifier of the agent being used",
        sa_column_kwargs={"comment": "Agent identifier for this session"}
    )

    # Session identification
    title: str = Field(
        nullable=False,
        max_length=500,
        description="Human-friendly title for the session",
        sa_column_kwargs={"comment": "Session title"}
    )

    # Session status
    status: str = Field(
        default=SessionStatus.ACTIVE,
        nullable=False,
        max_length=50,
        index=True,
        description="Session status (active, completed, failed, cancelled)",
        sa_column_kwargs={"comment": "Session status: active, completed, failed, cancelled"}
    )

    # Conversation data
    messages: List[Dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB),
        description="JSON array of conversation messages",
        sa_column_kwargs={"comment": "Conversation messages in chronological order"}
    )

    # Session context and metadata
    context: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB),
        description="JSON object containing session context and variables",
        sa_column_kwargs={"comment": "Session context and state variables"}
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB),
        description="JSON object for additional session metadata",
        sa_column_kwargs={"comment": "Additional session metadata"}
    )

    # Usage statistics
    total_messages: int = Field(
        default=0,
        nullable=False,
        description="Count of messages in the session",
        sa_column_kwargs={"comment": "Total number of messages"}
    )

    total_tokens: Optional[int] = Field(
        default=None,
        nullable=True,
        description="Total tokens used in the session",
        sa_column_kwargs={"comment": "Total tokens used (if tracked)"}
    )

    # Activity tracking
    last_activity_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        index=True,
        description="Timestamp of last activity in the session",
        sa_column_kwargs={"comment": "Last activity timestamp"}
    )

    # Expiration
    expires_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        index=True,
        description="Optional expiration timestamp for the session",
        sa_column_kwargs={"comment": "Session expiration timestamp"}
    )

    # Indexes for performance
    __table_args__ = (
        Index('ix_sessions_user_id_status', 'user_id', 'status'),
        Index('ix_sessions_user_id_last_activity', 'user_id', 'last_activity_at'),
        Index('ix_sessions_agent_id_status', 'agent_id', 'status'),
        Index('ix_sessions_status_deleted_at', 'status', 'deleted_at'),
    )

    @property
    def is_active(self) -> bool:
        """
        Check if the session is currently active.

        Returns:
            True if status is ACTIVE and not deleted, False otherwise

        Example:
            >>> session = Session(status=SessionStatus.ACTIVE)
            >>> session.is_active
            True
        """
        return self.status == SessionStatus.ACTIVE and not self.is_deleted

    @property
    def is_expired(self) -> bool:
        """
        Check if the session has expired.

        Returns:
            True if expires_at has passed, False otherwise

        Example:
            >>> from datetime import timedelta
            >>> session = Session(expires_at=datetime.utcnow() - timedelta(days=1))
            >>> session.is_expired
            True
        """
        if self.expires_at is None:
            return False
        return self.expires_at <= datetime.utcnow()

    def add_message(self, role: str, content: str, **kwargs) -> None:
        """
        Add a message to the conversation.

        Args:
            role: Message role (user, assistant, system)
            content: Message content
            **kwargs: Additional message fields

        Example:
            >>> session = Session()
            >>> session.add_message("user", "Hello, agent!")
            >>> session.add_message("assistant", "Hi! How can I help?")
            >>> assert len(session.messages) == 2
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        if self.messages is None:
            self.messages = []
        self.messages.append(message)
        self.total_messages = len(self.messages)
        self.last_activity_at = datetime.utcnow()

    def update_context(self, **kwargs) -> None:
        """
        Update session context variables.

        Args:
            **kwargs: Context variables to update

        Example:
            >>> session = Session()
            >>> session.update_context(language="python", mode="debug")
            >>> assert session.context["language"] == "python"
        """
        if self.context is None:
            self.context = {}
        self.context.update(kwargs)

    def update_metadata(self, **kwargs) -> None:
        """
        Update session metadata.

        Args:
            **kwargs: Metadata fields to update

        Example:
            >>> session = Session()
            >>> session.update_metadata(source="web", version="1.0")
            >>> assert session.metadata["source"] == "web"
        """
        if self.metadata is None:
            self.metadata = {}
        self.metadata.update(kwargs)

    def mark_completed(self) -> None:
        """
        Mark the session as completed.

        Example:
            >>> session = Session(status=SessionStatus.ACTIVE)
            >>> session.mark_completed()
            >>> assert session.status == SessionStatus.COMPLETED
        """
        self.status = SessionStatus.COMPLETED
        self.last_activity_at = datetime.utcnow()

    def mark_failed(self, error: Optional[str] = None) -> None:
        """
        Mark the session as failed.

        Args:
            error: Optional error message

        Example:
            >>> session = Session(status=SessionStatus.ACTIVE)
            >>> session.mark_failed("Agent timeout")
            >>> assert session.status == SessionStatus.FAILED
        """
        self.status = SessionStatus.FAILED
        if error:
            self.update_metadata(error=error)
        self.last_activity_at = datetime.utcnow()

    def mark_cancelled(self, reason: Optional[str] = None) -> None:
        """
        Mark the session as cancelled.

        Args:
            reason: Optional cancellation reason

        Example:
            >>> session = Session(status=SessionStatus.ACTIVE)
            >>> session.mark_cancelled("User requested")
            >>> assert session.status == SessionStatus.CANCELLED
        """
        self.status = SessionStatus.CANCELLED
        if reason:
            self.update_metadata(cancellation_reason=reason)
        self.last_activity_at = datetime.utcnow()

    def __repr__(self) -> str:
        """String representation of the session."""
        return (
            f"Session(id={self.id}, "
            f"user_id={self.user_id}, "
            f"agent_id={self.agent_id!r}, "
            f"title={self.title!r}, "
            f"status={self.status!r}, "
            f"messages={self.total_messages})"
        )
