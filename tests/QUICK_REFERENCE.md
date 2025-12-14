# Test Infrastructure Quick Reference

## Installation

```bash
pip install -e ".[dev]"
```

## Running Tests

```bash
# All tests
pytest

# Specific directory
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
pytest tests/security/

# Specific file
pytest tests/unit/test_example.py

# Specific test
pytest tests/unit/test_example.py::test_basic_assertion

# By marker
pytest -m "not slow"      # Fast tests only
pytest -m integration     # Integration tests
pytest -m security        # Security tests

# With coverage
pytest --cov=src/agent_service --cov-report=html

# Parallel
pytest -n auto

# Verbose
pytest -v

# Stop on first failure
pytest -x

# Show output
pytest -s
```

## Common Fixtures

```python
# Database
async def test_db(db_session: AsyncSession):
    user = User(name="test")
    db_session.add(user)
    await db_session.commit()

# HTTP Client
async def test_api(async_client: AsyncClient):
    response = await async_client.get("/api/v1/users")
    assert response.status_code == 200

# Authenticated Client
async def test_auth(authenticated_client: AsyncClient):
    response = await authenticated_client.get("/api/v1/profile")
    assert response.status_code == 200

# Factory
async def test_factory(factory_session):
    user = await UserFactory.create_async(
        session=factory_session,
        email="test@example.com"
    )

# Mock Redis
async def test_cache(mock_redis):
    mock_redis.get.return_value = b"value"
    value = await mock_redis.get("key")
    assert value == b"value"

# Settings
def test_config(test_settings):
    assert test_settings.debug is True
```

## Writing Tests

### Unit Test Template

```python
# tests/unit/test_my_module.py
import pytest

async def test_my_function():
    """Test description."""
    result = await my_function()
    assert result == expected
```

### Integration Test Template

```python
# tests/integration/test_my_integration.py
from sqlalchemy.ext.asyncio import AsyncSession

async def test_database_operation(db_session: AsyncSession):
    """Test database operation."""
    # Create
    record = MyModel(name="test")
    db_session.add(record)
    await db_session.commit()

    # Verify
    assert record.id is not None
```

### E2E Test Template

```python
# tests/e2e/test_my_api.py
from httpx import AsyncClient

async def test_endpoint(async_client: AsyncClient):
    """Test API endpoint."""
    response = await async_client.post(
        "/api/v1/resource",
        json={"name": "test"}
    )
    assert response.status_code == 201
```

### Factory Template

```python
# tests/factories/user.py
from tests.factories.base import AsyncSQLModelFactory
from agent_service.domain.models import User
import factory

class UserFactory(AsyncSQLModelFactory):
    class Meta:
        model = User

    email = factory.Faker("email")
    username = factory.Faker("user_name")
    is_active = True

# Usage in tests
async def test_with_factory(factory_session):
    user = await UserFactory.create_async(
        session=factory_session,
        email="custom@example.com"
    )
```

## Markers

```python
@pytest.mark.slow
def test_slow_operation():
    """Slow test."""
    pass

@pytest.mark.integration
async def test_integration():
    """Integration test."""
    pass

@pytest.mark.e2e
async def test_e2e():
    """E2E test."""
    pass

@pytest.mark.security
async def test_security():
    """Security test."""
    pass

@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
])
def test_parameterized(input, expected):
    assert input * 2 == expected
```

## Assertions

```python
# Basic
assert value == expected
assert value is not None
assert value in collection

# Exceptions
with pytest.raises(ValueError):
    raise ValueError("error")

with pytest.raises(ValueError, match="error message"):
    raise ValueError("error message")

# Async exceptions
async def test_async_exception():
    with pytest.raises(RuntimeError):
        await async_function()
```

## Mocking

```python
from unittest.mock import Mock, AsyncMock, patch

# Mock object
mock_obj = Mock()
mock_obj.method.return_value = 42

# Async mock
mock_service = AsyncMock()
mock_service.fetch.return_value = {"data": "value"}
result = await mock_service.fetch()

# Patch
@patch("module.function")
def test_with_patch(mock_func):
    mock_func.return_value = "mocked"
    result = function_that_calls_it()
```

## Configuration Files

### pytest.ini (root directory)

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
markers =
    slow: slow tests
    integration: integration tests
```

### .env (for test database)

```bash
DATABASE_URL=postgresql+asyncpg://localhost/test_db
REDIS_URL=redis://localhost:6379/15
```

## Directory Structure

```
tests/
├── conftest.py              # Fixtures
├── factories/               # Test data factories
│   ├── base.py
│   └── user.py             # Example
├── unit/                   # Unit tests
├── integration/            # Integration tests
├── e2e/                   # E2E tests
└── security/              # Security tests
```

## Key Files

- `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/tests/conftest.py` - All fixtures
- `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/pytest.ini` - Pytest config
- `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/tests/factories/base.py` - Factory base classes
- `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/tests/README.md` - Full documentation

## Troubleshooting

```bash
# Module not found
pip install -e ".[dev]"

# Show print statements
pytest -s

# Debug on failure
pytest --pdb

# Verbose output
pytest -vv

# Show local variables
pytest -l

# Re-run failed
pytest --lf
```

## Coverage

```bash
# Generate HTML coverage
pytest --cov=src/agent_service --cov-report=html

# View report
open htmlcov/index.html

# Terminal report
pytest --cov=src/agent_service --cov-report=term-missing

# Fail if coverage < 80%
pytest --cov=src/agent_service --cov-fail-under=80
```

## CI/CD Example

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: pytest --cov --cov-report=xml
```
