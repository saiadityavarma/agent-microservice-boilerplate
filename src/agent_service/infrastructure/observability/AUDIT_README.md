# Audit Logging System

Comprehensive audit logging system for security, compliance, and activity tracking.

## Overview

The audit logging system provides:
- Complete audit trail for all significant actions
- Request correlation via request_id
- Change tracking for UPDATE operations
- User and resource identification
- Request context capture (IP, user agent, HTTP details)
- Flexible metadata storage
- Admin-only query endpoints with filtering

## Components

### 1. Database Model

**Location**: `src/agent_service/infrastructure/database/models/audit_log.py`

**Key Features**:
- UUID primary key
- Timezone-aware timestamps
- Action types: CREATE, READ, UPDATE, DELETE, EXECUTE, LOGIN, LOGOUT, FAILED_AUTH
- Resource identification (type and ID)
- Request context (IP, user agent, request details)
- JSONB fields for changes and metadata
- Performance-optimized indexes

**Example Model**:
```python
from agent_service.infrastructure.database.models.audit_log import AuditLog, AuditAction

audit = AuditLog(
    user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
    action=AuditAction.UPDATE,
    resource_type="agent",
    resource_id="agent-123",
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0...",
    request_id=UUID("123e4567-e89b-12d3-a456-426614174001"),
    request_path="/api/v1/agents/agent-123",
    request_method="PUT",
    response_status=200,
    changes={"name": {"old": "Old Name", "new": "New Name"}},
    metadata={"reason": "User requested update"}
)
```

### 2. Audit Service

**Location**: `src/agent_service/infrastructure/observability/audit.py`

**Key Classes**:
- `AuditLogger`: Service for creating audit log entries
- `audit_log`: Decorator for automatic route auditing
- `get_audit_logger`: Factory function for creating logger instances

**Usage Examples**:

#### Programmatic Logging

```python
from agent_service.infrastructure.observability.audit import get_audit_logger
from agent_service.infrastructure.database.models.audit_log import AuditAction

# In your route handler
audit_logger = get_audit_logger(db, request)
await audit_logger.log(
    action=AuditAction.UPDATE,
    resource_type="agent",
    resource_id="agent-123",
    changes={"name": {"old": "Old", "new": "New"}},
    metadata={"reason": "User requested"}
)
```

#### Authentication Events

```python
# Successful login
await audit_logger.log_auth_event(
    event_type=AuditAction.LOGIN,
    user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
    success=True
)

# Failed authentication
await audit_logger.log_auth_event(
    event_type=AuditAction.FAILED_AUTH,
    user_id=None,
    success=False,
    reason="Invalid credentials"
)
```

#### Data Access Logging

```python
await audit_logger.log_data_access(
    resource_type="user",
    resource_id="user-123",
    user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
    metadata={"accessed_fields": ["email", "name"]}
)
```

#### Decorator for Routes

```python
from agent_service.infrastructure.observability.audit import audit_log
from agent_service.infrastructure.database.models.audit_log import AuditAction

@router.post("/agents")
@audit_log(action=AuditAction.CREATE, resource_type="agent")
async def create_agent(
    agent: AgentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    created_agent = await agent_service.create(agent)
    return created_agent

# With resource ID extraction
@router.put("/agents/{agent_id}")
@audit_log(
    action=AuditAction.UPDATE,
    resource_type="agent",
    extract_resource_id=lambda response: response.get("id")
)
async def update_agent(
    agent_id: str,
    agent: AgentUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    updated_agent = await agent_service.update(agent_id, agent)
    return updated_agent
```

### 3. Admin API Routes

**Location**: `src/agent_service/api/routes/audit.py`

**Endpoints**:

#### Query Audit Logs
```
GET /api/v1/admin/audit
```

**Query Parameters**:
- `user_id`: Filter by user ID (UUID)
- `action`: Filter by action type (CREATE, READ, UPDATE, DELETE, etc.)
- `resource_type`: Filter by resource type (user, agent, tool, etc.)
- `resource_id`: Filter by resource ID
- `request_id`: Filter by request ID (UUID)
- `ip_address`: Filter by IP address
- `start_date`: Filter by start date (ISO 8601)
- `end_date`: Filter by end date (ISO 8601)
- `response_status`: Filter by HTTP status code
- `limit`: Number of items to return (1-1000, default 100)
- `offset`: Number of items to skip (default 0)

**Example**:
```bash
curl -H "Authorization: Bearer <token>" \
  "https://api.example.com/api/v1/admin/audit?user_id=123e4567-e89b-12d3-a456-426614174000&action=CREATE&limit=50"
```

#### Get Audit Log by ID
```
GET /api/v1/admin/audit/{audit_id}
```

**Example**:
```bash
curl -H "Authorization: Bearer <token>" \
  "https://api.example.com/api/v1/admin/audit/123e4567-e89b-12d3-a456-426614174000"
```

#### Get Audit Statistics
```
GET /api/v1/admin/audit/stats/summary
```

**Query Parameters**:
- `start_date`: Filter by start date (ISO 8601)
- `end_date`: Filter by end date (ISO 8601)

**Example**:
```bash
curl -H "Authorization: Bearer <token>" \
  "https://api.example.com/api/v1/admin/audit/stats/summary?start_date=2024-01-01&end_date=2024-01-31"
```

### 4. Configuration

**Location**: `src/agent_service/config/settings.py`

**Settings**:
```python
# Audit Logging
audit_logging_enabled: bool = True  # Enable/disable audit logging
audit_log_retention_days: int = 90  # Retention period for audit logs
```

