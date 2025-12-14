# Test Suite

Comprehensive test suite for the Agent Service application.

## Structure

```
tests/
├── conftest.py                     # Main pytest configuration and shared fixtures
├── pytest.ini                      # Pytest configuration
├── README.md                       # This file
├── factories/                      # Factory Boy factories for test data
│   ├── __init__.py
│   ├── base.py                    # Base factory classes
│   └── fixtures.py                # Factory fixtures for pytest
├── unit/                          # Unit tests
│   ├── __init__.py
│   └── test_example.py           # Example unit tests
├── integration/                   # Integration tests
│   ├── __init__.py
│   └── test_example_integration.py
├── e2e/                          # End-to-end tests
│   ├── __init__.py
│   └── test_example_e2e.py
└── security/                     # Security tests
    ├── __init__.py
    └── test_example_security.py
```

## Setup

### Install Test Dependencies

```bash
# Install all dependencies including test dependencies
pip install -e ".[dev]"

# Or install test dependencies separately
pip install pytest pytest-asyncio pytest-cov httpx factory-boy
```

### Environment Setup

Tests use SQLite by default for speed and simplicity. To use PostgreSQL:

```bash
# Set test database URL
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/test_db"

# For Redis integration tests
export REDIS_URL="redis://localhost:6379/15"
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# End-to-end tests
pytest tests/e2e/

# Security tests
pytest tests/security/
```

### Run by Markers

```bash
# Run only fast tests (exclude slow tests)
pytest -m "not slow"

# Run only slow tests
pytest -m slow

# Run integration tests
pytest -m integration

# Run security tests
pytest -m security
```

### Run Specific Tests

```bash
# Run a specific test file
pytest tests/unit/test_example.py

# Run a specific test function
pytest tests/unit/test_example.py::test_basic_assertion

# Run tests matching a pattern
pytest -k "test_auth"
```

### Verbose Output

```bash
# More verbose output
pytest -v

# Even more verbose (show test names as they run)
pytest -vv

# Show local variables on failures
pytest -l
```

### Coverage

```bash
# Run with coverage report
pytest --cov=src/agent_service --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Parallel Execution

```bash
# Install pytest-xdist first
pip install pytest-xdist

# Run tests in parallel
pytest -n auto
```

## Available Fixtures

### Settings and Configuration

- `test_settings`: Test settings with overrides for test environment
- `override_settings`: Auto-use fixture that overrides global settings

### Database

- `test_engine`: Test database engine (session-scoped)
- `test_session_factory`: Session factory for creating test sessions
- `db_session`: Database session with automatic rollback after each test
- `db_manager`: Configured DatabaseManager instance

### Redis

- `mock_redis`: Mock Redis client for tests that don't need real Redis
- `redis_client`: Real Redis client for integration tests (skips if not available)

### FastAPI

- `app`: FastAPI application instance
- `async_client`: Async HTTP client for testing endpoints
- `authenticated_client`: HTTP client with authentication headers

### Authentication

- `mock_user`: Mock user data for authentication tests
- `mock_admin_user`: Mock admin user data
- `mock_api_key`: Mock API key for API key authentication
- `auth_headers`: Authentication headers dictionary
- `api_key_headers`: API key headers dictionary

### Factory Boy

- `factory_manager`: Manager for configuring factories with DB session
- `factory_session`: Direct access to DB session for factory usage

## Writing Tests

### Unit Test Example

```python
# tests/unit/test_my_feature.py
import pytest

async def test_my_function():
    """Test description."""
    result = await my_async_function()
    assert result == expected_value
```

### Integration Test with Database

```python
# tests/integration/test_my_feature.py
from sqlalchemy.ext.asyncio import AsyncSession

async def test_create_record(db_session: AsyncSession):
    """Test creating a database record."""
    record = MyModel(name="Test")
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    assert record.id is not None
```

### E2E Test with HTTP Client

```python
# tests/e2e/test_my_api.py
from httpx import AsyncClient

async def test_api_endpoint(async_client: AsyncClient):
    """Test API endpoint."""
    response = await async_client.get("/api/v1/resource")
    assert response.status_code == 200
    assert "data" in response.json()
```

### Using Factories

```python
# tests/factories/user.py
from tests.factories.base import AsyncSQLModelFactory
from agent_service.domain.models import User

class UserFactory(AsyncSQLModelFactory):
    class Meta:
        model = User

    email = factory.Faker("email")
    username = factory.Faker("user_name")

# In tests:
async def test_with_factory(factory_session):
    user = await UserFactory.create_async(
        session=factory_session,
        email="test@example.com"
    )
    assert user.id is not None
```

### Parameterized Tests

```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_multiply_by_two(input, expected):
    assert input * 2 == expected
```

### Testing Exceptions

```python
async def test_raises_exception():
    with pytest.raises(ValueError, match="invalid value"):
        await function_that_raises()
```

## Best Practices

### Test Organization

1. **One test per function/behavior**: Each test should verify one specific behavior
2. **Descriptive test names**: Use clear, descriptive names that explain what is being tested
3. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and verification
4. **Independent tests**: Tests should not depend on each other
5. **Clean up**: Use fixtures with proper teardown to clean up after tests

### Test Data

1. **Use factories**: Create test data using Factory Boy for consistency
2. **Minimal data**: Create only the data needed for the test
3. **Realistic data**: Use realistic values that match production scenarios
4. **Avoid magic values**: Use constants or fixtures for test values

### Async Tests

1. **Use async/await**: All async code must use async/await syntax
2. **AsyncClient**: Use async_client fixture for HTTP requests
3. **AsyncSession**: Use db_session fixture for database operations
4. **No sync calls**: Don't mix sync and async code

### Mocking

1. **Mock external services**: Always mock external APIs and services
2. **Use AsyncMock**: Use AsyncMock for async functions
3. **Verify calls**: Assert that mocks were called correctly
4. **Reset mocks**: Clean up mocks between tests

### Coverage

1. **Aim for >80%**: Maintain high test coverage
2. **Test edge cases**: Include tests for error conditions and edge cases
3. **Test error handling**: Verify error handling logic
4. **Integration tests**: Include integration tests for critical paths

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      - name: Run tests
        run: |
          pytest --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Troubleshooting

### Common Issues

**Issue**: Tests hang or timeout
- Check for async/await issues
- Ensure event loop is properly configured
- Check for deadlocks in database tests

**Issue**: Database errors
- Ensure test database URL is correct
- Check that migrations are applied
- Verify session management and rollback

**Issue**: Import errors
- Ensure package is installed: `pip install -e .`
- Check Python path
- Verify module structure

**Issue**: Fixture not found
- Check fixture is defined in conftest.py
- Verify pytest_plugins is configured
- Check fixture scope and dependencies

### Debug Mode

```bash
# Run with Python debugger
pytest --pdb

# Drop into debugger on first failure
pytest -x --pdb

# Show print statements
pytest -s
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Factory Boy](https://factoryboy.readthedocs.io/)
- [HTTPX](https://www.python-httpx.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
