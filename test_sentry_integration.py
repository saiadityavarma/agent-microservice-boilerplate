#!/usr/bin/env python3
"""
Standalone test for Sentry error tracking integration.

This script validates that the Sentry integration is properly configured
and all functions work as expected.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def test_error_tracking_module():
    """Test that the error tracking module can be imported."""
    print("Testing error tracking module import...")

    # Import the module directly, not via __init__.py to avoid other module issues
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "error_tracking",
        os.path.join(os.path.dirname(__file__), 'src', 'agent_service', 'infrastructure', 'observability', 'error_tracking.py')
    )
    error_tracking = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(error_tracking)

    print("✓ Error tracking module imported successfully")

    # Check if Sentry SDK is available
    print(f"  - Sentry SDK available: {error_tracking.SENTRY_AVAILABLE}")

    if not error_tracking.SENTRY_AVAILABLE:
        print("  ⚠ Sentry SDK not installed. Install with: pip install sentry-sdk[fastapi]")

    return error_tracking


def test_functions_exist(error_tracking):
    """Test that all required functions exist."""
    print("\nTesting function availability...")

    required_functions = [
        'init_sentry',
        'set_user_context',
        'set_request_context',
        'capture_exception',
        'capture_message',
        'clear_user_context',
        'add_breadcrumb',
        'set_tag',
        'set_context',
        'flush',
    ]

    for func_name in required_functions:
        assert hasattr(error_tracking, func_name), f"Missing function: {func_name}"
        print(f"  ✓ {func_name}")

    print("✓ All required functions are available")


def test_settings():
    """Test that Settings has Sentry configuration."""
    print("\nTesting Settings configuration...")

    from agent_service.config.settings import Settings

    settings = Settings()

    # Check that all Sentry settings exist
    assert hasattr(settings, 'sentry_dsn'), "Missing sentry_dsn setting"
    assert hasattr(settings, 'sentry_environment'), "Missing sentry_environment setting"
    assert hasattr(settings, 'sentry_sample_rate'), "Missing sentry_sample_rate setting"
    assert hasattr(settings, 'sentry_traces_sample_rate'), "Missing sentry_traces_sample_rate setting"

    print(f"  ✓ sentry_dsn: {settings.sentry_dsn or '(not set)'}")
    print(f"  ✓ sentry_environment: {settings.sentry_environment or '(not set)'}")
    print(f"  ✓ sentry_sample_rate: {settings.sentry_sample_rate}")
    print(f"  ✓ sentry_traces_sample_rate: {settings.sentry_traces_sample_rate}")

    # Validate default values
    assert settings.sentry_sample_rate == 1.0, "Unexpected sentry_sample_rate default"
    assert settings.sentry_traces_sample_rate == 0.1, "Unexpected sentry_traces_sample_rate default"

    print("✓ All Sentry settings are properly configured")


def test_initialization(error_tracking):
    """Test Sentry initialization."""
    print("\nTesting Sentry initialization...")

    # Test with no DSN (should return False but not crash)
    result = error_tracking.init_sentry(dsn=None)
    assert result is False, "Expected init_sentry(dsn=None) to return False"
    print("  ✓ init_sentry(dsn=None) correctly returns False")

    # Test with empty DSN (should return False but not crash)
    result = error_tracking.init_sentry(dsn="")
    assert result is False, "Expected init_sentry(dsn='') to return False"
    print("  ✓ init_sentry(dsn='') correctly returns False")

    print("✓ Sentry initialization works correctly")


def test_context_functions(error_tracking):
    """Test context management functions."""
    print("\nTesting context management functions...")

    # These should not crash even if Sentry is not available
    error_tracking.set_user_context(
        user_id="test_user_123",
        email="test@example.com",
        username="test_user",
    )
    print("  ✓ set_user_context() works")

    error_tracking.clear_user_context()
    print("  ✓ clear_user_context() works")

    error_tracking.add_breadcrumb(
        message="Test breadcrumb",
        category="test",
        level="info",
    )
    print("  ✓ add_breadcrumb() works")

    error_tracking.set_tag("test_tag", "test_value")
    print("  ✓ set_tag() works")

    error_tracking.set_context("test_context", {"key": "value"})
    print("  ✓ set_context() works")

    print("✓ All context management functions work correctly")


def test_capture_functions(error_tracking):
    """Test error and message capture functions."""
    print("\nTesting capture functions...")

    # Test capture_exception (should not crash even if Sentry is not available)
    try:
        raise ValueError("Test error")
    except ValueError as e:
        result = error_tracking.capture_exception(
            e,
            extra={"test": True},
            level="error",
        )
        # If Sentry is not available, should return None
        print(f"  ✓ capture_exception() returned: {result}")

    # Test capture_message
    result = error_tracking.capture_message(
        "Test message",
        level="info",
        extra={"test": True},
    )
    print(f"  ✓ capture_message() returned: {result}")

    print("✓ All capture functions work correctly")


def test_app_integration():
    """Test that app.py has Sentry integration."""
    print("\nTesting FastAPI app integration...")

    # Read app.py to check for integration
    app_path = os.path.join(os.path.dirname(__file__), 'src', 'agent_service', 'api', 'app.py')

    with open(app_path, 'r') as f:
        app_content = f.read()

    # Check for Sentry imports
    assert 'from agent_service.infrastructure.observability.error_tracking import' in app_content, \
        "Missing Sentry error_tracking import in app.py"
    assert 'init_sentry' in app_content, "Missing init_sentry in app.py"
    assert 'flush' in app_content, "Missing flush in app.py"

    # Check for initialization in lifespan
    assert 'init_sentry(' in app_content, "Sentry not initialized in app.py"
    assert 'flush_sentry(' in app_content, "Sentry flush not called in app.py shutdown"

    print("  ✓ app.py imports error_tracking")
    print("  ✓ app.py calls init_sentry() at startup")
    print("  ✓ app.py calls flush_sentry() at shutdown")

    print("✓ FastAPI app is properly integrated with Sentry")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Sentry Error Tracking Integration Test")
    print("=" * 60)

    try:
        # Test 1: Module import
        error_tracking = test_error_tracking_module()

        # Test 2: Function availability
        test_functions_exist(error_tracking)

        # Test 3: Settings configuration
        test_settings()

        # Test 4: Initialization
        test_initialization(error_tracking)

        # Test 5: Context functions
        test_context_functions(error_tracking)

        # Test 6: Capture functions
        test_capture_functions(error_tracking)

        # Test 7: App integration
        test_app_integration()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nSentry error tracking integration is ready to use.")
        print("\nTo enable Sentry, set the following environment variables:")
        print("  SENTRY_DSN=https://your-key@sentry.io/your-project-id")
        print("  SENTRY_ENVIRONMENT=production")
        print("\nSee ERROR_TRACKING_README.md for complete documentation.")

        return 0

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
