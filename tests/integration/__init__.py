# tests/integration/__init__.py
"""
Integration tests for component interactions.

Integration tests verify that different parts of the application work
together correctly. They may use real database connections (test DB)
but should still mock external APIs and services.

Guidelines:
- Test interactions between components
- Use test database (with auto-rollback)
- Mock external services (APIs, third-party services)
- Test error handling and edge cases
- Keep tests independent and isolated
"""
