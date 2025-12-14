# Test Setup Guide

Quick guide to set up and run the test suite.

## Prerequisites

- Python 3.11 or higher
- Git (for version control)

## Installation

### 1. Install the Package in Development Mode

From the project root directory:

```bash
# Install package with development dependencies
pip install -e ".[dev]"
```

This installs:
- The `agent_service` package in editable mode
- All test dependencies (pytest, pytest-asyncio, factory-boy, etc.)
- Code quality tools (ruff, mypy)

### 2. Verify Installation

```bash
# Check that pytest is installed
pytest --version

# Check that the package is importable
python -c "import agent_service; print('Success!')"
```

## Running Tests

### Quick Start

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test directory
pytest tests/unit/
```

### First Test Run

The example tests should work out of the box:

```bash
# Run the example unit tests
pytest tests/unit/test_example.py -v

# Run a specific test
pytest tests/unit/test_example.py::test_basic_assertion -v
```

Expected output:
```
tests/unit/test_example.py::test_basic_assertion PASSED
```

## Configuration

### Environment Variables

Create a `.env` file in the project root (optional for tests):

```bash
# .env
# Tests use SQLite by default, but you can override:

# Use PostgreSQL for tests
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/test_db

# Use real Redis for integration tests (optional)
REDIS_URL=redis://localhost:6379/15
```

### Test Database Setup (Optional)

Tests use SQLite in-memory database by default. For PostgreSQL tests:

```bash
# Create test database
createdb test_agent_service

# Set environment variable
export DATABASE_URL="postgresql+asyncpg://localhost/test_agent_service"

# Run tests
pytest
```

## Test Coverage

### Generate Coverage Report

```bash
# Run tests with coverage
pytest --cov=src/agent_service --cov-report=html

# View HTML report
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

### Coverage Configuration

Edit `pytest.ini` to customize coverage settings:

```ini
[pytest]
addopts =
    --cov=src/agent_service
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80  # Fail if coverage < 80%
```

## Common Commands

```bash
# Run fast tests only (exclude slow tests)
pytest -m "not slow"

# Run with output from print statements
pytest -s

# Run tests in parallel (faster)
pytest -n auto

# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l

# Re-run only failed tests
pytest --lf

# Run tests matching pattern
pytest -k "test_auth"
```

## Troubleshooting

### Import Error: No module named 'agent_service'

**Solution**: Install the package in development mode:
```bash
pip install -e .
```

### Tests hang or timeout

**Cause**: Async/await issues or database connection problems

**Solution**:
1. Check that all async functions use `async def` and `await`
2. Verify database connection settings
3. Check event loop configuration

### Database errors

**Cause**: Database not accessible or migrations not applied

**Solution**:
1. Use SQLite (default) for simple tests
2. For PostgreSQL, ensure database exists
3. Check connection string in settings

### pytest not found

**Solution**: Install development dependencies:
```bash
pip install -e ".[dev]"
```

### Factory Boy errors

**Cause**: Session not properly configured

**Solution**: Use the fixtures:
```python
async def test_example(factory_session):
    user = await UserFactory.create_async(session=factory_session)
```

## Next Steps

1. **Write Your First Test**: Start with a simple unit test
2. **Create Model Factories**: Add factories for your database models
3. **Test Your API**: Add E2E tests for your endpoints
4. **Security Tests**: Add security-focused tests
5. **CI/CD Integration**: Set up GitHub Actions or similar

## Resources

- Main README: [tests/README.md](./README.md)
- Pytest docs: https://docs.pytest.org/
- Factory Boy: https://factoryboy.readthedocs.io/
- FastAPI Testing: https://fastapi.tiangolo.com/tutorial/testing/

## Getting Help

If you encounter issues:

1. Check test output for error messages
2. Run with `-v` for more details
3. Use `--pdb` to drop into debugger on failure
4. Check the example tests for reference
5. Review the fixtures in `conftest.py`
