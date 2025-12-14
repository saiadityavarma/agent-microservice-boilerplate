# tests/integration/test_database.py
"""Integration tests for database repository operations."""

import pytest
from uuid import uuid4
from sqlalchemy import select

from agent_service.infrastructure.database.models.audit_log import AuditLog


@pytest.mark.integration
@pytest.mark.requires_db
class TestDatabaseConnection:
    """Test database connection and basic operations."""

    async def test_database_connection(self, db_session):
        """Test that database connection is established."""
        # Execute a simple query
        result = await db_session.execute(select(1))
        value = result.scalar()

        assert value == 1

    async def test_database_transaction_commit(self, db_session):
        """Test database transaction commit."""
        # Create audit log
        log = AuditLog(
            id=uuid4(),
            user_id="test-user",
            action="TEST_ACTION",
            resource_type="test",
            resource_id="test-123"
        )

        db_session.add(log)
        await db_session.commit()

        # Verify it exists
        result = await db_session.execute(
            select(AuditLog).where(AuditLog.user_id == "test-user")
        )
        found_log = result.scalar_one_or_none()

        assert found_log is not None
        assert found_log.action == "TEST_ACTION"

    async def test_database_transaction_rollback(self, db_session):
        """Test database transaction rollback."""
        log_id = uuid4()

        # Create audit log
        log = AuditLog(
            id=log_id,
            user_id="rollback-test",
            action="TEST_ROLLBACK",
            resource_type="test",
            resource_id="rollback-123"
        )

        db_session.add(log)
        await db_session.rollback()

        # Verify it doesn't exist
        result = await db_session.execute(
            select(AuditLog).where(AuditLog.id == log_id)
        )
        found_log = result.scalar_one_or_none()

        assert found_log is None


@pytest.mark.integration
@pytest.mark.requires_db
class TestAuditLogRepository:
    """Test audit log repository operations."""

    async def test_create_audit_log(self, db_session):
        """Test creating audit log entry."""
        log = AuditLog(
            id=uuid4(),
            user_id="user-123",
            action="CREATE_RESOURCE",
            resource_type="agent",
            resource_id="agent-456",
            metadata={"key": "value"}
        )

        db_session.add(log)
        await db_session.commit()

        # Verify
        result = await db_session.execute(
            select(AuditLog).where(AuditLog.resource_id == "agent-456")
        )
        found = result.scalar_one_or_none()

        assert found is not None
        assert found.action == "CREATE_RESOURCE"
        assert found.metadata["key"] == "value"

    async def test_query_audit_logs_by_user(self, db_session):
        """Test querying audit logs by user ID."""
        user_id = f"query-test-{uuid4()}"

        # Create multiple logs
        for i in range(3):
            log = AuditLog(
                id=uuid4(),
                user_id=user_id,
                action=f"ACTION_{i}",
                resource_type="test",
                resource_id=f"resource-{i}"
            )
            db_session.add(log)

        await db_session.commit()

        # Query logs
        result = await db_session.execute(
            select(AuditLog).where(AuditLog.user_id == user_id)
        )
        logs = result.scalars().all()

        assert len(logs) == 3

    async def test_query_audit_logs_by_action(self, db_session):
        """Test querying audit logs by action type."""
        action_type = "SPECIFIC_ACTION"

        # Create log
        log = AuditLog(
            id=uuid4(),
            user_id="user-action-test",
            action=action_type,
            resource_type="test",
            resource_id="test-123"
        )
        db_session.add(log)
        await db_session.commit()

        # Query
        result = await db_session.execute(
            select(AuditLog).where(AuditLog.action == action_type)
        )
        found = result.scalar_one_or_none()

        assert found is not None
        assert found.action == action_type


