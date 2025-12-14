"""
Background workers module for asynchronous task processing.

This module provides Celery-based background job processing for:
- Long-running agent invocations
- Scheduled maintenance tasks
- Cleanup operations
- Data archival

Start a worker with:
    celery -A agent_service.workers.celery_app worker --loglevel=info

Start the beat scheduler for periodic tasks:
    celery -A agent_service.workers.celery_app beat --loglevel=info

Monitor tasks:
    celery -A agent_service.workers.celery_app flower
"""

from agent_service.workers.celery_app import celery_app

__all__ = ["celery_app"]
