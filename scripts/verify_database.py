#!/usr/bin/env python3
"""
Database Infrastructure Verification Script

This script verifies that the database infrastructure is properly configured
and all components are working correctly.

Usage:
    python scripts/verify_database.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from agent_service.config.settings import get_settings
from agent_service.infrastructure.database import db
from agent_service.infrastructure.database.models import (
    User, Session, AuthProvider, SessionStatus
)
from agent_service.auth.models.api_key import APIKey


async def verify_connection():
    """Verify database connection."""
    print("1. Verifying database connection...")

    settings = get_settings()

    if not settings.database_url:
        print("   ERROR: DATABASE_URL not configured")
        return False

    try:
        await db.connect(
            url=settings.database_url.get_secret_value(),
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_recycle=settings.db_pool_recycle,
            pool_pre_ping=True,
            echo_sql=settings.db_echo_sql,
        )
        print(f"   SUCCESS: Connected to database")
        print(f"   Pool size: {settings.db_pool_size}")
        print(f"   Max overflow: {settings.db_max_overflow}")
        return True
    except Exception as e:
        print(f"   ERROR: Failed to connect - {e}")
        return False


async def verify_health_check():
    """Verify health check."""
    print("\n2. Verifying health check...")

    try:
        is_healthy = await db.health_check()
        if is_healthy:
            print("   SUCCESS: Health check passed")
            return True
        else:
            print("   ERROR: Health check failed")
            return False
    except Exception as e:
        print(f"   ERROR: Health check exception - {e}")
        return False


def verify_pool_stats():
    """Verify pool statistics."""
    print("\n3. Verifying pool statistics...")

    try:
        stats = db.get_pool_stats()
        print(f"   SUCCESS: Pool stats retrieved")
        print(f"   - Pool size: {stats['pool_size']}")
        print(f"   - Max overflow: {stats['max_overflow']}")
        print(f"   - Checked in: {stats['checked_in']}")
        print(f"   - Checked out: {stats['checked_out']}")
        print(f"   - Overflow: {stats['overflow']}")
        print(f"   - Total: {stats['total']}")
        return True
    except Exception as e:
        print(f"   ERROR: Failed to get pool stats - {e}")
        return False


async def verify_models():
    """Verify all models are properly defined."""
    print("\n4. Verifying database models...")

    try:
        # Check User model
        user = User(
            email="test@example.com",
            name="Test User",
            provider=AuthProvider.LOCAL,
            provider_user_id="test123",
            roles=["user"],
            groups=["test"],
            is_active=True
        )
        print("   SUCCESS: User model instantiated")

        # Check Session model
        session = Session(
            user_id=user.id,
            agent_id="test_agent",
            title="Test Session",
            status=SessionStatus.ACTIVE
        )
        session.add_message("user", "Test message")
        print("   SUCCESS: Session model instantiated")

        # Check APIKey model
        api_key = APIKey(
            user_id=user.id,
            name="Test Key",
            key_hash="0" * 64,
            key_prefix="sk_test",
            scopes=["read"],
            rate_limit_tier="free"
        )
        print("   SUCCESS: APIKey model instantiated")

        return True
    except Exception as e:
        print(f"   ERROR: Model verification failed - {e}")
        return False


async def verify_migrations():
    """Verify migrations are applied."""
    print("\n5. Verifying database migrations...")

    try:
        from sqlalchemy import text

        async with db.session() as session:
            # Check if alembic_version table exists
            result = await session.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_name = 'alembic_version'"
            ))
            table_exists = result.scalar() > 0

            if not table_exists:
                print("   WARNING: alembic_version table not found")
                print("   Run: alembic upgrade head")
                return False

            # Get current migration version
            result = await session.execute(text(
                "SELECT version_num FROM alembic_version"
            ))
            version = result.scalar()

            print(f"   SUCCESS: Migrations applied (version: {version})")

            # Check all tables exist
            required_tables = ['users', 'sessions', 'api_keys', 'audit_logs']
            for table in required_tables:
                result = await session.execute(text(
                    f"SELECT COUNT(*) FROM information_schema.tables "
                    f"WHERE table_name = '{table}'"
                ))
                exists = result.scalar() > 0
                if exists:
                    print(f"   SUCCESS: Table '{table}' exists")
                else:
                    print(f"   ERROR: Table '{table}' not found")
                    return False

            return True
    except Exception as e:
        print(f"   ERROR: Migration verification failed - {e}")
        print("   You may need to run: alembic upgrade head")
        return False


async def verify_crud_operations():
    """Verify basic CRUD operations."""
    print("\n6. Verifying CRUD operations...")

    try:
        from sqlalchemy import select
        from datetime import datetime

        # Create a test user
        async with db.session() as session:
            user = User(
                email=f"test_{datetime.utcnow().timestamp()}@example.com",
                name="Test User",
                provider=AuthProvider.LOCAL,
                provider_user_id=f"test_{datetime.utcnow().timestamp()}",
                roles=["user"],
                is_active=True
            )
            session.add(user)
            await session.commit()
            user_id = user.id
            print(f"   SUCCESS: Created test user (id: {user_id})")

        # Read the user
        async with db.session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one()
            print(f"   SUCCESS: Retrieved user (email: {user.email})")

        # Update the user
        async with db.session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one()
            user.name = "Updated Name"
            await session.commit()
            print("   SUCCESS: Updated user")

        # Soft delete the user
        async with db.session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one()
            user.soft_delete()
            await session.commit()
            print("   SUCCESS: Soft deleted user")

        # Verify soft delete
        async with db.session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one()
            assert user.is_deleted, "User should be soft deleted"
            print("   SUCCESS: Verified soft delete")

        return True
    except Exception as e:
        print(f"   ERROR: CRUD verification failed - {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Database Infrastructure Verification")
    print("=" * 60)

    results = []

    # Run all checks
    results.append(("Connection", await verify_connection()))

    if results[-1][1]:  # Only continue if connection succeeded
        results.append(("Health Check", await verify_health_check()))
        results.append(("Pool Stats", verify_pool_stats()))
        results.append(("Models", await verify_models()))
        results.append(("Migrations", await verify_migrations()))

        # Only run CRUD if migrations are applied
        if results[-1][1]:
            results.append(("CRUD Operations", await verify_crud_operations()))

    # Cleanup
    if db.is_connected:
        await db.disconnect()
        print("\n7. Database connection closed")

    # Summary
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)

    all_passed = True
    for check_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{check_name:20} {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\nSUCCESS: All checks passed!")
        return 0
    else:
        print("\nFAILURE: Some checks failed. See details above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
