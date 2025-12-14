# Background Workers with Celery

This module provides asynchronous task processing using Celery for long-running operations and scheduled maintenance tasks.

## Overview

The workers module handles:
- **Agent Tasks**: Asynchronous agent invocations with progress tracking
- **Cleanup Tasks**: Scheduled maintenance operations (sessions, logs, cache)
- **Task Monitoring**: Status tracking and result retrieval

## Architecture

```
workers/
├── __init__.py              # Module exports
├── celery_app.py           # Celery configuration and setup
├── tasks/
│   ├── __init__.py         # Task registration
│   ├── agent_tasks.py      # Agent invocation tasks
│   └── cleanup_tasks.py    # Maintenance and cleanup tasks
└── README.md               # This file
```

## Prerequisites

### Install Dependencies

```bash
pip install celery[redis] redis
```

### Redis Server

Celery requires Redis as a message broker and result backend:

```bash
# macOS (using Homebrew)
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis:alpine
```

### Environment Configuration

Add to your `.env` file:

```bash
# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
CELERY_TASK_DEFAULT_QUEUE=agent-service

# Task Configuration
CELERY_TASK_DEFAULT_RETRY_DELAY=60
CELERY_TASK_MAX_RETRIES=3
CELERY_TASK_TIME_LIMIT=600
CELERY_TASK_SOFT_TIME_LIMIT=540

# Worker Configuration
CELERY_WORKER_PREFETCH_MULTIPLIER=4
CELERY_WORKER_MAX_TASKS_PER_CHILD=1000
```

## Running Workers

### Start a Worker

```bash
# Start worker with INFO logging
celery -A agent_service.workers.celery_app worker --loglevel=info

# Start worker with specific queue
celery -A agent_service.workers.celery_app worker --loglevel=info -Q agent-tasks

# Start worker with concurrency
celery -A agent_service.workers.celery_app worker --loglevel=info --concurrency=4

# Start worker in development (with auto-reload)
watchmedo auto-restart -d . -p '*.py' -- celery -A agent_service.workers.celery_app worker --loglevel=info
```

### Start Beat Scheduler (for Periodic Tasks)

```bash
# Start beat scheduler for periodic tasks
celery -A agent_service.workers.celery_app beat --loglevel=info
```

### Start Flower (Monitoring UI)

```bash
# Install flower
pip install flower

# Start monitoring UI (accessible at http://localhost:5555)
celery -A agent_service.workers.celery_app flower
```

### Production Setup (systemd)

Create `/etc/systemd/system/celery-worker.service`:

```ini
[Unit]
Description=Celery Worker
After=network.target redis.target

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/path/to/project
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/celery -A agent_service.workers.celery_app worker --loglevel=info --pidfile=/var/run/celery/%n.pid
ExecStop=/bin/kill -s TERM $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/celery-beat.service`:

```ini
[Unit]
Description=Celery Beat Scheduler
After=network.target redis.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/path/to/project
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/celery -A agent_service.workers.celery_app beat --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable celery-worker celery-beat
sudo systemctl start celery-worker celery-beat
sudo systemctl status celery-worker celery-beat
```

## Available Tasks

### Agent Tasks

#### 1. Async Agent Invocation

**Task:** `agent_service.workers.tasks.agent_tasks.invoke_agent_async`

Invokes an agent asynchronously and stores the result.

```python
from agent_service.workers.tasks.agent_tasks import invoke_agent_async

# Queue task
task = invoke_agent_async.delay(
    agent_id="simple_llm_agent",
    message="What is the capital of France?",
    user_id="user123",
    session_id="session_abc",
    metadata={"source": "api"}
)

# Get task ID
print(f"Task ID: {task.id}")

# Check status
result = task.get(timeout=10)  # Wait up to 10 seconds
```

**Configuration:**
- Rate limit: 100/minute
- Time limit: 10 minutes
- Max retries: 3

#### 2. Streaming Agent Invocation

