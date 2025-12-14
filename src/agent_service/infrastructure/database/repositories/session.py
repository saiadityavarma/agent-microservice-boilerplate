# src/agent_service/infrastructure/database/repositories/session.py
"""
Session repository with specialized methods for conversation management.

Provides repository methods for managing agent conversation sessions,
including message history, context, and session analytics.
"""

import logging
from datetime import datetime, timedelta
from typing import Sequence, Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from agent_service.infrastructure.database.models.session import Session, SessionStatus
from agent_service.infrastructure.database.repositories.base import BaseRepository, PaginatedResult
from agent_service.config.settings import get_settings

logger = logging.getLogger(__name__)


class SessionStats(Dict[str, Any]):
    """
    Session statistics for a user.

    Contains aggregated metrics about user's sessions.
    """

    @property
    def total_sessions(self) -> int:
        """Total number of sessions."""
        return self.get("total_sessions", 0)

    @property
    def active_sessions(self) -> int:
        """Number of active sessions."""
        return self.get("active_sessions", 0)

    @property
    def total_messages(self) -> int:
        """Total messages across all sessions."""
        return self.get("total_messages", 0)

    @property
    def total_tokens(self) -> int:
        """Total tokens used across all sessions."""
        return self.get("total_tokens", 0)

    @property
    def avg_messages_per_session(self) -> float:
        """Average messages per session."""
        return self.get("avg_messages_per_session", 0.0)


