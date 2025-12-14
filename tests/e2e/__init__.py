# tests/e2e/__init__.py
"""
End-to-end tests for complete workflows.

E2E tests verify complete user workflows and scenarios from start to finish.
They test the application as a whole, including API endpoints, database
interactions, and business logic.

Guidelines:
- Test complete user journeys
- Use real database connections (test DB)
- Test via HTTP API (using async_client fixture)
- Verify entire workflow from request to response
- Include realistic test data
- Test happy paths and error scenarios
"""