**Task:** `agent_service.workers.tasks.agent_tasks.invoke_agent_with_streaming`

Invokes an agent with streaming and collects all chunks.

```python
from agent_service.workers.tasks.agent_tasks import invoke_agent_with_streaming

task = invoke_agent_with_streaming.delay(
    agent_id="simple_llm_agent",
    message="Write a long story...",
    user_id="user123"
)
```

**Configuration:**
- Rate limit: 50/minute
- Time limit: 15 minutes
- Max retries: 3

### Cleanup Tasks

#### 1. Session Cleanup

**Task:** `agent_service.workers.tasks.cleanup_tasks.cleanup_expired_sessions`

Deletes expired sessions from the database.

**Schedule:** Every hour
**Configuration:** `session_expiry_hours` (default: 24)

```python
from agent_service.workers.tasks.cleanup_tasks import cleanup_expired_sessions

# Manual trigger
result = cleanup_expired_sessions.delay()
```

#### 2. Audit Log Archival

**Task:** `agent_service.workers.tasks.cleanup_tasks.archive_old_audit_logs`

Archives old audit logs to cold storage and removes from primary database.

**Schedule:** Daily at 2:00 AM
**Configuration:** `audit_log_retention_days` (default: 90)

```python
from agent_service.workers.tasks.cleanup_tasks import archive_old_audit_logs

# Manual trigger
result = archive_old_audit_logs.delay()
```

#### 3. Token Blacklist Cleanup

**Task:** `agent_service.workers.tasks.cleanup_tasks.cleanup_token_blacklist`

Removes expired tokens from Redis blacklist.

**Schedule:** Every 6 hours

```python
from agent_service.workers.tasks.cleanup_tasks import cleanup_token_blacklist

# Manual trigger
result = cleanup_token_blacklist.delay()
```

#### 4. Temp File Cleanup

**Task:** `agent_service.workers.tasks.cleanup_tasks.cleanup_temp_files`

Deletes temporary files older than threshold.

**Schedule:** Daily at 3:00 AM
**Default:** Deletes files older than 24 hours from `/tmp/agent_service`

```python
from agent_service.workers.tasks.cleanup_tasks import cleanup_temp_files

# Manual trigger with custom settings
result = cleanup_temp_files.delay(
    temp_dir="/tmp/custom_dir",
    max_age_hours=48
)
```

## Task Monitoring

### Using Python API

```python
from agent_service.workers.celery_app import get_task_info, revoke_task

# Get task information
task_info = get_task_info("task-id-here")
print(task_info)
# {
#     "task_id": "...",
#     "state": "SUCCESS",
#     "ready": True,
#     "successful": True,
#     "result": {...}
# }

# Revoke (cancel) a task
revoke_task("task-id-here", terminate=False)

# Terminate a running task (use with caution)
revoke_task("task-id-here", terminate=True)
```

### Using REST API

```bash
# Queue async agent invocation
curl -X POST http://localhost:8000/api/v1/agents/simple_llm_agent/invoke-async \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, agent!"}'

# Response:
# {
#   "task_id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "queued",
#   "status_url": "/api/v1/agents/tasks/550e8400-e29b-41d4-a716-446655440000"
# }

# Check task status
curl http://localhost:8000/api/v1/agents/tasks/550e8400-e29b-41d4-a716-446655440000

# Response:
# {
#   "task_id": "550e8400-e29b-41d4-a716-446655440000",
#   "state": "SUCCESS",
#   "status": "completed",
#   "progress": 100,
#   "result": {
#     "content": "Hello! How can I help you?",
#     "metadata": {}
#   }
# }
```

### Using Flower UI

Access the monitoring dashboard at `http://localhost:5555`:

- View active tasks
- Monitor task progress
- Inspect task results
- View worker status
- Task graphs and statistics

## Queue Configuration

The system uses multiple queues for task organization:

### 1. Default Queue: `agent-service`
- General purpose tasks
- Default for all tasks