@pytest.mark.integration
@pytest.mark.requires_db
class TestAPIKeyRepository:
    """Test API key repository operations."""

    async def test_create_api_key(self, db_session):
        """Test creating API key."""
        from agent_service.auth.services.api_key_service import APIKeyService

        service = APIKeyService(db_session)

        api_key = await service.create_api_key(
            user_id="user-create-test",
            name="Test API Key",
            scopes=["read", "write"]
        )

        assert api_key is not None
        assert api_key.name == "Test API Key"
        assert api_key.is_active is True

    async def test_validate_api_key(self, db_session):
        """Test validating API key."""
        from agent_service.auth.services.api_key_service import APIKeyService

        service = APIKeyService(db_session)

        # Create key
        created = await service.create_api_key(
            user_id="user-validate-test",
            name="Validation Key",
            scopes=["read"]
        )

        # Validate
        validated = await service.validate_key(created.key)

        assert validated is not None
        assert validated.id == created.id

    async def test_revoke_api_key(self, db_session):
        """Test revoking API key."""
        from agent_service.auth.services.api_key_service import APIKeyService

        service = APIKeyService(db_session)

        # Create key
        api_key = await service.create_api_key(
            user_id="user-revoke-test",
            name="Revoke Key",
            scopes=["read"]
        )

        # Revoke
        success = await service.revoke_key(api_key.key)

        assert success is True

        # Validate should fail
        validated = await service.validate_key(api_key.key)
        assert validated is None or validated.is_active is False

    async def test_list_user_api_keys(self, db_session):
        """Test listing user's API keys."""
        from agent_service.auth.services.api_key_service import APIKeyService

        service = APIKeyService(db_session)
        user_id = f"list-test-{uuid4()}"

        # Create multiple keys
        for i in range(3):
            await service.create_api_key(
                user_id=user_id,
                name=f"Key {i}",
                scopes=["read"]
            )

        # List keys
        keys = await service.list_user_keys(user_id)

        assert len(keys) >= 3


@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.slow
class TestDatabasePerformance:
    """Test database performance characteristics."""

    async def test_bulk_insert_performance(self, db_session):
        """Test bulk insert performance."""
        import time

        # Create 100 audit logs
        start = time.time()

        logs = []
        for i in range(100):
            logs.append(AuditLog(
                id=uuid4(),
                user_id=f"bulk-user-{i}",
                action="BULK_ACTION",
                resource_type="test",
                resource_id=f"bulk-{i}"
            ))

        db_session.add_all(logs)
        await db_session.commit()

        duration = time.time() - start

        # Should complete in reasonable time (< 5 seconds)
        assert duration < 5.0

    async def test_concurrent_transactions(self, db_session):
        """Test concurrent transaction handling."""
        import asyncio

        async def create_log(user_id: str):
            log = AuditLog(
                id=uuid4(),
                user_id=user_id,
                action="CONCURRENT_ACTION",
                resource_type="test",
                resource_id=f"concurrent-{user_id}"
            )
            db_session.add(log)
            await db_session.commit()

        # Create 10 logs concurrently
        tasks = [create_log(f"concurrent-{i}") for i in range(10)]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Verify logs were created
        result = await db_session.execute(
            select(AuditLog).where(AuditLog.action == "CONCURRENT_ACTION")
        )
        logs = result.scalars().all()

        # Should have created most/all logs
        assert len(logs) >= 8


@pytest.mark.integration
@pytest.mark.requires_db
class TestDatabaseMigrations:
    """Test database migration compatibility."""

    async def test_audit_log_table_exists(self, db_session):
        """Test that audit_log table exists."""
        from sqlalchemy import inspect

        # Get inspector
        inspector = inspect(db_session.get_bind())

        # Check if table exists
        tables = await db_session.run_sync(lambda sync_session: inspector.get_table_names())

        assert "audit_logs" in tables or "audit_log" in tables

    async def test_database_schema_valid(self, db_session):
        """Test that database schema is valid."""
        # Try to query each known table
        try:
            await db_session.execute(select(AuditLog))
            schema_valid = True
        except Exception:
            schema_valid = False

        assert schema_valid is True
