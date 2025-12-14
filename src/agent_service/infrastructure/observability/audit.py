"""
Audit logging service for comprehensive security and compliance tracking.

This module provides:
- AuditLogger class for programmatic audit logging
- Decorator for automatic route auditing
- Request context capture (user, IP, user agent, etc.)
- Integration with existing observability infrastructure

Usage:
    Programmatic logging:
        >>> from agent_service.infrastructure.observability.audit import get_audit_logger
        >>>
        >>> audit_logger = get_audit_logger()
        >>> await audit_logger.log(
        ...     action=AuditAction.UPDATE,
        ...     resource_type="agent",
        ...     resource_id="agent-123",
        ...     changes={"name": {"old": "Old", "new": "New"}},
        ...     metadata={"reason": "User requested"}
        ... )

    Authentication events:
        >>> await audit_logger.log_auth_event(
        ...     event_type=AuditAction.LOGIN,
        ...     user_id=uuid.uuid4(),
        ...     success=True
        ... )

    Data access logging:
        >>> await audit_logger.log_data_access(
        ...     resource_type="user",
        ...     resource_id="user-123",
        ...     user_id=uuid.uuid4()
        ... )

    Decorator for routes:
        >>> from agent_service.infrastructure.observability.audit import audit_log
        >>> from agent_service.infrastructure.database.models.audit_log import AuditAction
        >>>
        >>> @router.post("/agents")
        >>> @audit_log(action=AuditAction.CREATE, resource_type="agent")
        >>> async def create_agent(agent: AgentCreate):
        ...     # Route logic here
        ...     return created_agent
"""

from datetime import datetime
from typing import Optional, Dict, Any, Callable
from uuid import UUID, uuid4
from functools import wraps
import json

from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert

from agent_service.infrastructure.database.models.audit_log import AuditLog, AuditAction
from agent_service.config.settings import get_settings
from agent_service.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


