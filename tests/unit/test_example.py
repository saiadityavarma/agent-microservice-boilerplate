# tests/unit/test_example.py
"""
Example unit tests demonstrating test infrastructure usage.

These tests show how to:
- Write simple unit tests
- Use fixtures
- Test async functions
- Mock dependencies
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch


# ============================================================================
# Basic Unit Tests
# ============================================================================

def test_basic_assertion():
    """Basic test example."""
    assert 1 + 1 == 2


def test_with_fixture(test_settings):
    """Test using the test_settings fixture."""
    assert test_settings.app_name == "Agent Service Test"
    assert test_settings.debug is True
    assert test_settings.environment == "local"


# ============================================================================
# Async Unit Tests
# ============================================================================

async def test_async_function():
    """Example async test."""
    async def async_add(a: int, b: int) -> int:
        return a + b

    result = await async_add(2, 3)
    assert result == 5


async def test_async_with_mock():
    """Test async function with mock."""
    mock_service = AsyncMock()
    mock_service.fetch_data.return_value = {"status": "success"}

    result = await mock_service.fetch_data()
    assert result["status"] == "success"
    mock_service.fetch_data.assert_called_once()


# ============================================================================
# Testing with Mocks
# ============================================================================

def test_with_mock():
    """Test using unittest.mock."""
    mock_obj = Mock()
    mock_obj.method.return_value = 42

    result = mock_obj.method()
    assert result == 42
    mock_obj.method.assert_called_once()


@patch("agent_service.config.settings.get_settings")
def test_with_patch(mock_get_settings, test_settings):
    """Test using patch decorator."""
    mock_get_settings.return_value = test_settings

    from agent_service.config.settings import get_settings
    settings = get_settings()

    assert settings.app_name == "Agent Service Test"


# ============================================================================
# Parameterized Tests
# ============================================================================

@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
    (4, 8),
])
def test_parameterized(input, expected):
    """Example of parameterized test."""
    assert input * 2 == expected


@pytest.mark.parametrize("email", [
    "test@example.com",
    "user@domain.co.uk",
    "admin@test.org",
])
def test_email_validation(email):
    """Test email validation with different inputs."""
    assert "@" in email
    assert "." in email


# ============================================================================
# Testing Exceptions
# ============================================================================

def test_exception_raised():
    """Test that an exception is raised."""
    with pytest.raises(ValueError, match="invalid value"):
        raise ValueError("invalid value")


async def test_async_exception():
    """Test async exception handling."""
    async def failing_function():
        raise RuntimeError("Something went wrong")

    with pytest.raises(RuntimeError):
        await failing_function()


# ============================================================================
# Skip and Mark Tests
# ============================================================================

@pytest.mark.skip(reason="Demonstration of skipping tests")
def test_skipped():
    """This test will be skipped."""
    assert False


@pytest.mark.skipif(True, reason="Conditional skip demonstration")
def test_conditionally_skipped():
    """This test will be conditionally skipped."""
    assert False


# ============================================================================
# Custom Markers (define in pytest.ini)
# ============================================================================

@pytest.mark.slow
def test_slow_operation():
    """
    Example of custom marker for slow tests.

    Run with: pytest -m slow
    Skip with: pytest -m "not slow"
    """
    import time
    time.sleep(0.1)
    assert True
