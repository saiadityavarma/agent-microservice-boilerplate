"""
Cleanup and maintenance background tasks.

This module provides periodic tasks for:
- Session cleanup (delete expired sessions)
- Audit log archival (move old logs to archive storage)
- Token blacklist cleanup (remove expired blacklisted tokens)
- Temp file cleanup (delete temporary files older than threshold)

All cleanup tasks are designed to run periodically via Celery Beat.
They're configured in the beat_schedule in celery_app.py.
"""

import asyncio
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List

from celery import Task
from sqlalchemy import delete, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from agent_service.workers.celery_app import celery_app
from agent_service.infrastructure.database import db
from agent_service.infrastructure.database.models.session import Session
from agent_service.infrastructure.database.models.audit_log import AuditLog
from agent_service.infrastructure.cache.redis import get_redis_manager
from agent_service.config.settings import get_settings

settings = get_settings()


# ============================================================================
# Session Cleanup Tasks
# ============================================================================

@celery_app.task(
    bind=True,
    name="agent_service.workers.tasks.cleanup_tasks.cleanup_expired_sessions",
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
    time_limit=600,  # 10 minutes
    soft_time_limit=540,
)
def cleanup_expired_sessions(self: Task) -> Dict[str, Any]:
    """
    Clean up expired sessions from the database.

    This task:
    1. Finds all sessions older than the expiry threshold
    2. Deletes expired sessions
    3. Returns statistics about cleanup

    Runs: Every hour (configured in beat_schedule)

    Returns:
        Dictionary containing:
            - deleted_count: Number of sessions deleted
            - cutoff_time: The expiry cutoff time used
            - status: Task status
            - completed_at: When cleanup completed
    """
    started_at = datetime.utcnow()
    print(f"Starting session cleanup at {started_at}")

    async def cleanup():
        """Async cleanup implementation."""
        if not db._engine:
            print("Database not configured, skipping session cleanup")
            return {
                "deleted_count": 0,
                "status": "skipped",
                "reason": "database_not_configured",
            }

        # Calculate cutoff time
        cutoff_time = datetime.utcnow() - timedelta(hours=settings.session_expiry_hours)

        async with db.session() as session:
            try:
                # Find expired sessions
                stmt = select(Session).where(
                    Session.updated_at < cutoff_time
                )
                result = await session.execute(stmt)
                expired_sessions = result.scalars().all()

                # Delete expired sessions
                delete_stmt = delete(Session).where(
                    Session.updated_at < cutoff_time
                )
                result = await session.execute(delete_stmt)
                await session.commit()

                deleted_count = result.rowcount

                print(f"Deleted {deleted_count} expired sessions (cutoff: {cutoff_time})")

                return {
                    "deleted_count": deleted_count,
                    "cutoff_time": cutoff_time.isoformat(),
                    "status": "success",
                }

            except Exception as e:
                await session.rollback()
                print(f"Error during session cleanup: {e}")
                raise

    try:
        cleanup_result = asyncio.run(cleanup())

        return {
            **cleanup_result,
            "started_at": started_at.isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        print(f"Session cleanup failed: {e}")
        raise self.retry(exc=e, countdown=self.default_retry_delay)


# ============================================================================
# Audit Log Archival Tasks
# ============================================================================

@celery_app.task(
    bind=True,
    name="agent_service.workers.tasks.cleanup_tasks.archive_old_audit_logs",
    max_retries=3,
    default_retry_delay=600,  # 10 minutes
    time_limit=1800,  # 30 minutes
    soft_time_limit=1680,  # 28 minutes
)
def archive_old_audit_logs(self: Task) -> Dict[str, Any]:
    """
    Archive old audit logs beyond retention period.

    This task:
    1. Finds audit logs older than retention period
    2. Archives them to cold storage (e.g., S3, file system)
    3. Deletes archived logs from primary database
    4. Returns archival statistics

    Runs: Daily at 2 AM (configured in beat_schedule)

    Returns:
        Dictionary containing:
            - archived_count: Number of logs archived
            - deleted_count: Number of logs deleted from DB
            - archive_path: Path where logs were archived
            - cutoff_time: The retention cutoff time used
            - status: Task status
    """
    started_at = datetime.utcnow()
    print(f"Starting audit log archival at {started_at}")

    async def archive():
        """Async archival implementation."""
        if not db._engine:
            print("Database not configured, skipping audit log archival")
            return {
                "archived_count": 0,
                "deleted_count": 0,
                "status": "skipped",
                "reason": "database_not_configured",
            }

        # Calculate cutoff time (retention period)
        cutoff_time = datetime.utcnow() - timedelta(days=settings.audit_log_retention_days)

        async with db.session() as session:
            try:
                # Find old audit logs
                stmt = select(AuditLog).where(
                    AuditLog.timestamp < cutoff_time
                )
                result = await session.execute(stmt)
                old_logs = result.scalars().all()

                archived_count = len(old_logs)

                if archived_count == 0:
                    print("No audit logs to archive")
                    return {
                        "archived_count": 0,
                        "deleted_count": 0,
                        "status": "success",
                        "message": "no_logs_to_archive",
                    }

                # Archive to file system (in production, use S3 or similar)
                archive_dir = Path("/tmp/audit_logs_archive")
                archive_dir.mkdir(parents=True, exist_ok=True)

                archive_filename = f"audit_logs_{cutoff_time.strftime('%Y%m%d')}.jsonl"
                archive_path = archive_dir / archive_filename

                # Write logs to archive file (JSONL format)
                import json
                with open(archive_path, "w") as f:
                    for log in old_logs:
                        log_data = {
                            "id": str(log.id),
                            "user_id": str(log.user_id) if log.user_id else None,
                            "action": log.action,
                            "resource_type": log.resource_type,
                            "resource_id": log.resource_id,
                            "timestamp": log.timestamp.isoformat(),
                            "ip_address": log.ip_address,
                            "user_agent": log.user_agent,
                            "request_id": log.request_id,
                            "metadata": log.metadata,
                        }
                        f.write(json.dumps(log_data) + "\n")

                print(f"Archived {archived_count} logs to {archive_path}")

                # Delete archived logs from database
                delete_stmt = delete(AuditLog).where(
                    AuditLog.timestamp < cutoff_time
                )
                result = await session.execute(delete_stmt)
                await session.commit()

                deleted_count = result.rowcount

                print(f"Deleted {deleted_count} archived logs from database")

                return {
                    "archived_count": archived_count,
                    "deleted_count": deleted_count,
                    "archive_path": str(archive_path),
                    "cutoff_time": cutoff_time.isoformat(),
                    "status": "success",
                }

            except Exception as e:
                await session.rollback()
                print(f"Error during audit log archival: {e}")
                raise

    try:
        archival_result = asyncio.run(archive())

        return {
            **archival_result,
            "started_at": started_at.isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        print(f"Audit log archival failed: {e}")
        raise self.retry(exc=e, countdown=self.default_retry_delay)


# ============================================================================
# Token Blacklist Cleanup Tasks
# ============================================================================

@celery_app.task(
    bind=True,
    name="agent_service.workers.tasks.cleanup_tasks.cleanup_token_blacklist",
    max_retries=3,
    default_retry_delay=300,
    time_limit=300,  # 5 minutes
    soft_time_limit=270,
)
def cleanup_token_blacklist(self: Task) -> Dict[str, Any]:
    """
    Clean up expired tokens from the blacklist.

    This task:
    1. Connects to Redis
    2. Scans for blacklisted tokens
    3. Removes expired tokens
    4. Returns cleanup statistics

    Runs: Every 6 hours (configured in beat_schedule)

    Returns:
        Dictionary containing:
            - removed_count: Number of tokens removed
            - scanned_count: Number of tokens scanned
            - status: Task status
    """
    started_at = datetime.utcnow()
    print(f"Starting token blacklist cleanup at {started_at}")

    async def cleanup():
        """Async cleanup implementation."""
        redis_manager = await get_redis_manager()

        if not redis_manager.is_available:
            print("Redis not available, skipping token blacklist cleanup")
            return {
                "removed_count": 0,
                "scanned_count": 0,
                "status": "skipped",
                "reason": "redis_not_available",
            }

        try:
            # Get all blacklisted token keys
            pattern = "blacklist:token:*"
            keys = await redis_manager.client.keys(pattern)

            scanned_count = len(keys)
            removed_count = 0

            # Check each token and remove if expired
            for key in keys:
                ttl = await redis_manager.client.ttl(key)
                if ttl == -1:  # No expiry set (shouldn't happen, but clean up anyway)
                    await redis_manager.client.delete(key)
                    removed_count += 1
                elif ttl == -2:  # Key doesn't exist
                    removed_count += 1

            print(f"Cleaned up {removed_count} expired tokens from blacklist (scanned {scanned_count})")

            return {
                "removed_count": removed_count,
                "scanned_count": scanned_count,
                "status": "success",
            }

        except Exception as e:
            print(f"Error during token blacklist cleanup: {e}")
            raise

    try:
        cleanup_result = asyncio.run(cleanup())

        return {
            **cleanup_result,
            "started_at": started_at.isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        print(f"Token blacklist cleanup failed: {e}")
        raise self.retry(exc=e, countdown=self.default_retry_delay)


# ============================================================================
# Temporary File Cleanup Tasks
# ============================================================================

@celery_app.task(
    bind=True,
    name="agent_service.workers.tasks.cleanup_tasks.cleanup_temp_files",
    max_retries=3,
    default_retry_delay=300,
    time_limit=600,  # 10 minutes
    soft_time_limit=540,
)
def cleanup_temp_files(
    self: Task,
    temp_dir: str = "/tmp/agent_service",
    max_age_hours: int = 24,
) -> Dict[str, Any]:
    """
    Clean up temporary files older than threshold.

    This task:
    1. Scans the temporary directory
    2. Identifies files older than max_age_hours
    3. Deletes old files and empty directories
    4. Returns cleanup statistics

    Runs: Daily at 3 AM (configured in beat_schedule)

    Args:
        temp_dir: Directory to clean (default: /tmp/agent_service)
        max_age_hours: Maximum file age in hours (default: 24)

    Returns:
        Dictionary containing:
            - deleted_files: Number of files deleted
            - deleted_dirs: Number of directories deleted
            - freed_bytes: Total bytes freed
            - status: Task status
    """
    started_at = datetime.utcnow()
    print(f"Starting temp file cleanup at {started_at}")

    try:
        temp_path = Path(temp_dir)

        if not temp_path.exists():
            print(f"Temp directory {temp_dir} does not exist, nothing to clean")
            return {
                "deleted_files": 0,
                "deleted_dirs": 0,
                "freed_bytes": 0,
                "status": "skipped",
                "reason": "directory_not_found",
                "started_at": started_at.isoformat(),
                "completed_at": datetime.utcnow().isoformat(),
            }

        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        deleted_files = 0
        deleted_dirs = 0
        freed_bytes = 0

        # Walk through directory
        for root, dirs, files in os.walk(temp_dir, topdown=False):
            # Delete old files
            for filename in files:
                filepath = Path(root) / filename
                try:
                    file_mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                    if file_mtime < cutoff_time:
                        file_size = filepath.stat().st_size
                        filepath.unlink()
                        deleted_files += 1
                        freed_bytes += file_size
                        print(f"Deleted old file: {filepath}")
                except Exception as e:
                    print(f"Error deleting file {filepath}: {e}")

            # Delete empty directories
            for dirname in dirs:
                dirpath = Path(root) / dirname
                try:
                    if not any(dirpath.iterdir()):  # Directory is empty
                        dirpath.rmdir()
                        deleted_dirs += 1
                        print(f"Deleted empty directory: {dirpath}")
                except Exception as e:
                    print(f"Error deleting directory {dirpath}: {e}")

        print(f"Cleanup complete: deleted {deleted_files} files, {deleted_dirs} dirs, freed {freed_bytes} bytes")

        return {
            "deleted_files": deleted_files,
            "deleted_dirs": deleted_dirs,
            "freed_bytes": freed_bytes,
            "freed_mb": round(freed_bytes / 1024 / 1024, 2),
            "temp_dir": temp_dir,
            "max_age_hours": max_age_hours,
            "cutoff_time": cutoff_time.isoformat(),
            "status": "success",
            "started_at": started_at.isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        print(f"Temp file cleanup failed: {e}")
        raise self.retry(exc=e, countdown=self.default_retry_delay)


# ============================================================================
# Task Exports
# ============================================================================

__all__ = [
    "cleanup_expired_sessions",
    "archive_old_audit_logs",
    "cleanup_token_blacklist",
    "cleanup_temp_files",
]
