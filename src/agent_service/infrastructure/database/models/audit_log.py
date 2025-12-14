"""
SQLAlchemy model for audit logging.

This module defines the database schema for comprehensive audit logging with support for:
- Action tracking (CREATE, READ, UPDATE, DELETE, EXECUTE, LOGIN, LOGOUT, FAILED_AUTH)
- Resource identification and tracking
- Request context capture (IP, user agent, request details)
- Change tracking with diffs for UPDATE operations
- Flexible metadata storage
- Performance-optimized indexes
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy import Column, String, Integer, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

from agent_service.infrastructure.database.base_model import BaseModel


class AuditAction(str, Enum):
    """
    Audit action types for comprehensive activity tracking.

    These action types cover all major operations in the system:
    - Data operations: CREATE, READ, UPDATE, DELETE
    - Execution: EXECUTE (for agent/tool execution)
    - Authentication: LOGIN, LOGOUT, FAILED_AUTH
    """
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    EXECUTE = "EXECUTE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    FAILED_AUTH = "FAILED_AUTH"


class AuditLog(BaseModel, table=True):
    """
    Audit log model for comprehensive security and compliance tracking.

    This model captures all significant actions in the system, providing:
    - Complete audit trail for compliance and security
    - Request correlation via request_id
    - Change tracking for UPDATE operations
    - User and resource identification
    - Request context (IP, user agent, HTTP details)
    - Flexible metadata storage for additional context

    Attributes:
        id: Unique identifier (UUID)
        timestamp: When the action occurred (timezone-aware)
        user_id: UUID of the user who performed the action (nullable for anonymous)
        action: Type of action performed (CREATE, READ, UPDATE, DELETE, etc.)
        resource_type: Type of resource affected (user, agent, tool, api_key, etc.)
        resource_id: Identifier of the specific resource (nullable for list operations)
        ip_address: IP address of the client
        user_agent: Browser/client user agent string
        request_id: UUID for correlating related audit entries
        request_path: HTTP request path
        request_method: HTTP method (GET, POST, PUT, DELETE, etc.)
        request_body: Request body (optional, can be encrypted for sensitive operations)
        response_status: HTTP response status code
        changes: JSONB field containing before/after diff for UPDATE operations
        metadata: JSONB field for additional context and custom data
        created_at: Timestamp when record was created (inherited from BaseModel)
        updated_at: Timestamp when record was last updated (inherited from BaseModel)

    Indexes:
        - timestamp: Fast queries by time range
        - user_id: Fast queries by user
        - action: Fast queries by action type
        - resource_type: Fast queries by resource
        - request_id: Fast correlation of related audit entries
        - Composite indexes for common query patterns

    Example:
        >>> audit = AuditLog(
        ...     user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
        ...     action=AuditAction.UPDATE,
        ...     resource_type="agent",
        ...     resource_id="agent-123",
        ...     ip_address="192.168.1.1",
        ...     user_agent="Mozilla/5.0...",
        ...     request_id=UUID("123e4567-e89b-12d3-a456-426614174001"),
        ...     request_path="/api/v1/agents/agent-123",
        ...     request_method="PUT",
        ...     response_status=200,
        ...     changes={"name": {"old": "Old Name", "new": "New Name"}},
        ...     metadata={"reason": "User requested update"}
        ... )
    """

    __tablename__ = "audit_logs"

    # Timestamp (indexed for time-based queries)
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        index=True,
        description="Timestamp when the action occurred (UTC)",
        sa_column_kwargs={"comment": "When the audited action occurred"}
    )

    # User identification (nullable for anonymous actions)
    user_id: Optional[UUID] = Field(
        default=None,
        nullable=True,
        index=True,
        description="UUID of the user who performed the action (null for anonymous)",
        sa_column_kwargs={"comment": "User who performed the action, null for system/anonymous"}
    )

    # Action type
    action: str = Field(
        nullable=False,
        max_length=50,
        index=True,
        description="Type of action performed (CREATE, READ, UPDATE, DELETE, etc.)",
        sa_column_kwargs={"comment": "Action type: CREATE, READ, UPDATE, DELETE, EXECUTE, LOGIN, LOGOUT, FAILED_AUTH"}
    )

    # Resource identification
    resource_type: str = Field(
        nullable=False,
        max_length=100,
        index=True,
        description="Type of resource affected (user, agent, tool, api_key, etc.)",
        sa_column_kwargs={"comment": "Resource type: user, agent, tool, api_key, etc."}
    )

    resource_id: Optional[str] = Field(
        default=None,
        nullable=True,
        max_length=255,
        description="Identifier of the specific resource (null for list operations)",
        sa_column_kwargs={"comment": "Resource identifier, null for list/bulk operations"}
    )

    # Request context
    ip_address: str = Field(
        nullable=False,
        max_length=45,  # IPv6 max length
        description="IP address of the client",
        sa_column_kwargs={"comment": "Client IP address (IPv4 or IPv6)"}
    )

    user_agent: str = Field(
        nullable=False,
        max_length=500,
        description="Browser/client user agent string",
        sa_column_kwargs={"comment": "Client user agent string"}
    )

    # Request correlation
    request_id: UUID = Field(
        nullable=False,
        index=True,
        description="UUID for correlating related audit entries",
        sa_column_kwargs={"comment": "Request ID for correlating related audit entries"}
    )

    # HTTP request details
    request_path: str = Field(
        nullable=False,
        max_length=500,
        description="HTTP request path",
        sa_column_kwargs={"comment": "HTTP request path"}
    )

    request_method: str = Field(
        nullable=False,
        max_length=10,
        description="HTTP method (GET, POST, PUT, DELETE, etc.)",
        sa_column_kwargs={"comment": "HTTP method: GET, POST, PUT, DELETE, PATCH, etc."}
    )

    request_body: Optional[str] = Field(
        default=None,
        nullable=True,
        sa_column=Column(Text),
        description="Request body (optional, can be encrypted for sensitive operations)",
        sa_column_kwargs={"comment": "Request body, may be encrypted or redacted for sensitive data"}
    )

    # Response
    response_status: int = Field(
        nullable=False,
        sa_column=Column(Integer),
        description="HTTP response status code",
        sa_column_kwargs={"comment": "HTTP response status code"}
    )

    # Change tracking (for UPDATE operations)
    changes: Optional[Dict[str, Any]] = Field(
        default=None,
        nullable=True,
        sa_column=Column(JSONB),
        description="JSONB field containing before/after diff for UPDATE operations",
        sa_column_kwargs={"comment": "Before/after diff for UPDATE operations: {field: {old: value, new: value}}"}
    )

    # Additional metadata
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        nullable=True,
        sa_column=Column(JSONB),
        description="JSONB field for additional context and custom data",
        sa_column_kwargs={"comment": "Additional context and metadata for the audit entry"}
    )

    # Indexes for performance optimization
    __table_args__ = (
        # Individual column indexes (already defined via index=True above)
        # Composite indexes for common query patterns
        Index('ix_audit_logs_user_action', 'user_id', 'action'),
        Index('ix_audit_logs_resource', 'resource_type', 'resource_id'),
        Index('ix_audit_logs_timestamp_action', 'timestamp', 'action'),
        Index('ix_audit_logs_timestamp_user', 'timestamp', 'user_id'),
        Index('ix_audit_logs_timestamp_resource', 'timestamp', 'resource_type'),
    )

    def __repr__(self) -> str:
        """String representation of the audit log entry."""
        return (
            f"AuditLog(id={self.id}, "
            f"timestamp={self.timestamp.isoformat()}, "
            f"user_id={self.user_id}, "
            f"action={self.action}, "
            f"resource_type={self.resource_type}, "
            f"resource_id={self.resource_id})"
        )
