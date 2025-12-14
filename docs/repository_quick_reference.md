# Repository Quick Reference

Quick reference guide for the enhanced BaseRepository features.

## Initialization

```python
from sqlalchemy.ext.asyncio import AsyncSession
from agent_service.infrastructure.database.repositories.base import BaseRepository
from agent_service.infrastructure.database.models.user import User

class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session, enable_query_logging=False)

# Create repository
repo = UserRepository(session)
```

## CRUD Operations

### Create

```python
# Single create
user = User(email="user@example.com", name="User", provider="local", provider_user_id="user")
user = await repo.create(user)

# Bulk create
users = await repo.create_many([
    {"email": "user1@example.com", "name": "User 1", "provider": "local", "provider_user_id": "user1"},
    {"email": "user2@example.com", "name": "User 2", "provider": "local", "provider_user_id": "user2"},
])
```

### Read

```python
# Get by ID
user = await repo.get(user_id)
user = await repo.get(user_id, include_deleted=True)  # Include soft-deleted

# Get many
users = await repo.get_many(skip=0, limit=100)
users = await repo.get_many(is_active=True)  # With filter
users = await repo.get_many(include_deleted=True)  # Include soft-deleted
```

### Update

```python
# Update by ID
user = await repo.update(user_id, name="New Name", is_active=False)

# Bulk update
count = await repo.update_many(
    {"is_active__eq": False},  # Filters
    {"deleted_at": datetime.utcnow()}  # Updates
)
```

### Delete

```python
# Soft delete
deleted = await repo.delete(user_id)

# Hard delete
deleted = await repo.hard_delete(user_id)

# Bulk soft delete
count = await repo.delete_many({"is_active__eq": False})
```

## Filtering

```python
from sqlalchemy import select

query = select(User)
query = repo.apply_filters(query, {
    "is_active__eq": True,                    # Equal
    "name__ne": "Admin",                      # Not equal
    "age__gt": 18,                            # Greater than
    "created_at__gte": datetime(2024, 1, 1),  # Greater than or equal
    "age__lt": 65,                            # Less than
    "created_at__lte": datetime(2024, 12, 31),# Less than or equal
    "email__like": "%@example.com",           # LIKE
    "email__ilike": "%@EXAMPLE.COM",          # Case-insensitive LIKE
    "provider__in": ["azure_ad", "local"],    # IN
    "status__not_in": ["deleted", "banned"],  # NOT IN
    "deleted_at__is_null": True,              # IS NULL
    "deleted_at__is_not_null": True,          # IS NOT NULL
})
```

## Sorting

```python
from sqlalchemy import select

query = select(User)

# Sort ascending
query = repo.apply_sorting(query, "email", "asc")

# Sort descending (default)
query = repo.apply_sorting(query, "created_at", "desc")

# Execute
result = await repo.session.execute(query)
users = result.scalars().all()
```

## Pagination

```python
from sqlalchemy import select

query = select(User).where(User.is_active == True)
result = await repo.paginate(query, page=1, page_size=20)

# Access data
items = result.items          # List of entities
total = result.total          # Total count
page = result.page            # Current page
page_size = result.page_size  # Items per page
total_pages = result.total_pages  # Total pages
has_next = result.has_next    # Has next page
has_prev = result.has_prev    # Has previous page
```

## Transactions

### Context Manager

```python
async with repo.transaction():
    user = await repo.create(user_data)
    # More operations...
    # Commits on success, rolls back on error
```

### Decorator

```python
from agent_service.infrastructure.database.repositories.base import transactional

@transactional
async def create_user_and_profile(repo, user_data, profile_data):
    user = await repo.create(user_data)
    # Create profile...
    return user

# Usage
user = await create_user_and_profile(repo, user_data, profile_data)
```

## Combined Example

```python
from datetime import datetime
from sqlalchemy import select

# Build query with all features
query = select(User)

# 1. Apply filters
filters = {
    "is_active__eq": True,
    "created_at__gte": datetime(2024, 1, 1),
    "email__ilike": "%@example.com",
}
query = repo.apply_filters(query, filters)

# 2. Apply sorting
query = repo.apply_sorting(query, "created_at", "desc")

# 3. Paginate
result = await repo.paginate(query, page=1, page_size=20)

# 4. Use results
for user in result.items:
    print(f"{user.email} - {user.created_at}")
```

## Filter Operators Cheat Sheet

| Operator | SQL | Example |
|----------|-----|---------|
| `eq` | `=` | `{"age__eq": 25}` |
| `ne` | `!=` | `{"status__ne": "banned"}` |
| `gt` | `>` | `{"age__gt": 18}` |
| `gte` | `>=` | `{"age__gte": 18}` |
| `lt` | `<` | `{"age__lt": 65}` |
| `lte` | `<=` | `{"age__lte": 65}` |
| `like` | `LIKE` | `{"email__like": "%@example.com"}` |
| `ilike` | `ILIKE` | `{"email__ilike": "%@EXAMPLE.com"}` |
| `in` | `IN` | `{"status__in": ["active", "pending"]}` |
| `not_in` | `NOT IN` | `{"status__not_in": ["deleted"]}` |
| `is_null` | `IS NULL` | `{"deleted_at__is_null": True}` |
| `is_not_null` | `IS NOT NULL` | `{"deleted_at__is_not_null": True}` |

## Common Patterns

### Active Users Only

```python
users = await repo.get_many(is_active=True)
```

### Recent Users

```python
from datetime import datetime, timedelta

query = select(User)
query = repo.apply_filters(query, {
    "created_at__gte": datetime.utcnow() - timedelta(days=30)
})
result = await repo.paginate(query, page=1, page_size=50)
```

### Search by Email

```python
query = select(User)
query = repo.apply_filters(query, {"email__ilike": f"%{search_term}%"})
users = (await repo.session.execute(query)).scalars().all()
```

### Bulk Deactivate

```python
count = await repo.update_many(
    {"last_login__lt": datetime.utcnow() - timedelta(days=90)},
    {"is_active": False}
)
```

### Soft Delete Inactive

```python
count = await repo.delete_many({"is_active__eq": False})
```

## Tips

1. Always use `include_deleted=False` (default) unless you specifically need deleted records
2. Combine filters before pagination for better performance
3. Use bulk operations instead of loops
4. Use transactions for multi-step operations
5. Enable query logging in development only
6. Add database indexes for frequently filtered/sorted fields
