# Database Quick Reference Card

## Setup

```bash
# 1. Configure environment
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db"

# 2. Run migrations
alembic upgrade head

# 3. Verify setup
python scripts/verify_database.py
```

## Configuration Settings

```python
# .env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db
DB_POOL_SIZE=5              # Default connection pool size
DB_MAX_OVERFLOW=10          # Max connections beyond pool
DB_POOL_TIMEOUT=30          # Connection timeout (seconds)
DB_POOL_RECYCLE=3600        # Recycle after 1 hour
DB_ECHO_SQL=false           # Log SQL queries
```

## Models Quick Reference

### User
```python
from agent_service.infrastructure.database.models import User, AuthProvider

user = User(
    email="user@example.com",
    name="John Doe",
    provider=AuthProvider.LOCAL,  # or AZURE_AD, AWS_COGNITO
    provider_user_id="john123",
    roles=["user", "admin"],
    groups=["engineering"],
    is_active=True
)

# Methods
user.has_role("admin")
user.add_role("developer")
user.is_in_group("engineering")
user.activate() / user.deactivate()
user.soft_delete()
```

### Session
```python
from agent_service.infrastructure.database.models import Session, SessionStatus

session = Session(
    user_id=user.id,
    agent_id="code_assistant",
    title="Debug Session",
    status=SessionStatus.ACTIVE
)

# Methods
session.add_message("user", "Hello")
session.update_context(language="python")
session.mark_completed()
session.mark_failed("error message")
```

### API Key
```python
from agent_service.auth.models.api_key import APIKey

key = APIKey(
    user_id=user.id,
    name="Production API",
    key_hash="...",
    key_prefix="sk_live",
    scopes=["read", "write"],
    rate_limit_tier="pro"
)

# Methods
key.has_scope("write")
key.update_last_used()
key.soft_delete()
```

## Database Operations

### Create
```python
async with db.session() as session:
    user = User(email="test@example.com", ...)
    session.add(user)
    # Auto-commits on exit
```

### Read
```python
from sqlalchemy import select

async with db.session() as session:
    result = await session.execute(
        select(User).where(User.email == "test@example.com")
    )
    user = result.scalar_one_or_none()
```

### Update
```python
async with db.session() as session:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    user.name = "New Name"
    # Auto-commits on exit
```

### Delete (Soft)
```python
async with db.session() as session:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    user.soft_delete()
```

## Common Queries

### Filter Active Users
```python
result = await session.execute(
    select(User)
    .where(User.is_active == True)
    .where(User.deleted_at.is_(None))
)
```

### Get User Sessions
```python
result = await session.execute(
    select(Session)
    .where(Session.user_id == user_id)
    .where(Session.status == SessionStatus.ACTIVE)
    .order_by(Session.last_activity_at.desc())
)
```

### Pagination
```python
result = await session.execute(
    select(User)
    .offset((page - 1) * page_size)
    .limit(page_size)
)
```

## Monitoring

### Pool Statistics
```python
stats = db.get_pool_stats()
# Returns: pool_size, max_overflow, checked_in, checked_out, overflow, total
```

### Health Check
```python
is_healthy = await db.health_check()
```

### HTTP Endpoint
```bash
curl http://localhost:8000/health
```

## Migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# Check status
alembic current
alembic history
```

## Migration Chain

```
20241213_0001 -> audit_logs table
20241213_0002 -> users table
20241213_0003 -> api_keys table
20241213_0004 -> sessions table
```

## Troubleshooting

### Pool Exhausted
```env
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
```

### Stale Connections
```env
DB_POOL_RECYCLE=1800  # 30 minutes
```

### Debug SQL
```env
DB_ECHO_SQL=true
```

### Migration Issues
```bash
alembic current  # Check version
alembic upgrade head  # Apply all migrations
```

## Files Reference

### Models
- `/src/agent_service/infrastructure/database/models/user.py`
- `/src/agent_service/infrastructure/database/models/session.py`
- `/src/agent_service/auth/models/api_key.py`
- `/src/agent_service/infrastructure/database/models/audit_log.py`

### Migrations
- `/alembic/versions/20241213_0001_create_audit_logs_table.py`
- `/alembic/versions/20241213_0002_create_users_table.py`
- `/alembic/versions/20241213_0003_create_api_keys_table.py`
- `/alembic/versions/20241213_0004_create_sessions_table.py`

### Configuration
- `/src/agent_service/config/settings.py` - Database settings
- `/src/agent_service/infrastructure/database/connection.py` - Connection manager
- `/alembic/env.py` - Alembic configuration

### Documentation
- `/DATABASE_ENHANCEMENT_SUMMARY.md` - Complete implementation details
- `/docs/database_guide.md` - Developer guide with examples
- `/scripts/verify_database.py` - Verification script
