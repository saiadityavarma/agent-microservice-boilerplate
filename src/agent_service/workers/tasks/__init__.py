"""
Background tasks module.

This module contains all Celery tasks organized by category:
- agent_tasks: Long-running agent invocations and processing
- cleanup_tasks: Maintenance and cleanup operations
"""

# Import tasks to register them with Celery
from agent_service.workers.tasks.agent_tasks import (
    invoke_agent_async,
    invoke_agent_with_streaming,
)
from agent_service.workers.tasks.cleanup_tasks import (
    cleanup_expired_sessions,
    archive_old_audit_logs,
    cleanup_token_blacklist,
    cleanup_temp_files,
)

__all__ = [
    # Agent tasks
    "invoke_agent_async",
    "invoke_agent_with_streaming",
    # Cleanup tasks
    "cleanup_expired_sessions",
    "archive_old_audit_logs",
    "cleanup_token_blacklist",
    "cleanup_temp_files",
]
