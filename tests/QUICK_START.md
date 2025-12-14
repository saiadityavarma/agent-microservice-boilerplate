# Test Suite Quick Start

Get started with the test suite in 5 minutes!

## 1. Install Dependencies

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov httpx

# Optional: for load testing
pip install locust
```

## 2. Run Tests

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=src/agent_service --cov-report=html
open htmlcov/index.html  # View coverage report
```

## 3. Common Test Commands

```bash
# Fast unit tests only
pytest -m unit

# Integration tests (requires database)
pytest -m integration

# End-to-end tests
pytest -m e2e

# Skip slow tests
pytest -m "not slow"

# Specific component
pytest tests/unit/api/

# Specific test file
pytest tests/unit/api/test_agents_routes.py -v

# Specific test
pytest tests/unit/api/test_agents_routes.py::TestAgentInvokeRoute::test_invoke_agent_success -v
```

## 4. Understanding Test Output

```
tests/unit/api/test_agents_routes.py::TestAgentInvokeRoute::test_invoke_agent_success PASSED [100%]

==================== test session starts ====================
platform darwin -- Python 3.11.x, pytest-7.x, pluggy-1.x
collected 535 items

tests/unit/... [SUCCESS]

---------- coverage: platform darwin, python 3.11 ----------
Name                     Stmts   Miss  Cover
--------------------------------------------
src/agent_service/...      500     50    90%
--------------------------------------------
TOTAL                      500     50    90%

==================== 535 passed in 45.2s ====================
```

## 5. Test Organization

```
tests/
├── unit/           # Fast, isolated tests
├── integration/    # Tests with database/services
├── e2e/           # Full workflow tests
├── load/          # Performance tests (Locust)
└── security/      # Security tests
```

## 6. Load Testing

```bash
# Start your service
uvicorn agent_service.main:app --port 8000

# Run load test with web UI
locust -f tests/load/locustfile.py --host=http://localhost:8000

# Visit http://localhost:8089 to configure and start
```

## 7. Debug Failing Tests

```bash
# Show print statements
pytest -s

# Drop into debugger on failure
pytest --pdb

# Show full traceback
pytest --tb=long

# Run only last failed tests
pytest --lf

# Stop on first failure
pytest -x
```

## 8. CI/CD Integration

Add to your CI pipeline:

```bash
# Run tests with coverage
pytest --cov=src/agent_service --cov-report=xml --cov-fail-under=80

# Upload coverage
# (varies by CI system)
```

## 9. Next Steps

- Read [TEST_GUIDE.md](TEST_GUIDE.md) for comprehensive documentation
- Check [TEST_SUITE_SUMMARY.md](TEST_SUITE_SUMMARY.md) for overview
- See [load/README.md](load/README.md) for load testing guide

## 10. Getting Help

```bash
# Pytest help
pytest --help

# Available markers
pytest --markers

# Available fixtures
pytest --fixtures

# Collect tests without running
pytest --collect-only
```

## Common Issues

### Tests fail with database errors
```bash
# Run database migrations
alembic upgrade head
```

### Import errors
```bash
# Ensure package is installed
pip install -e .
```

### Coverage seems low
```bash
# Run all tests including integration
pytest -m "unit or integration" --cov
```

## Quick Reference Card

| Command | Description |
|---------|-------------|
| `pytest` | Run all tests |
| `pytest -m unit` | Unit tests only |
| `pytest -m integration` | Integration tests |
| `pytest -m e2e` | E2E tests |
| `pytest -v` | Verbose output |
| `pytest -x` | Stop on first failure |
| `pytest --lf` | Run last failed |
| `pytest --cov` | With coverage |
| `pytest -k "agent"` | Tests matching "agent" |
| `pytest tests/unit/api/` | Specific directory |

Happy Testing! 🚀