class AuditLogger:
    """
    Service for creating and managing audit log entries.

    This class provides methods for logging various types of audit events:
    - General actions (CREATE, READ, UPDATE, DELETE, EXECUTE)
    - Authentication events (LOGIN, LOGOUT, FAILED_AUTH)
    - Data access tracking

    The logger automatically captures request context when used within
    a FastAPI request context.
    """

    def __init__(self, db_session: AsyncSession, request: Optional[Request] = None):
        """
        Initialize the audit logger.

        Args:
            db_session: SQLAlchemy async session for database operations
            request: Optional FastAPI request object for context capture
        """
        self.db_session = db_session
        self.request = request
        self.settings = get_settings()

    async def log(
        self,
        action: AuditAction | str,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[UUID] = None,
        changes: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request_body: Optional[str] = None,
        response_status: int = 200,
    ) -> Optional[AuditLog]:
        """
        Log an audit event.

        Args:
            action: Type of action (CREATE, READ, UPDATE, DELETE, etc.)
            resource_type: Type of resource (user, agent, tool, api_key, etc.)
            resource_id: Identifier of the specific resource
            user_id: UUID of the user performing the action
            changes: Dictionary of changes for UPDATE operations (before/after)
            metadata: Additional context and metadata
            request_body: Request body (will be truncated/redacted if needed)
            response_status: HTTP response status code

        Returns:
            Created AuditLog entry or None if audit logging is disabled

        Example:
            >>> await audit_logger.log(
            ...     action=AuditAction.UPDATE,
            ...     resource_type="agent",
            ...     resource_id="agent-123",
            ...     user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            ...     changes={"name": {"old": "Agent 1", "new": "Updated Agent"}},
            ...     metadata={"reason": "User requested name change"},
            ...     response_status=200
            ... )
        """
        # Check if audit logging is enabled
        if not self.settings.audit_logging_enabled:
            return None

        try:
            # Convert action to string if it's an enum
            action_str = action.value if isinstance(action, AuditAction) else action

            # Extract request context
            request_context = self._extract_request_context(user_id)

            # Prepare request body (truncate/redact if needed)
            prepared_body = self._prepare_request_body(request_body)

            # Create audit log entry
            audit_entry = AuditLog(
                timestamp=datetime.utcnow(),
                user_id=request_context["user_id"],
                action=action_str,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=request_context["ip_address"],
                user_agent=request_context["user_agent"],
                request_id=request_context["request_id"],
                request_path=request_context["request_path"],
                request_method=request_context["request_method"],
                request_body=prepared_body,
                response_status=response_status,
                changes=changes,
                metadata=metadata,
            )

            # Insert into database
            self.db_session.add(audit_entry)
            await self.db_session.commit()
            await self.db_session.refresh(audit_entry)

            logger.info(
                "audit_event_logged",
                audit_id=str(audit_entry.id),
                action=action_str,
                resource_type=resource_type,
                resource_id=resource_id,
                user_id=str(request_context["user_id"]) if request_context["user_id"] else None,
            )

            return audit_entry

        except Exception as e:
            logger.error(
                "audit_logging_failed",
                error=str(e),
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
            )
            # Don't fail the operation if audit logging fails
            return None

    async def log_auth_event(
        self,
        event_type: AuditAction | str,
        user_id: Optional[UUID] = None,
        success: bool = True,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[AuditLog]:
        """
        Log an authentication event.

        Args:
            event_type: Type of auth event (LOGIN, LOGOUT, FAILED_AUTH)
            user_id: UUID of the user (if known)
            success: Whether the auth attempt was successful
            reason: Reason for failure (if applicable)
            metadata: Additional context

        Returns:
            Created AuditLog entry or None if audit logging is disabled

        Example:
            >>> # Successful login
            >>> await audit_logger.log_auth_event(
            ...     event_type=AuditAction.LOGIN,
            ...     user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            ...     success=True
            ... )
            >>>
            >>> # Failed authentication
            >>> await audit_logger.log_auth_event(
            ...     event_type=AuditAction.FAILED_AUTH,
            ...     user_id=None,
            ...     success=False,
            ...     reason="Invalid credentials"
            ... )
        """
        # Prepare metadata
        auth_metadata = metadata or {}
        auth_metadata["success"] = success
        if reason:
            auth_metadata["reason"] = reason

        # Determine response status
        response_status = 200 if success else 401

        return await self.log(
            action=event_type,
            resource_type="authentication",
            resource_id=str(user_id) if user_id else None,
            user_id=user_id,
            metadata=auth_metadata,
            response_status=response_status,
        )

    async def log_data_access(
        self,
        resource_type: str,
        resource_id: str,
        user_id: UUID,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[AuditLog]:
        """
        Log a data access event (READ operation).

        Args:
            resource_type: Type of resource accessed
            resource_id: Identifier of the resource
            user_id: UUID of the user accessing the data
            metadata: Additional context

        Returns:
            Created AuditLog entry or None if audit logging is disabled

        Example:
            >>> await audit_logger.log_data_access(
            ...     resource_type="user",
            ...     resource_id="user-123",
            ...     user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            ...     metadata={"accessed_fields": ["email", "name"]}
            ... )
        """
        return await self.log(
            action=AuditAction.READ,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            metadata=metadata,
        )

    def _extract_request_context(self, user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        Extract context information from the current request.

        Args:
            user_id: Optional user ID to override request context

        Returns:
            Dictionary containing request context information
        """
        if self.request:
            # Extract user ID from request state if not provided
            if user_id is None:
                user_id = getattr(self.request.state, "user_id", None)
                if user_id and isinstance(user_id, str):
                    try:
                        user_id = UUID(user_id)
                    except (ValueError, AttributeError):
                        user_id = None

            # Extract request ID
            request_id = getattr(self.request.state, "request_id", None)
            if request_id and isinstance(request_id, str):
                try:
                    request_id = UUID(request_id)
                except (ValueError, AttributeError):
                    request_id = uuid4()
            else:
                request_id = request_id or uuid4()

            # Extract IP address
            ip_address = self.request.client.host if self.request.client else "unknown"

            # Check for X-Forwarded-For header (proxy/load balancer)
            forwarded_for = self.request.headers.get("X-Forwarded-For")
            if forwarded_for:
                # Get the first IP in the chain
                ip_address = forwarded_for.split(",")[0].strip()

            return {
                "user_id": user_id,
                "ip_address": ip_address,
                "user_agent": self.request.headers.get("User-Agent", "unknown"),
                "request_id": request_id,
                "request_path": self.request.url.path,
                "request_method": self.request.method,
            }
        else:
            # No request context (programmatic call)
            return {
                "user_id": user_id,
                "ip_address": "system",
                "user_agent": "system",
                "request_id": uuid4(),
                "request_path": "/system",
                "request_method": "SYSTEM",
            }

    def _prepare_request_body(self, request_body: Optional[str]) -> Optional[str]:
        """
        Prepare request body for storage (truncate/redact as needed).

        Args:
            request_body: Raw request body

        Returns:
            Prepared request body or None
        """
        if not request_body:
            return None

        # Check if we should include request body
        if not self.settings.log_include_request_body:
            return "[REDACTED]"

        # Truncate to max length
        max_length = self.settings.log_max_body_length
        if len(request_body) > max_length:
            return request_body[:max_length] + "...[TRUNCATED]"

        return request_body


def audit_log(
    action: AuditAction | str,
    resource_type: str,
    extract_resource_id: Optional[Callable] = None,
):
    """
    Decorator for automatically auditing route operations.

    This decorator captures request/response information and creates
    audit log entries for the decorated route.

    Args:
        action: Type of action being performed
        resource_type: Type of resource being operated on
        extract_resource_id: Optional function to extract resource ID from response

    Returns:
        Decorated function

    Example:
        >>> from agent_service.infrastructure.observability.audit import audit_log
        >>> from agent_service.infrastructure.database.models.audit_log import AuditAction
        >>>
        >>> @router.post("/agents")
        >>> @audit_log(action=AuditAction.CREATE, resource_type="agent")
        >>> async def create_agent(
        ...     agent: AgentCreate,
        ...     request: Request,
        ...     db: AsyncSession = Depends(get_db_session),
        ... ):
        ...     created_agent = await agent_service.create(agent)
        ...     return created_agent
        >>>
        >>> # With resource ID extraction
        >>> @router.put("/agents/{agent_id}")
        >>> @audit_log(
        ...     action=AuditAction.UPDATE,
        ...     resource_type="agent",
        ...     extract_resource_id=lambda response: response.get("id")
        ... )
        >>> async def update_agent(agent_id: str, agent: AgentUpdate):
        ...     updated_agent = await agent_service.update(agent_id, agent)
        ...     return updated_agent
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute the route handler
            response = await func(*args, **kwargs)

            # Try to get request and db_session from kwargs/args
            request = kwargs.get("request") or next(
                (arg for arg in args if isinstance(arg, Request)), None
            )
            db_session = kwargs.get("db") or kwargs.get("db_session") or next(
                (arg for arg in args if isinstance(arg, AsyncSession)), None
            )

            # Only log if we have both request and db_session
            if request and db_session:
                try:
                    # Extract resource ID
                    resource_id = None
                    if extract_resource_id and response:
                        resource_id = extract_resource_id(response)
                    elif isinstance(response, dict) and "id" in response:
                        resource_id = str(response["id"])

                    # Get user ID from request state
                    user_id = getattr(request.state, "user_id", None)
                    if user_id and isinstance(user_id, str):
                        try:
                            user_id = UUID(user_id)
                        except (ValueError, AttributeError):
                            user_id = None

                    # Get request body
                    request_body = None
                    if hasattr(request, "_body"):
                        try:
                            body_bytes = await request.body()
                            request_body = body_bytes.decode("utf-8")
                        except Exception:
                            pass

                    # Create audit logger and log
                    audit_logger = AuditLogger(db_session, request)
                    await audit_logger.log(
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        user_id=user_id,
                        request_body=request_body,
                    )
                except Exception as e:
                    # Log error but don't fail the request
                    logger.error(
                        "audit_decorator_failed",
                        error=str(e),
                        action=action,
                        resource_type=resource_type,
                    )

            return response

        return wrapper
    return decorator


# Global audit logger factory
def get_audit_logger(
    db_session: AsyncSession,
    request: Optional[Request] = None,
) -> AuditLogger:
    """
    Factory function for creating AuditLogger instances.

    Args:
        db_session: SQLAlchemy async session
        request: Optional FastAPI request object

    Returns:
        Configured AuditLogger instance

    Example:
        >>> from fastapi import Depends
        >>> from agent_service.infrastructure.observability.audit import get_audit_logger
        >>>
        >>> @router.post("/custom-action")
        >>> async def custom_action(
        ...     db: AsyncSession = Depends(get_db_session),
        ...     request: Request = None,
        ... ):
        ...     audit_logger = get_audit_logger(db, request)
        ...     await audit_logger.log(
        ...         action=AuditAction.EXECUTE,
        ...         resource_type="custom",
        ...         resource_id="custom-123"
        ...     )
        ...     return {"status": "success"}
    """
    return AuditLogger(db_session, request)
