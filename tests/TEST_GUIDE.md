# Comprehensive Test Suite Guide

This directory contains a comprehensive test suite for the Agent Service, organized into unit tests, integration tests, end-to-end tests, and load tests.

## Table of Contents

- [Quick Start](#quick-start)
- [Test Organization](#test-organization)
- [Running Tests](#running-tests)
- [Test Markers](#test-markers)
- [Coverage](#coverage)
- [Writing Tests](#writing-tests)
- [CI/CD Integration](#cicd-integration)

## Quick Start

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/agent_service --cov-report=html

# Run specific test categories
pytest -m unit          # Only unit tests
pytest -m integration   # Only integration tests
pytest -m e2e           # Only end-to-end tests

# Run tests for specific component
pytest tests/unit/api/              # API tests
pytest tests/unit/agents/           # Agent tests
pytest tests/integration/           # All integration tests
```

## Test Organization

```
tests/
├── unit/                       # Unit tests (fast, isolated)
│   ├── api/                   # API route handler tests
│   │   ├── test_agents_routes.py
│   │   └── test_protocols_routes.py
│   ├── agents/                # Agent implementation tests
│   │   └── test_agent_implementations.py
│   ├── tools/                 # Tool registry and implementation tests
│   │   └── test_tool_registry.py
│   ├── protocols/             # Protocol handler tests
│   │   └── test_protocol_handlers.py
│   └── auth/                  # Authentication tests (existing)
│
├── integration/               # Integration tests (with database, services)
│   ├── test_auth_flow.py     # Complete auth flows
│   ├── test_agent_invocation.py  # Agent with database
│   ├── test_protocol_handlers.py # Protocols with mock agents
│   └── test_database.py      # Database operations
│
├── e2e/                       # End-to-end tests (full workflows)
│   ├── test_full_agent_flow.py   # Complete user journeys
│   └── test_api_workflow.py      # API CRUD workflows
│
├── load/                      # Load/performance tests
│   ├── locustfile.py         # Locust load test definitions
│   └── README.md             # Load testing guide
│
├── security/                  # Security tests (existing)
├── config/                    # Configuration tests (existing)
├── factories/                 # Test data factories (existing)
├── conftest.py               # Shared fixtures
└── TEST_GUIDE.md             # This file
```

## Running Tests

### By Test Type

```bash
# Unit tests (fast, no external dependencies)
pytest -m unit

# Integration tests (require database)
pytest -m integration

# End-to-end tests (full workflows)
pytest -m e2e

# Security tests
pytest -m security

# Smoke tests (quick validation)
pytest -m smoke
```

### By Component

```bash
# API tests
pytest tests/unit/api/ -v

# Agent tests
pytest tests/unit/agents/ -v

# Tool tests
pytest tests/unit/tools/ -v

# Protocol tests
pytest tests/unit/protocols/ -v

# Database tests
pytest tests/integration/test_database.py -v
```

### By Speed

```bash
# Fast tests only (exclude slow tests)
pytest -m "not slow"

# All tests including slow ones
pytest -m slow
```

### With Specific Requirements

```bash
# Tests that need database
pytest -m requires_db

# Tests that need Redis
pytest -m requires_redis

# Tests that need Celery
pytest -m requires_celery
```

## Test Markers

All available test markers are defined in `pytest.ini`:

### Test Types
- `unit` - Unit tests (isolated, fast)
- `integration` - Integration tests (with external services)
- `e2e` - End-to-end tests (full workflows)
- `security` - Security-focused tests
- `smoke` - Quick validation tests

### Component Markers
- `api` - API endpoint tests
- `agent` - Agent implementation tests
- `tool` - Tool implementation tests
- `protocol` - Protocol handler tests
- `auth` - Authentication/authorization tests
- `database` - Database operation tests

### Special Requirements
- `slow` - Slow tests (>5 seconds)
- `requires_db` - Requires real database
- `requires_redis` - Requires Redis connection
- `requires_celery` - Requires Celery worker
- `requires_external_api` - Requires external API access
- `performance` - Performance/benchmark tests

### Using Markers

```python
import pytest

@pytest.mark.unit
def test_simple_function():
    """Fast unit test."""
    assert True

@pytest.mark.integration
@pytest.mark.requires_db
async def test_database_operation(db_session):
    """Integration test with database."""
    # Test code here

@pytest.mark.e2e
@pytest.mark.slow
async def test_complete_workflow():
    """Full end-to-end workflow test."""
    # Test code here
```

## Coverage

### Generate Coverage Reports

```bash
# HTML report (opens in browser)
pytest --cov=src/agent_service --cov-report=html
open htmlcov/index.html

# Terminal report
pytest --cov=src/agent_service --cov-report=term-missing

# XML report (for CI)
pytest --cov=src/agent_service --cov-report=xml

# All formats
pytest --cov=src/agent_service --cov-report=html --cov-report=term-missing --cov-report=xml
```

### Coverage Targets

- **Overall**: 80%+ coverage required
- **Unit Tests**: Should achieve 90%+ coverage
- **Critical Paths**: Authentication, agent invocation - 95%+ coverage

### Viewing Coverage

```bash
# After running tests with --cov-report=html
open htmlcov/index.html
```

Coverage reports show:
- Line coverage per file
- Branch coverage
- Missing lines
- Excluded lines

## Writing Tests

### Unit Test Example

```python
# tests/unit/api/test_my_route.py
import pytest
from unittest.mock import AsyncMock

@pytest.mark.unit
async def test_my_endpoint(async_client):
    """Test endpoint returns expected data."""
    response = await async_client.get("/api/v1/endpoint")

    assert response.status_code == 200
    assert response.json()["key"] == "value"
```

### Integration Test Example

```python
# tests/integration/test_my_integration.py
import pytest

@pytest.mark.integration
@pytest.mark.requires_db
async def test_database_integration(db_session):
    """Test database operations."""
    from agent_service.models import MyModel

    # Create
    obj = MyModel(name="test")
    db_session.add(obj)
    await db_session.commit()

    # Verify
    assert obj.id is not None
```

### E2E Test Example

```python
# tests/e2e/test_my_workflow.py
import pytest

@pytest.mark.e2e
async def test_complete_workflow(async_client, db_session):
    """Test complete user workflow."""
    # Step 1: Create user
    # Step 2: Authenticate
    # Step 3: Perform action
    # Step 4: Verify results
    pass
```

## Fixtures

Common fixtures available in `conftest.py`:

- `async_client` - AsyncClient for API testing
- `db_session` - Database session with auto-rollback
- `mock_user` - Mock user data
- `mock_api_key` - Mock API key
- `test_settings` - Test configuration
- `mock_redis` - Mock Redis client

### Using Fixtures

```python
async def test_with_fixtures(async_client, db_session, mock_user):
    """Test using multiple fixtures."""
    # Use async_client for API calls
    # Use db_session for database operations
    # Use mock_user for authentication
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements/test.txt

      - name: Run unit tests
        run: pytest -m unit --cov --cov-report=xml

      - name: Run integration tests
        run: pytest -m integration --cov --cov-append

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

## Test Commands Cheat Sheet

```bash
# Quick validation
pytest -m smoke

# Fast unit tests only
pytest -m unit -v

# Integration with coverage
pytest -m integration --cov=src/agent_service

# E2E tests
pytest -m e2e --log-cli-level=INFO

# All tests with HTML report
pytest --cov=src/agent_service --cov-report=html

# Specific test file
pytest tests/unit/api/test_agents_routes.py -v

# Specific test function
pytest tests/unit/api/test_agents_routes.py::TestAgentInvokeRoute::test_invoke_agent_success

# Run with debugging
pytest --pdb  # Drop into debugger on failure
pytest -s     # Show print statements

# Parallel execution (if pytest-xdist installed)
pytest -n auto

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf

# Verbose with full output
pytest -vv --tb=long

# Create baseline for performance
pytest -m performance --benchmark-save=baseline
```

## Best Practices

### 1. Test Naming
- Use descriptive names: `test_invoke_agent_returns_correct_response`
- Include test type in module: `test_agent_routes.py`

### 2. Test Organization
- One test class per component/route
- Group related tests together
- Use clear docstrings

### 3. Fixtures
- Use fixtures for common setup
- Keep fixtures in `conftest.py` for reuse
- Clean up after tests (auto-rollback in db fixtures)

### 4. Markers
- Always mark tests appropriately
- Use multiple markers when relevant
- Document custom markers

### 5. Assertions
- Use specific assertions
- Include helpful failure messages
- Test both success and failure cases

### 6. Mocking
- Mock external dependencies
- Use AsyncMock for async functions
- Verify mock calls when testing behavior

### 7. Coverage
- Aim for 80%+ overall coverage
- Focus on critical paths first
- Don't test external libraries

## Troubleshooting

### Tests Fail Locally

```bash
# Clear pytest cache
pytest --cache-clear

# Recreate database
alembic downgrade base
alembic upgrade head

# Check test isolation
pytest -v --tb=short
```

### Slow Tests

```bash
# Find slowest tests
pytest --durations=10

# Run only fast tests
pytest -m "not slow"
```

### Coverage Not Matching

```bash
# Ensure coverage config is correct
pytest --cov-config=pytest.ini

# Check omit patterns in pytest.ini
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Testing FastAPI](https://fastapi.tiangolo.com/tutorial/testing/)
- [Async Testing Guide](https://docs.pytest.org/en/stable/how-to/async.html)