class SessionRepository(BaseRepository[Session]):
    """
    Repository for Session entity with conversation-specific operations.

    Extends base repository with specialized methods for managing
    conversation sessions, messages, and session analytics.

    Example:
        >>> from agent_service.infrastructure.database.connection import get_session
        >>> async with get_session() as db:
        >>>     repo = SessionRepository(db)
        >>>     sessions = await repo.get_user_sessions(user_id, active_only=True)
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize session repository.

        Args:
            session: SQLAlchemy async session
        """
        super().__init__(Session, session)

    async def get_user_sessions(
        self,
        user_id: UUID,
        active_only: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> Sequence[Session]:
        """
        Get all sessions for a user.

        Args:
            user_id: User UUID
            active_only: If True, return only active sessions
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip

        Returns:
            Sequence of sessions ordered by last activity (most recent first)

        Example:
            >>> sessions = await repo.get_user_sessions(
            ...     user_id=user.id,
            ...     active_only=True,
            ...     limit=10
            ... )
            >>> for session in sessions:
            ...     print(f"{session.title}: {session.total_messages} messages")
        """
        query = select(Session).where(Session.user_id == user_id)

        # Exclude soft-deleted
        query = self._exclude_deleted(query)

        # Filter by status if active_only
        if active_only:
            query = query.where(Session.status == SessionStatus.ACTIVE)

        # Order by most recent activity
        query = query.order_by(Session.last_activity_at.desc())

        # Apply pagination
        query = query.offset(offset).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_session_with_messages(
        self,
        session_id: UUID,
        include_deleted: bool = False
    ) -> Session | None:
        """
        Get session by ID with all messages loaded.

        Args:
            session_id: Session UUID
            include_deleted: Include soft-deleted sessions

        Returns:
            Session with messages or None if not found

        Example:
            >>> session = await repo.get_session_with_messages(session_id)
            >>> if session:
            ...     print(f"Session has {len(session.messages)} messages")
            ...     for msg in session.messages:
            ...         print(f"{msg['role']}: {msg['content']}")
        """
        # Use base get method which includes relationship loading
        session = await self.get(session_id, include_deleted=include_deleted)
        return session

    async def add_message_to_session(
        self,
        session_id: UUID,
        message: Dict[str, Any]
    ) -> Session | None:
        """
        Add a message to a session.

        Automatically updates total_messages count and last_activity_at timestamp.

        Args:
            session_id: Session UUID
            message: Message dictionary with at minimum 'role' and 'content' fields

        Returns:
            Updated session or None if session not found

        Example:
            >>> session = await repo.add_message_to_session(
            ...     session_id=session.id,
            ...     message={
            ...         "role": "user",
            ...         "content": "Hello, how can you help?",
            ...         "metadata": {"source": "web"}
            ...     }
            ... )
            >>> if session:
            ...     print(f"Message added. Total: {session.total_messages}")
        """
        session = await self.get(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return None

        # Check message limit from settings
        settings = get_settings()
        if session.total_messages >= settings.session_max_messages:
            logger.warning(
                f"Session {session_id} has reached max messages "
                f"({settings.session_max_messages})"
            )
            # Still add the message but log warning
            # Alternatively, you could raise an exception or return None

        # Ensure message has timestamp
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()

        # Add message using model method
        session.add_message(
            role=message.get("role", "user"),
            content=message.get("content", ""),
            **{k: v for k, v in message.items() if k not in ("role", "content")}
        )

        await self.session.flush()
        await self.session.refresh(session)

        return session

    async def update_session_context(
        self,
        session_id: UUID,
        context: Dict[str, Any]
    ) -> Session | None:
        """
        Update session context variables.

        Merges new context with existing context.

        Args:
            session_id: Session UUID
            context: Context variables to update/add

        Returns:
            Updated session or None if session not found

        Example:
            >>> session = await repo.update_session_context(
            ...     session_id=session.id,
            ...     context={
            ...         "language": "python",
            ...         "framework": "fastapi",
            ...         "current_file": "main.py"
            ...     }
            ... )
        """
        session = await self.get(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return None

        # Update context using model method
        session.update_context(**context)

        await self.session.flush()
        await self.session.refresh(session)

        return session

    async def cleanup_expired_sessions(self) -> int:
        """
        Mark expired sessions as completed.

        This should be called periodically (e.g., via scheduled task)
        to clean up old sessions based on session_expiry_hours setting.

        Returns:
            Number of sessions marked as completed

        Example:
            >>> # In a scheduled task (e.g., celery, APScheduler)
            >>> cleaned = await repo.cleanup_expired_sessions()
            >>> print(f"Cleaned up {cleaned} expired sessions")
        """
        settings = get_settings()
        expiry_threshold = datetime.utcnow() - timedelta(hours=settings.session_expiry_hours)

        # Find active sessions that are expired
        query = select(Session).where(
            and_(
                Session.status == SessionStatus.ACTIVE,
                Session.deleted_at.is_(None),
                or_(
                    # Session has explicit expiration that has passed
                    and_(
                        Session.expires_at.is_not(None),
                        Session.expires_at <= datetime.utcnow()
                    ),
                    # Session has no activity beyond expiry threshold
                    Session.last_activity_at <= expiry_threshold
                )
            )
        )

        result = await self.session.execute(query)
        expired_sessions = result.scalars().all()

        # Mark each as completed
        for session in expired_sessions:
            session.mark_completed()
            logger.info(f"Marked session {session.id} as completed (expired)")

        if expired_sessions:
            await self.session.flush()

        return len(expired_sessions)

    async def get_session_stats(self, user_id: UUID) -> SessionStats:
        """
        Get session statistics for a user.

        Provides aggregated metrics about user's sessions for analytics.

        Args:
            user_id: User UUID

        Returns:
            SessionStats dictionary with aggregated metrics

        Example:
            >>> stats = await repo.get_session_stats(user_id)
            >>> print(f"Total sessions: {stats.total_sessions}")
            >>> print(f"Active sessions: {stats.active_sessions}")
            >>> print(f"Total messages: {stats.total_messages}")
            >>> print(f"Avg messages/session: {stats.avg_messages_per_session:.1f}")
        """
        # Query for aggregated statistics
        query = select(
            func.count(Session.id).label("total_sessions"),
            func.count(Session.id).filter(
                Session.status == SessionStatus.ACTIVE
            ).label("active_sessions"),
            func.sum(Session.total_messages).label("total_messages"),
            func.sum(Session.total_tokens).label("total_tokens"),
            func.avg(Session.total_messages).label("avg_messages_per_session")
        ).where(
            and_(
                Session.user_id == user_id,
                Session.deleted_at.is_(None)
            )
        )

        result = await self.session.execute(query)
        row = result.one()

        return SessionStats({
            "total_sessions": row.total_sessions or 0,
            "active_sessions": row.active_sessions or 0,
            "total_messages": row.total_messages or 0,
            "total_tokens": row.total_tokens or 0,
            "avg_messages_per_session": float(row.avg_messages_per_session or 0.0)
        })

    async def get_recent_sessions(
        self,
        user_id: UUID,
        hours: int = 24,
        limit: int = 10
    ) -> Sequence[Session]:
        """
        Get user's recent sessions within specified time window.

        Args:
            user_id: User UUID
            hours: Time window in hours
            limit: Maximum number of sessions to return

        Returns:
            Sequence of recent sessions

        Example:
            >>> # Get sessions from last 24 hours
            >>> recent = await repo.get_recent_sessions(user_id, hours=24)
        """
        threshold = datetime.utcnow() - timedelta(hours=hours)

        query = select(Session).where(
            and_(
                Session.user_id == user_id,
                Session.last_activity_at >= threshold,
                Session.deleted_at.is_(None)
            )
        ).order_by(
            Session.last_activity_at.desc()
        ).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_sessions_by_agent(
        self,
        agent_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Sequence[Session]:
        """
        Get sessions for a specific agent.

        Args:
            agent_id: Agent identifier
            status: Optional status filter
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip

        Returns:
            Sequence of sessions

        Example:
            >>> # Get all active sessions for code_agent
            >>> sessions = await repo.get_sessions_by_agent(
            ...     agent_id="code_agent",
            ...     status=SessionStatus.ACTIVE
            ... )
        """
        query = select(Session).where(Session.agent_id == agent_id)

        # Exclude soft-deleted
        query = self._exclude_deleted(query)

        # Filter by status if provided
        if status:
            query = query.where(Session.status == status)

        # Order by most recent activity
        query = query.order_by(Session.last_activity_at.desc())

        # Apply pagination
        query = query.offset(offset).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def search_sessions(
        self,
        user_id: UUID,
        search_term: str,
        limit: int = 20
    ) -> Sequence[Session]:
        """
        Search user's sessions by title or message content.

        Note: For message content search, this performs a simple JSONB search.
        For production use with large datasets, consider using full-text search
        (PostgreSQL FTS) or external search engine (Elasticsearch).

        Args:
            user_id: User UUID
            search_term: Search term to match against title
            limit: Maximum number of results

        Returns:
            Sequence of matching sessions

        Example:
            >>> # Search for sessions about Python
            >>> sessions = await repo.search_sessions(user_id, "python")
        """
        query = select(Session).where(
            and_(
                Session.user_id == user_id,
                Session.deleted_at.is_(None),
                Session.title.ilike(f"%{search_term}%")
            )
        ).order_by(
            Session.last_activity_at.desc()
        ).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_paginated_user_sessions(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        agent_id: Optional[str] = None
    ) -> PaginatedResult:
        """
        Get paginated sessions for a user with optional filters.

        Args:
            user_id: User UUID
            page: Page number (1-indexed)
            page_size: Number of items per page
            status: Optional status filter
            agent_id: Optional agent filter

        Returns:
            PaginatedResult with sessions and pagination metadata

        Example:
            >>> result = await repo.get_paginated_user_sessions(
            ...     user_id=user.id,
            ...     page=1,
            ...     page_size=10,
            ...     status=SessionStatus.ACTIVE
            ... )
            >>> print(f"Page {result.page} of {result.total_pages}")
            >>> for session in result.items:
            ...     print(session.title)
        """
        query = select(Session).where(Session.user_id == user_id)

        # Exclude soft-deleted
        query = self._exclude_deleted(query)

        # Apply filters
        if status:
            query = query.where(Session.status == status)
        if agent_id:
            query = query.where(Session.agent_id == agent_id)

        # Order by most recent activity
        query = query.order_by(Session.last_activity_at.desc())

        # Use base repository pagination
        return await self.paginate(query, page=page, page_size=page_size)

    async def count_active_sessions(self, user_id: UUID) -> int:
        """
        Count active sessions for a user.

        Args:
            user_id: User UUID

        Returns:
            Number of active sessions

        Example:
            >>> count = await repo.count_active_sessions(user_id)
            >>> print(f"User has {count} active sessions")
        """
        query = select(func.count(Session.id)).where(
            and_(
                Session.user_id == user_id,
                Session.status == SessionStatus.ACTIVE,
                Session.deleted_at.is_(None)
            )
        )

        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_session_by_title(
        self,
        user_id: UUID,
        title: str
    ) -> Session | None:
        """
        Get session by exact title match.

        Args:
            user_id: User UUID
            title: Exact session title

        Returns:
            Session or None if not found

        Example:
            >>> session = await repo.get_session_by_title(
            ...     user_id=user.id,
            ...     title="Debug Python Script"
            ... )
        """
        query = select(Session).where(
            and_(
                Session.user_id == user_id,
                Session.title == title,
                Session.deleted_at.is_(None)
            )
        )

        result = await self.session.execute(query)
        return result.scalars().first()

    async def bulk_update_session_status(
        self,
        session_ids: List[UUID],
        status: str
    ) -> int:
        """
        Update status for multiple sessions.

        Args:
            session_ids: List of session UUIDs
            status: New status

        Returns:
            Number of sessions updated

        Example:
            >>> # Mark multiple sessions as completed
            >>> count = await repo.bulk_update_session_status(
            ...     session_ids=[id1, id2, id3],
            ...     status=SessionStatus.COMPLETED
            ... )
        """
        if not session_ids:
            return 0

        updated = await self.update_many(
            filters={"id__in": session_ids},
            updates={
                "status": status,
                "last_activity_at": datetime.utcnow()
            }
        )

        return updated
