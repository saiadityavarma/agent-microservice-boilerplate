# Enhanced Repository Pattern Features

This document describes the advanced features added to the BaseRepository pattern.

## Overview

The enhanced BaseRepository provides a comprehensive set of features for database operations:

1. Soft delete as default behavior
2. Pagination helper with metadata
3. Sorting helper with nested field support
4. Advanced filtering with operators
5. Bulk operations
6. Transaction support (decorator and context manager)
7. Query logging for debugging

## 1. Soft Delete

### Default Behavior

By default, `delete()` performs a soft delete by setting the `deleted_at` timestamp:

```python
# Soft delete (sets deleted_at)
deleted = await repo.delete(user_id)

# Get excludes soft-deleted records by default
user = await repo.get(user_id)  # Returns None

# Include deleted records explicitly
user = await repo.get(user_id, include_deleted=True)  # Returns user
```

### Hard Delete

For permanent deletion, use `hard_delete()`:

```python
# Permanent deletion
await repo.hard_delete(user_id)

# Now it's really gone
user = await repo.get(user_id, include_deleted=True)  # Returns None
```

### Query Behavior

All queries automatically exclude soft-deleted records:

```python
# Excludes deleted by default
users = await repo.get_many()

# Include deleted records
users = await repo.get_many(include_deleted=True)
```

## 2. Pagination

The `paginate()` method returns a `PaginatedResult` with comprehensive metadata:

```python
from sqlalchemy import select

query = select(User).where(User.is_active == True)
result = await repo.paginate(query, page=2, page_size=10)

# Access pagination metadata
print(f"Page {result.page} of {result.total_pages}")
print(f"Total items: {result.total}")
print(f"Has next: {result.has_next}")
print(f"Has previous: {result.has_prev}")

# Iterate over items
for user in result.items:
    print(user.email)
```

### PaginatedResult Structure

```python
class PaginatedResult(NamedTuple):
    items: Sequence[Any]      # List of entities on current page
    total: int                # Total number of items across all pages
    page: int                 # Current page number (1-indexed)
    page_size: int            # Number of items per page
    total_pages: int          # Total number of pages
    has_next: bool            # Whether there's a next page
    has_prev: bool            # Whether there's a previous page
```

## 3. Sorting

The `apply_sorting()` method supports sorting by any field:

```python
from sqlalchemy import select

query = select(User)

# Sort by created_at descending (default)
query = repo.apply_sorting(query, "created_at", "desc")

# Sort by email ascending
query = repo.apply_sorting(query, "email", "asc")

# Sort by name descending
query = repo.apply_sorting(query, "name", "desc")
```

### Nested Field Support

The sorting helper supports nested fields (simplified implementation):

```python
# Sort by nested field
query = repo.apply_sorting(query, "user.email", "asc")
```

Note: Full nested field support requires proper table joins. The current implementation extracts the field name.

## 4. Advanced Filtering

The `apply_filters()` method supports multiple operators:

### Supported Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equal | `{"is_active__eq": True}` |
| `ne` | Not equal | `{"name__ne": "Admin"}` |
| `gt` | Greater than | `{"age__gt": 18}` |
| `gte` | Greater than or equal | `{"created_at__gte": date}` |
| `lt` | Less than | `{"age__lt": 65}` |
| `lte` | Less than or equal | `{"created_at__lte": date}` |
| `like` | SQL LIKE | `{"email__like": "%@example.com"}` |
| `ilike` | Case-insensitive LIKE | `{"email__ilike": "%@EXAMPLE.com"}` |
| `in` | IN clause | `{"provider__in": ["azure_ad", "local"]}` |
| `not_in` | NOT IN clause | `{"status__not_in": ["deleted", "banned"]}` |
| `is_null` | IS NULL | `{"deleted_at__is_null": True}` |
| `is_not_null` | IS NOT NULL | `{"deleted_at__is_not_null": True}` |

### Usage Examples

```python
from datetime import datetime
from sqlalchemy import select

query = select(User)

# Single filter
query = repo.apply_filters(query, {"is_active__eq": True})

# Multiple filters
filters = {
    "is_active__eq": True,
    "created_at__gte": datetime(2024, 1, 1),
    "email__ilike": "%@example.com",
    "provider__in": ["azure_ad", "aws_cognito"],
}
query = repo.apply_filters(query, filters)

result = await repo.session.execute(query)
users = result.scalars().all()
```

## 5. Bulk Operations

### Bulk Create

Create multiple entities in a single operation:

```python
users_data = [
    {"email": "user1@example.com", "name": "User 1", "provider": "local", "provider_user_id": "user1"},
    {"email": "user2@example.com", "name": "User 2", "provider": "local", "provider_user_id": "user2"},
]

users = await repo.create_many(users_data)
print(f"Created {len(users)} users")
```

### Bulk Update

Update multiple entities matching filters:

