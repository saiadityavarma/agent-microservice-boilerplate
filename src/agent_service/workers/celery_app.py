"""
Celery application configuration for background task processing.

This module configures Celery with:
- Redis broker and result backend
- Task routing and queues
- Retry configuration
- Rate limiting
- Error handling hooks
- Periodic task scheduling

Configuration is loaded from application settings.
"""

from celery import Celery, Task
from celery.schedules import crontab
from celery.signals import (
    task_prerun,
    task_postrun,
    task_failure,
    task_retry,
)
from kombu import Queue

from agent_service.config.settings import get_settings

settings = get_settings()


# ============================================================================
# Celery Application Configuration
# ============================================================================

celery_app = Celery(
    "agent_service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "agent_service.workers.tasks.agent_tasks",
        "agent_service.workers.tasks.cleanup_tasks",
    ],
)


# ============================================================================
# Celery Configuration
# ============================================================================

celery_app.conf.update(
    # Task Configuration
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task Execution
    task_default_queue=settings.celery_task_default_queue,
    task_default_retry_delay=settings.celery_task_default_retry_delay,
    task_time_limit=settings.celery_task_time_limit,
    task_soft_time_limit=settings.celery_task_soft_time_limit,
    task_acks_late=True,  # Acknowledge tasks after completion
    task_reject_on_worker_lost=True,  # Reject tasks if worker dies

    # Worker Configuration
    worker_prefetch_multiplier=settings.celery_worker_prefetch_multiplier,
    worker_max_tasks_per_child=settings.celery_worker_max_tasks_per_child,
    worker_disable_rate_limits=False,

    # Result Backend Configuration
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,  # Store additional task metadata
    result_backend_transport_options={
        "master_name": "mymaster",
        "visibility_timeout": 3600,
    },

    # Queue Configuration
    task_queues=(
        Queue(
            settings.celery_task_default_queue,
            routing_key=f"{settings.celery_task_default_queue}.#",
        ),
        Queue(
            "agent-tasks",
            routing_key="agent-tasks.#",
            # Rate limit: 100 tasks per minute
            queue_arguments={"x-max-priority": 10},
        ),
        Queue(
            "cleanup-tasks",
            routing_key="cleanup-tasks.#",
            # Lower priority for cleanup tasks
            queue_arguments={"x-max-priority": 5},
        ),
    ),

    # Task Routing
    task_routes={
        "agent_service.workers.tasks.agent_tasks.*": {
            "queue": "agent-tasks",
            "routing_key": "agent-tasks.invoke",
        },
        "agent_service.workers.tasks.cleanup_tasks.*": {
            "queue": "cleanup-tasks",
            "routing_key": "cleanup-tasks.maintenance",
        },
    },

    # Rate Limits (global)
    task_default_rate_limit="1000/m",  # 1000 tasks per minute by default

    # Error Handling
    task_track_started=True,  # Track when tasks start
    task_send_sent_event=True,  # Send task-sent events

    # Periodic Tasks (Beat Schedule)
    beat_schedule={
        # Session cleanup - runs every hour
        "cleanup-expired-sessions": {
            "task": "agent_service.workers.tasks.cleanup_tasks.cleanup_expired_sessions",
            "schedule": crontab(minute=0),  # Every hour at minute 0
            "options": {"queue": "cleanup-tasks"},
        },
        # Audit log archival - runs daily at 2 AM
        "archive-old-audit-logs": {
            "task": "agent_service.workers.tasks.cleanup_tasks.archive_old_audit_logs",
            "schedule": crontab(hour=2, minute=0),  # Daily at 2:00 AM
            "options": {"queue": "cleanup-tasks"},
        },
        # Token blacklist cleanup - runs every 6 hours
        "cleanup-token-blacklist": {
            "task": "agent_service.workers.tasks.cleanup_tasks.cleanup_token_blacklist",
            "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
            "options": {"queue": "cleanup-tasks"},
        },
        # Temp file cleanup - runs daily at 3 AM
        "cleanup-temp-files": {
            "task": "agent_service.workers.tasks.cleanup_tasks.cleanup_temp_files",
            "schedule": crontab(hour=3, minute=0),  # Daily at 3:00 AM
            "options": {"queue": "cleanup-tasks"},
        },
    },
)