**Environment Variables**:
```bash
AUDIT_LOGGING_ENABLED=true
AUDIT_LOG_RETENTION_DAYS=90
```

## Database Migration

**Location**: `alembic/versions/20241213_0001_create_audit_logs_table.py`

**Running the Migration**:

```bash
# Upgrade to latest
alembic upgrade head

# Downgrade
alembic downgrade -1

# Check current revision
alembic current

# View migration history
alembic history
```

## Security Features

### Authorization
- All admin endpoints require ADMIN or SUPER_ADMIN role
- Uses RBAC (Role-Based Access Control) for authorization
- Proper HTTP 403 responses for unauthorized access

### Data Protection
- Request bodies can be redacted (controlled by `log_include_request_body`)
- PII masking support (controlled by `log_pii_masking_enabled`)
- Request body truncation (controlled by `log_max_body_length`)
- Optional encryption for sensitive request bodies

### Privacy
- User ID is nullable for anonymous operations
- IP addresses captured for security auditing
- User agent strings stored for forensics

## Performance Considerations

### Indexes
The following indexes are created for optimal query performance:
- `timestamp` (for time-range queries)
- `user_id` (for user activity queries)
- `action` (for action-specific queries)
- `resource_type` (for resource queries)
- `request_id` (for request correlation)
- Composite indexes for common query patterns

### Retention
Configure `audit_log_retention_days` to automatically clean up old audit logs. Implement a scheduled task to delete logs older than the retention period:

```python
from datetime import datetime, timedelta
from agent_service.config.settings import get_settings

settings = get_settings()
cutoff_date = datetime.utcnow() - timedelta(days=settings.audit_log_retention_days)

# Delete old audit logs
await db.execute(
    delete(AuditLog).where(AuditLog.timestamp < cutoff_date)
)
await db.commit()
```

## Integration Example

### FastAPI Application Setup

```python
from fastapi import FastAPI
from agent_service.api.routes import audit
from agent_service.infrastructure.database.connection import get_db_session

app = FastAPI()

# Override database session dependency
audit.get_db_session = get_db_session

# Include the router
app.include_router(audit.router)
```

### Using in Routes

```python
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from agent_service.infrastructure.observability.audit import audit_log, get_audit_logger
from agent_service.infrastructure.database.models.audit_log import AuditAction

router = APIRouter()

# Automatic auditing with decorator
@router.post("/resources")
@audit_log(action=AuditAction.CREATE, resource_type="resource")
async def create_resource(
    resource: ResourceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    # Your logic here
    return created_resource

# Manual auditing for complex scenarios
@router.put("/resources/{resource_id}")
async def update_resource(
    resource_id: str,
    resource: ResourceUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    # Get old resource state
    old_resource = await get_resource(resource_id)

    # Update resource
    new_resource = await update_resource_logic(resource_id, resource)

    # Calculate changes
    changes = {
        "name": {
            "old": old_resource.name,
            "new": new_resource.name
        }
    }

    # Manual audit logging
    audit_logger = get_audit_logger(db, request)
    await audit_logger.log(
        action=AuditAction.UPDATE,
        resource_type="resource",
        resource_id=resource_id,
        changes=changes,
        metadata={"updated_by": "api"}
    )

    return new_resource
```

## Common Use Cases

### 1. Track All User Actions
```python
# Query all actions by a specific user
GET /api/v1/admin/audit?user_id=<uuid>
```

### 2. Investigate Security Incident
```python
# Find all failed authentication attempts from an IP
GET /api/v1/admin/audit?action=FAILED_AUTH&ip_address=192.168.1.100
```

### 3. Compliance Reporting
```python
# Get all data access events for a time period
GET /api/v1/admin/audit?action=READ&start_date=2024-01-01&end_date=2024-01-31
```

### 4. Debug Request Flow
```python
# Find all audit entries for a specific request
GET /api/v1/admin/audit?request_id=<uuid>
```

### 5. Monitor Resource Changes
```python
# Track all updates to a specific resource
GET /api/v1/admin/audit?action=UPDATE&resource_type=agent&resource_id=agent-123
```

## Troubleshooting

### Audit Logs Not Being Created

1. Check if audit logging is enabled:
```python
from agent_service.config.settings import get_settings
print(get_settings().audit_logging_enabled)
```

2. Verify database session is properly injected in routes

3. Check for errors in application logs

### Performance Issues

1. Review and optimize indexes
2. Implement audit log archival/retention
3. Consider partitioning the audit_logs table by timestamp
4. Use read replicas for audit queries

### Missing User Context

Ensure request middleware is setting user_id in request.state:
```python
request.state.user_id = user.id
```

## Best Practices

1. **Always audit sensitive operations**: LOGIN, LOGOUT, data access, permission changes
2. **Include meaningful metadata**: Add context that will help future investigations
3. **Track changes for updates**: Always include before/after diffs
4. **Use request_id for correlation**: Group related audit entries
5. **Implement retention policies**: Don't keep logs forever
6. **Monitor audit log creation**: Alert on audit logging failures
7. **Regular audits of the audit system**: Ensure the system itself is working correctly
8. **Secure audit logs**: Audit logs should be immutable and protected

## Future Enhancements

Potential improvements:
- Real-time audit event streaming
- Automated anomaly detection
- Audit log encryption at rest
- Export to SIEM systems
- Audit log signing for tamper detection
- Automated compliance report generation
