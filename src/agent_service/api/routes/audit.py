"""
Audit log API routes.

This module provides admin-only endpoints for querying and managing audit logs:

Admin Routes:
    - GET /api/v1/admin/audit - Query audit logs with filters

Security:
    - All endpoints require ADMIN or SUPER_ADMIN role
    - Comprehensive filtering and pagination
    - OpenAPI documentation included

Example Usage:
    GET /api/v1/admin/audit?user_id=<uuid>&action=CREATE&limit=50&offset=0
    GET /api/v1/admin/audit?resource_type=agent&start_date=2024-01-01&end_date=2024-01-31
    GET /api/v1/admin/audit?request_id=<uuid>
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from pydantic import BaseModel, Field

from agent_service.auth.dependencies import get_current_user
from agent_service.auth.schemas import UserInfo
from agent_service.auth.rbac.decorators import RoleRequired
from agent_service.auth.rbac.roles import Role
from agent_service.infrastructure.database.models.audit_log import AuditLog, AuditAction


# Router without prefix (will be versioned and prefixed when mounted)
router = APIRouter(tags=["Audit Logs (Admin)"])


# ============================================================================
# Request/Response Models
# ============================================================================


class AuditLogResponse(BaseModel):
    """Response model for a single audit log entry."""

    model_config = {"from_attributes": True, "str_strip_whitespace": True}

    id: UUID = Field(..., description="Unique identifier for the audit log entry")
    timestamp: datetime = Field(..., description="When the action occurred")
    user_id: Optional[UUID] = Field(None, description="User who performed the action")
    action: str = Field(..., description="Action type (CREATE, READ, UPDATE, DELETE, etc.)")
    resource_type: str = Field(..., description="Type of resource (user, agent, tool, etc.)")
    resource_id: Optional[str] = Field(None, description="ID of the specific resource")
    ip_address: str = Field(..., description="IP address of the client")
    user_agent: str = Field(..., description="Client user agent string")
    request_id: UUID = Field(..., description="Request correlation ID")
    request_path: str = Field(..., description="HTTP request path")
    request_method: str = Field(..., description="HTTP method")
    request_body: Optional[str] = Field(None, description="Request body (may be redacted)")
    response_status: int = Field(..., description="HTTP response status code")
    changes: Optional[dict] = Field(None, description="Changes made (for UPDATE operations)")
    metadata: Optional[dict] = Field(None, description="Additional metadata")
    created_at: datetime = Field(..., description="When the record was created")
    updated_at: datetime = Field(..., description="When the record was last updated")


class AuditLogListResponse(BaseModel):
    """Response model for paginated audit log list."""

    model_config = {"str_strip_whitespace": True}

    items: List[AuditLogResponse] = Field(..., description="List of audit log entries")
    total: int = Field(..., description="Total number of matching entries")
    limit: int = Field(..., description="Number of items per page")
    offset: int = Field(..., description="Offset for pagination")
    has_more: bool = Field(..., description="Whether there are more results")


class AuditLogStatsResponse(BaseModel):
    """Response model for audit log statistics."""

    model_config = {"str_strip_whitespace": True}

    total_events: int = Field(..., description="Total number of audit events")
    events_by_action: dict[str, int] = Field(..., description="Count of events by action type")
    events_by_resource: dict[str, int] = Field(..., description="Count of events by resource type")
    unique_users: int = Field(..., description="Number of unique users")
    date_range: dict[str, Optional[datetime]] = Field(..., description="Date range of events")


# ============================================================================
# Dependencies
# ============================================================================


# Placeholder for database session dependency
# This should be overridden by the application
async def get_db_session() -> AsyncSession:
    """
    Database session dependency.

    This is a placeholder that should be overridden by the application.
    See agent_service.infrastructure.database.connection for implementation.

    Raises:
        NotImplementedError: If not overridden by the application

    Example:
        >>> from agent_service.api.routes import audit
        >>> from your_app.database import get_session
        >>>
        >>> # Override the dependency
        >>> audit.get_db_session = get_session
    """
    raise NotImplementedError(
        "Database session dependency not configured. "
        "Please override get_db_session in your application startup."
    )


# ADMIN role requirement dependency
require_admin = RoleRequired([Role.ADMIN, Role.SUPER_ADMIN], require_all=False)


# ============================================================================
# Route Handlers
# ============================================================================


@router.get(
    "",
    response_model=AuditLogListResponse,
    summary="Query audit logs",
    description="""
    Query audit logs with comprehensive filtering options.

    Requires ADMIN or SUPER_ADMIN role.

    Filtering options:
    - By user: user_id
    - By action: action (CREATE, READ, UPDATE, DELETE, etc.)
    - By resource: resource_type, resource_id
    - By time: start_date, end_date
    - By request: request_id, ip_address
    - By status: response_status

    Results are paginated using limit and offset parameters.
    """,
)
async def get_audit_logs(
    # Filters
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    request_id: Optional[UUID] = Query(None, description="Filter by request ID"),
    ip_address: Optional[str] = Query(None, description="Filter by IP address"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date (inclusive)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (inclusive)"),
    response_status: Optional[int] = Query(None, description="Filter by HTTP status code"),
    # Pagination
    limit: int = Query(100, ge=1, le=1000, description="Number of items to return (1-1000)"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    # Dependencies
    db: AsyncSession = Depends(get_db_session),
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_admin),
) -> AuditLogListResponse:
    """
    Query audit logs with filtering and pagination.

    Args:
        user_id: Filter by user ID
        action: Filter by action type
        resource_type: Filter by resource type
        resource_id: Filter by resource ID
        request_id: Filter by request ID
        ip_address: Filter by IP address
        start_date: Filter by start date (inclusive)
        end_date: Filter by end date (inclusive)
        response_status: Filter by HTTP status code
        limit: Number of items to return (1-1000)
        offset: Number of items to skip
        db: Database session
        user: Current authenticated user
        _: Admin role check

    Returns:
        Paginated list of audit log entries

    Example:
        GET /api/v1/admin/audit?user_id=123e4567-e89b-12d3-a456-426614174000&action=CREATE
    """
    # Build filter conditions
    conditions = []

    if user_id:
        conditions.append(AuditLog.user_id == user_id)
    if action:
        conditions.append(AuditLog.action == action.upper())
    if resource_type:
        conditions.append(AuditLog.resource_type == resource_type)
    if resource_id:
        conditions.append(AuditLog.resource_id == resource_id)
    if request_id:
        conditions.append(AuditLog.request_id == request_id)
    if ip_address:
        conditions.append(AuditLog.ip_address == ip_address)
    if start_date:
        conditions.append(AuditLog.timestamp >= start_date)
    if end_date:
        conditions.append(AuditLog.timestamp <= end_date)
    if response_status:
        conditions.append(AuditLog.response_status == response_status)

    # Build query
    query = select(AuditLog)
    if conditions:
        query = query.where(and_(*conditions))

    # Count total matching entries
    count_query = select(func.count()).select_from(AuditLog)
    if conditions:
        count_query = count_query.where(and_(*conditions))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply ordering and pagination
    query = query.order_by(AuditLog.timestamp.desc())
    query = query.limit(limit).offset(offset)

    # Execute query
    result = await db.execute(query)
    audit_logs = result.scalars().all()

    # Convert to response models
    items = [AuditLogResponse.model_validate(log) for log in audit_logs]

    return AuditLogListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


@router.get(
    "/{audit_id}",
    response_model=AuditLogResponse,
    summary="Get audit log by ID",
    description="Retrieve a specific audit log entry by its ID. Requires ADMIN or SUPER_ADMIN role.",
)
async def get_audit_log(
    audit_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_admin),
) -> AuditLogResponse:
    """
    Get a specific audit log entry by ID.

    Args:
        audit_id: ID of the audit log entry
        db: Database session
        user: Current authenticated user
        _: Admin role check

    Returns:
        Audit log entry

    Raises:
        HTTPException: 404 if audit log not found

    Example:
        GET /api/v1/admin/audit/123e4567-e89b-12d3-a456-426614174000
    """
    query = select(AuditLog).where(AuditLog.id == audit_id)
    result = await db.execute(query)
    audit_log = result.scalar_one_or_none()

    if not audit_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log with ID {audit_id} not found",
        )

    return AuditLogResponse.model_validate(audit_log)


@router.get(
    "/stats/summary",
    response_model=AuditLogStatsResponse,
    summary="Get audit log statistics",
    description="""
    Get statistical summary of audit logs.

    Requires ADMIN or SUPER_ADMIN role.

    Returns:
    - Total number of events
    - Events by action type
    - Events by resource type
    - Number of unique users
    - Date range of events
    """,
)
async def get_audit_stats(
    start_date: Optional[datetime] = Query(None, description="Filter by start date (inclusive)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (inclusive)"),
    db: AsyncSession = Depends(get_db_session),
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_admin),
) -> AuditLogStatsResponse:
    """
    Get audit log statistics.

    Args:
        start_date: Filter by start date (inclusive)
        end_date: Filter by end date (inclusive)
        db: Database session
        user: Current authenticated user
        _: Admin role check

    Returns:
        Statistics about audit log entries

    Example:
        GET /api/v1/admin/audit/stats/summary?start_date=2024-01-01&end_date=2024-01-31
    """
    # Build filter conditions
    conditions = []
    if start_date:
        conditions.append(AuditLog.timestamp >= start_date)
    if end_date:
        conditions.append(AuditLog.timestamp <= end_date)

    # Total events
    count_query = select(func.count()).select_from(AuditLog)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total_events = total_result.scalar() or 0

    # Events by action
    action_query = select(AuditLog.action, func.count()).group_by(AuditLog.action)
    if conditions:
        action_query = action_query.where(and_(*conditions))
    action_result = await db.execute(action_query)
    events_by_action = {action: count for action, count in action_result.all()}

    # Events by resource type
    resource_query = select(AuditLog.resource_type, func.count()).group_by(AuditLog.resource_type)
    if conditions:
        resource_query = resource_query.where(and_(*conditions))
    resource_result = await db.execute(resource_query)
    events_by_resource = {resource: count for resource, count in resource_result.all()}

    # Unique users
    users_query = select(func.count(func.distinct(AuditLog.user_id))).select_from(AuditLog)
    if conditions:
        users_query = users_query.where(and_(*conditions))
    users_result = await db.execute(users_query)
    unique_users = users_result.scalar() or 0

    # Date range
    date_query = select(
        func.min(AuditLog.timestamp),
        func.max(AuditLog.timestamp)
    )
    if conditions:
        date_query = date_query.where(and_(*conditions))
    date_result = await db.execute(date_query)
    min_date, max_date = date_result.one()

    return AuditLogStatsResponse(
        total_events=total_events,
        events_by_action=events_by_action,
        events_by_resource=events_by_resource,
        unique_users=unique_users,
        date_range={"start": min_date, "end": max_date},
    )