```python
# Update all inactive users
count = await repo.update_many(
    filters={"is_active__eq": False},
    updates={"deleted_at": datetime.utcnow()}
)
print(f"Updated {count} users")

# Update users created before a date
count = await repo.update_many(
    filters={"created_at__lt": datetime(2024, 1, 1)},
    updates={"is_active": False}
)
```

### Bulk Delete

Soft delete multiple entities matching filters:

```python
# Soft delete all inactive users
count = await repo.delete_many({"is_active__eq": False})
print(f"Deleted {count} users")

# Soft delete users from specific provider
count = await repo.delete_many({"provider__eq": "local"})
```

## 6. Transaction Support

### Context Manager

Use the `transaction()` context manager for explicit transaction control:

```python
async with repo.transaction():
    user = await repo.create(user_data)
    await other_repo.create(related_data)
    # Commits on success, rolls back on exception
```

### Decorator

Use the `@transactional` decorator for automatic transaction handling:

```python
from agent_service.infrastructure.database.repositories.base import transactional

@transactional
async def create_user_with_related_data(repo, user_data, related_data):
    """Create user and related data in a transaction."""
    user = await repo.create(user_data)
    # ... create related data ...
    return user

# Usage
user = await create_user_with_related_data(repo, user_data, related_data)
```

### Error Handling

Both methods automatically commit on success and rollback on exception:

```python
try:
    async with repo.transaction():
        user = await repo.create(user_data)
        # This will cause rollback
        raise ValueError("Something went wrong")
except ValueError:
    # User creation was rolled back
    pass
```

## 7. Query Logging

Enable query logging for debugging:

```python
# Enable logging when creating repository
repo = UserRepository(session, enable_query_logging=True)

# All queries will be logged with DEBUG level
users = await repo.get_many(is_active=True)

# Pagination also logs queries
result = await repo.paginate(query, page=1, page_size=10)
```

Logs include:
- SQL query statement
- Query parameters
- Pagination metadata

## Combining Features

All features work together seamlessly:

```python
from datetime import datetime
from sqlalchemy import select

# Build base query
query = select(User)

# Apply filters
filters = {
    "is_active__eq": True,
    "created_at__gte": datetime(2024, 1, 1),
    "email__ilike": "%@example.com",
}
query = repo.apply_filters(query, filters)

# Apply sorting
query = repo.apply_sorting(query, "created_at", "desc")

# Paginate
result = await repo.paginate(query, page=1, page_size=20)

print(f"Found {result.total} active users")
print(f"Showing page {result.page} of {result.total_pages}")

for user in result.items:
    print(f"- {user.email} (created: {user.created_at})")
```

## Model Requirements

### Soft Delete Support

To support soft delete, your model must include the `SoftDeleteMixin`:

```python
from agent_service.infrastructure.database.base_model import BaseModel, SoftDeleteMixin

class User(BaseModel, SoftDeleteMixin, table=True):
    __tablename__ = "users"
    # ... fields ...
```

The `SoftDeleteMixin` provides:
- `deleted_at: datetime | None` field
- `is_deleted: bool` property

### Without Soft Delete

Models without `SoftDeleteMixin` will use hard delete by default:

```python
class Session(BaseModel, table=True):
    __tablename__ = "sessions"
    # ... fields ...

# delete() will perform hard delete
await repo.delete(session_id)
```

## Best Practices

1. **Always use soft delete for user data** - Enables data recovery and audit trails
2. **Use hard delete for temporary data** - Sessions, tokens, etc.
3. **Combine filters, sorting, and pagination** - Build complex queries efficiently
4. **Use bulk operations for batch processing** - Better performance than loops
5. **Use transactions for multi-entity operations** - Ensures data consistency
6. **Enable query logging in development** - Helps debug performance issues
7. **Exclude deleted records explicitly** - Use `include_deleted=False` in custom queries

## Performance Considerations

1. **Pagination** - Always paginate large result sets
2. **Bulk operations** - Use `create_many()`, `update_many()`, `delete_many()` instead of loops
3. **Filtering** - Apply filters before pagination to reduce query size
4. **Sorting** - Add database indexes for frequently sorted fields
5. **Query logging** - Disable in production for better performance

## Examples

See the following files for complete examples:

- `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/examples/repository_usage.py` - Comprehensive usage examples
- `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/tests/test_enhanced_repository.py` - Test suite with examples

## Implementation Details

Location: `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/infrastructure/database/repositories/base.py`

Key classes:
- `BaseRepository[T]` - Enhanced repository base class
- `PaginatedResult` - Pagination result container
- `transactional` - Transaction decorator

Key methods:
- `get()`, `get_many()` - Read operations with soft delete support
- `create()`, `create_many()` - Create operations
- `update()`, `update_many()` - Update operations
- `delete()`, `hard_delete()`, `delete_many()` - Delete operations
- `apply_filters()` - Advanced filtering
- `apply_sorting()` - Sorting support
- `paginate()` - Pagination with metadata
- `transaction()` - Transaction context manager
