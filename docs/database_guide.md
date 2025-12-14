# Database Developer Guide

## Quick Start

### 1. Configure Database Connection
```bash
# .env file
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/agentdb
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
```

### 2. Run Migrations
```bash
# Apply all migrations
alembic upgrade head

# Check current version
alembic current
```

### 3. Use Database in Code
```python
from agent_service.infrastructure.database import db
from agent_service.infrastructure.database.models import User, Session

# In async endpoint
async with db.session() as session:
    # Query users
    result = await session.execute(
        select(User).where(User.email == "user@example.com")
    )
    user = result.scalar_one_or_none()
```

## Models Reference

### User Model

```python
from agent_service.infrastructure.database.models import User, AuthProvider

# Create user
user = User(
    email="john@example.com",
    name="John Doe",
    provider=AuthProvider.AZURE_AD,
    provider_user_id="azure-123",
    roles=["user", "developer"],
    groups=["engineering"],
    is_active=True
)

# Check permissions
if user.has_role("admin"):
    # Admin-only logic
    pass

if user.has_any_role(["admin", "developer"]):
    # Developer or admin logic
    pass

# Manage roles
user.add_role("tester")
user.remove_role("developer")

# Deactivate account
user.deactivate()
```

### Session Model

```python
from agent_service.infrastructure.database.models import Session, SessionStatus

# Create session
session = Session(
    user_id=user.id,
    agent_id="code_assistant",
    title="Debug Python Script",
    status=SessionStatus.ACTIVE
)

# Add messages
session.add_message("user", "Help me debug this code")
session.add_message("assistant", "I'll help you with that", tool_calls=[...])

# Update context
session.update_context(
    language="python",
    file_path="/path/to/script.py"
)

# Track completion
session.mark_completed()

# Or handle failure
session.mark_failed("Agent timeout after 30s")
```

### API Key Model

```python
from agent_service.auth.models.api_key import APIKey

# Create API key
api_key = APIKey(
    user_id=user.id,
    name="Production API",
    key_hash="...",  # SHA256 hash
    key_prefix="sk_live",
    scopes=["read", "write"],
    rate_limit_tier="pro"
)

# Check permissions
if api_key.has_scope("write"):
    # Write operation
    pass

# Track usage
api_key.update_last_used()
```

## Common Patterns

### Creating Records

```python
from agent_service.infrastructure.database import db
from agent_service.infrastructure.database.models import User

async def create_user(email: str, name: str):
    async with db.session() as session:
        user = User(
            email=email,
            name=name,
            provider="local",
            provider_user_id=email,
            roles=["user"]
        )
        session.add(user)
        # Auto-commits on context exit
        return user
```

### Querying Records

```python
from sqlalchemy import select

async def get_user_by_email(email: str):
    async with db.session() as session:
        result = await session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

async def get_active_users():
    async with db.session() as session:
        result = await session.execute(
            select(User)
            .where(User.is_active == True)
            .where(User.deleted_at.is_(None))
        )
        return result.scalars().all()
```

### Updating Records

```python
async def update_user_roles(user_id: UUID, new_roles: list[str]):
    async with db.session() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one()
        user.roles = new_roles
        # Auto-commits on context exit
        return user
```

### Soft Deletion

```python
async def delete_user(user_id: UUID):
    async with db.session() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one()
        user.soft_delete()  # Sets deleted_at
        # Auto-commits on context exit
```

### Complex Queries

```python
from sqlalchemy import and_, or_

async def get_user_sessions(user_id: UUID, status: str = None):
    async with db.session() as session:
        query = select(Session).where(Session.user_id == user_id)

        if status:
            query = query.where(Session.status == status)

        # Active sessions only (not deleted)
        query = query.where(Session.deleted_at.is_(None))

        # Order by recent activity
        query = query.order_by(Session.last_activity_at.desc())

        result = await session.execute(query)
        return result.scalars().all()
```

## Migration Workflow

### Create New Migration

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "add user preferences"