### 2. Agent Tasks Queue: `agent-tasks`
- Agent invocation tasks
- Priority: 10 (highest)
- Rate limit: 100/minute

### 3. Cleanup Tasks Queue: `cleanup-tasks`
- Maintenance and cleanup tasks
- Priority: 5 (lower)
- Runs in background

### Starting Workers for Specific Queues

```bash
# Agent tasks only
celery -A agent_service.workers.celery_app worker -Q agent-tasks --loglevel=info

# Cleanup tasks only
celery -A agent_service.workers.celery_app worker -Q cleanup-tasks --loglevel=info

# Multiple queues
celery -A agent_service.workers.celery_app worker -Q agent-tasks,cleanup-tasks --loglevel=info
```

## Error Handling

### Automatic Retries

Tasks automatically retry on failure with exponential backoff:

```python
# Default retry configuration
max_retries = 3
retry_backoff = True  # Exponential backoff
retry_backoff_max = 600  # Max 10 minutes
retry_jitter = True  # Add randomness
```

### Custom Error Handling

Tasks use the `BaseTask` class with hooks:

- `on_failure()`: Called when task fails
- `on_retry()`: Called when task is retried
- `on_success()`: Called when task succeeds

### Sentry Integration

Errors are automatically sent to Sentry (if configured):

```python
# In celery_app.py BaseTask
def on_failure(self, exc, task_id, args, kwargs, einfo):
    # Automatically captured by Sentry
    sentry_sdk.capture_exception(exc)
```

## Performance Tuning

### Worker Concurrency

```bash
# Prefork pool (default) - good for CPU-bound tasks
celery -A agent_service.workers.celery_app worker --concurrency=4

# Gevent pool - good for I/O-bound tasks
celery -A agent_service.workers.celery_app worker --pool=gevent --concurrency=100

# Solo pool - single process (debugging)
celery -A agent_service.workers.celery_app worker --pool=solo
```

### Task Prioritization

Tasks support priority levels:

```python
# High priority
task.apply_async(priority=9)

# Low priority
task.apply_async(priority=1)
```

### Rate Limiting

Configure per-task rate limits:

```python
@celery_app.task(rate_limit="10/m")  # 10 tasks per minute
def my_task():
    pass
```

## Troubleshooting

### Worker Not Starting

```bash
# Check Redis connection
redis-cli ping

# Verify configuration
celery -A agent_service.workers.celery_app inspect active

# Check logs
celery -A agent_service.workers.celery_app worker --loglevel=debug
```

### Tasks Not Executing

```bash
# Check worker status
celery -A agent_service.workers.celery_app inspect active_queues

# Purge all tasks (development only!)
celery -A agent_service.workers.celery_app purge

# Inspect registered tasks
celery -A agent_service.workers.celery_app inspect registered
```

### Memory Issues

```bash
# Restart workers after N tasks
celery -A agent_service.workers.celery_app worker --max-tasks-per-child=100

# Monitor memory usage
celery -A agent_service.workers.celery_app inspect stats
```

## Best Practices

1. **Task Design**
   - Keep tasks small and focused
   - Make tasks idempotent (safe to retry)
   - Avoid storing large data in task results
   - Use task chaining for complex workflows

2. **Error Handling**
   - Always handle exceptions
   - Use appropriate retry strategies
   - Log errors with context
   - Monitor task failures

3. **Performance**
   - Use appropriate worker pools
   - Configure concurrency based on workload
   - Monitor queue lengths
   - Use task priorities

4. **Monitoring**
   - Set up Flower for production
   - Monitor task execution times
   - Track task failure rates
   - Alert on queue buildup

## Additional Resources

- [Celery Documentation](https://docs.celeryproject.org/)
- [Redis Documentation](https://redis.io/documentation)
- [Flower Documentation](https://flower.readthedocs.io/)
- [Celery Best Practices](https://docs.celeryproject.org/en/stable/userguide/tasks.html#tips-and-best-practices)