# ============================================================================
# Custom Task Base Class
# ============================================================================

class BaseTask(Task):
    """
    Custom base task class with enhanced error handling and logging.

    All tasks should inherit from this class to get:
    - Automatic retry on failure
    - Error tracking integration
    - Logging with context
    - Timeout handling
    """

    autoretry_for = (Exception,)
    max_retries = settings.celery_task_max_retries
    retry_backoff = True  # Exponential backoff
    retry_backoff_max = 600  # Max 10 minutes between retries
    retry_jitter = True  # Add random jitter to backoff

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Handle task failure.

        Args:
            exc: The exception raised by the task
            task_id: Unique id of the failed task
            args: Positional arguments of the task
            kwargs: Keyword arguments of the task
            einfo: Exception info with traceback
        """
        print(f"Task {self.name}[{task_id}] failed: {exc}")
        # In production, send to error tracking service (Sentry)
        # sentry_sdk.capture_exception(exc)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """
        Handle task retry.

        Args:
            exc: The exception that caused the retry
            task_id: Unique id of the task
            args: Positional arguments of the task
            kwargs: Keyword arguments of the task
            einfo: Exception info with traceback
        """
        print(f"Task {self.name}[{task_id}] retry {self.request.retries}/{self.max_retries}: {exc}")

    def on_success(self, retval, task_id, args, kwargs):
        """
        Handle task success.

        Args:
            retval: The return value of the task
            task_id: Unique id of the task
            args: Positional arguments of the task
            kwargs: Keyword arguments of the task
        """
        print(f"Task {self.name}[{task_id}] succeeded")


# Set the default base task class
celery_app.Task = BaseTask


# ============================================================================
# Celery Signal Handlers
# ============================================================================

@task_prerun.connect
def task_prerun_handler(task_id, task, args, kwargs, **extra_kwargs):
    """
    Handler called before task execution.

    Use for:
    - Setting up task context
    - Logging task start
    - Initializing resources
    """
    print(f"Starting task {task.name}[{task_id}]")


@task_postrun.connect
def task_postrun_handler(task_id, task, args, kwargs, retval, **extra_kwargs):
    """
    Handler called after task execution.

    Use for:
    - Cleanup
    - Logging task completion
    - Resource disposal
    """
    print(f"Completed task {task.name}[{task_id}]")


@task_failure.connect
def task_failure_handler(task_id, exception, args, kwargs, traceback, einfo, **extra_kwargs):
    """
    Handler called when task fails.

    Use for:
    - Error reporting
    - Alerting
    - Cleanup after failure
    """
    print(f"Task {task_id} failed with exception: {exception}")


@task_retry.connect
def task_retry_handler(task_id, reason, einfo, **extra_kwargs):
    """
    Handler called when task is retried.

    Use for:
    - Logging retries
    - Tracking retry patterns
    - Alerting on excessive retries
    """
    print(f"Task {task_id} retry: {reason}")


# ============================================================================
# Utility Functions
# ============================================================================

def get_task_info(task_id: str) -> dict:
    """
    Get information about a task.

    Args:
        task_id: The task ID

    Returns:
        Dictionary with task information
    """
    result = celery_app.AsyncResult(task_id)

    return {
        "task_id": task_id,
        "state": result.state,
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else None,
        "failed": result.failed() if result.ready() else None,
        "result": result.result if result.ready() else None,
        "info": result.info,
    }


def revoke_task(task_id: str, terminate: bool = False) -> dict:
    """
    Revoke (cancel) a task.

    Args:
        task_id: The task ID to revoke
        terminate: If True, terminate the task immediately (use with caution)

    Returns:
        Dictionary with revocation status
    """
    celery_app.control.revoke(task_id, terminate=terminate)

    return {
        "task_id": task_id,
        "revoked": True,
        "terminated": terminate,
    }


# ============================================================================
# Application Export
# ============================================================================

__all__ = ["celery_app", "BaseTask", "get_task_info", "revoke_task"]