# Manual migration
alembic revision -m "add custom index"
```

### Migration Template

```python
"""add user preferences

Revision ID: 20241213_0005
Revises: 20241213_0004
Create Date: 2024-12-13 22:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '20241213_0005'
down_revision = '20241213_0004'

def upgrade() -> None:
    op.add_column('users',
        sa.Column('preferences', sa.JSON, nullable=True)
    )

def downgrade() -> None:
    op.drop_column('users', 'preferences')
```

### Apply Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade one version
alembic upgrade +1

# Downgrade one version
alembic downgrade -1

# Go to specific version
alembic upgrade 20241213_0002
```

## Pool Monitoring

### Check Pool Stats

```python
# Get pool statistics
stats = db.get_pool_stats()
print(f"Pool size: {stats['pool_size']}")
print(f"Active connections: {stats['checked_out']}")
print(f"Idle connections: {stats['checked_in']}")
print(f"Overflow connections: {stats['overflow']}")
```

### Health Check

```python
# Programmatic health check
is_healthy = await db.health_check()

# Via HTTP endpoint
# GET /health
{
  "status": "healthy",
  "components": [{
    "name": "database",
    "status": "healthy",
    "latency_ms": 2.5,
    "details": {
      "pool_size": 5,
      "checked_out": 2,
      "checked_in": 3
    }
  }]
}
```

## Transaction Management

### Manual Transaction Control

```python
async def transfer_session(session_id: UUID, new_user_id: UUID):
    async with db.session() as session:
        try:
            # Get session
            result = await session.execute(
                select(Session).where(Session.id == session_id)
            )
            sess = result.scalar_one()

            # Update ownership
            sess.user_id = new_user_id

            # Log transfer in audit
            audit = AuditLog(
                user_id=sess.user_id,
                action="UPDATE",
                resource_type="session",
                resource_id=str(session_id),
                # ... other fields
            )
            session.add(audit)

            # Both updates committed together
        except Exception:
            # Auto-rollback on exception
            raise
```

### Explicit Rollback

```python
async with db.session() as session:
    try:
        # Some operations
        pass
    except ValidationError:
        await session.rollback()
        # Handle validation error
        raise
```

## Performance Tips

### Use Indexes
All models have indexes on common query fields:
- Users: email, provider, is_active
- Sessions: user_id, agent_id, status, last_activity_at
- API Keys: user_id, key_hash

### Eager Loading
```python
from sqlalchemy.orm import selectinload

# Load user with all sessions
result = await session.execute(
    select(User)
    .options(selectinload(User.sessions))
    .where(User.id == user_id)
)
user = result.scalar_one()
```

### Batch Operations
```python
# Insert multiple records efficiently
async with db.session() as session:
    users = [
        User(email=f"user{i}@example.com", ...)
        for i in range(100)
    ]
    session.add_all(users)
```

### Pagination
```python
async def get_sessions_paginated(user_id: UUID, page: int = 1, size: int = 20):
    async with db.session() as session:
        offset = (page - 1) * size

        query = (
            select(Session)
            .where(Session.user_id == user_id)
            .offset(offset)
            .limit(size)
        )

        result = await session.execute(query)
        return result.scalars().all()
```

## Troubleshooting

### Connection Pool Exhausted
```
Error: QueuePool limit of size 5 overflow 10 reached
```

**Solution:** Increase pool size or reduce connection lifetime:
```env
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
```

### Stale Connections
```
Error: server closed the connection unexpectedly
```

**Solution:** Enable pre-ping and reduce recycle time:
```env
DB_POOL_RECYCLE=1800  # 30 minutes
```

### Migration Conflicts
```
Error: Target database is not up to date
```

**Solution:**
```bash
# Check current version
alembic current

# View history
alembic history

# Upgrade to head
alembic upgrade head
```

### Debug SQL Queries
```env
DB_ECHO_SQL=true
```

This will log all SQL queries to console.

## Best Practices

1. **Always use soft delete** for user-facing data (users, sessions, API keys)
2. **Check is_active and deleted_at** in queries
3. **Use transactions** for multi-step operations
4. **Monitor pool stats** in production
5. **Index frequently queried fields**
6. **Use batch operations** for bulk inserts/updates
7. **Paginate large result sets**
8. **Log all mutations** in audit_logs table
9. **Validate data** before database operations
10. **Handle exceptions** gracefully with rollback

## Security Considerations

### Password Hashing
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash password
user.hashed_password = pwd_context.hash(plain_password)

# Verify password
is_valid = pwd_context.verify(plain_password, user.hashed_password)
```

### API Key Generation
```python
import secrets
import hashlib

def generate_api_key():
    # Generate random key
    raw_key = f"sk_live_{secrets.token_urlsafe(32)}"

    # Hash for storage
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    # Return both (only show raw key once)
    return raw_key, key_hash
```

### Audit Logging
```python
from agent_service.infrastructure.database.models import AuditLog, AuditAction

async def log_action(user_id: UUID, action: str, resource: str):
    async with db.session() as session:
        audit = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource,
            timestamp=datetime.utcnow(),
            # ... other fields
        )
        session.add(audit)
```

## Resources

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [FastAPI Database Guide](https://fastapi.tiangolo.com/tutorial/sql-databases/)
