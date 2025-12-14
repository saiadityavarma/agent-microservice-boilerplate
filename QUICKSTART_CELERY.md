# Quick Start Guide - Background Jobs with Celery

Get up and running with the Agent Service background jobs system in 5 minutes.

## Prerequisites

Install required dependencies:

```bash
pip install celery[redis] redis flower
```

## Step 1: Start Redis

Choose one method:

### Option A: Docker (Recommended)
```bash
docker run -d -p 6379:6379 --name redis redis:alpine
```

### Option B: Homebrew (macOS)
```bash
brew install redis
brew services start redis
```

### Option C: apt (Ubuntu/Debian)
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

Verify Redis is running:
```bash
redis-cli ping
# Should respond: PONG
```

## Step 2: Configure Environment

Add to your `.env` file:

```bash
# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
CELERY_TASK_DEFAULT_QUEUE=agent-service
```

## Step 3: Start Services

Open 4 terminal windows:

### Terminal 1: FastAPI Server
```bash
uvicorn agent_service.main:app --reload
```

### Terminal 2: Celery Worker
```bash
celery -A agent_service.workers.celery_app worker --loglevel=info
```

### Terminal 3: Celery Beat (Optional - for periodic tasks)
```bash
celery -A agent_service.workers.celery_app beat --loglevel=info
```

### Terminal 4: Flower Monitoring UI (Optional)
```bash
celery -A agent_service.workers.celery_app flower
```

## Step 4: Test the System

### Test 1: Async Agent Invocation

```bash
# Queue a task
curl -X POST http://localhost:8000/api/v1/agents/simple_llm_agent/invoke-async \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the capital of France?"}' \
  | jq

# Response:
# {
#   "task_id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "queued",
#   "status_url": "/api/v1/agents/tasks/550e8400-e29b-41d4-a716-446655440000"
# }

# Check task status (replace with your task_id)
curl http://localhost:8000/api/v1/agents/tasks/550e8400-e29b-41d4-a716-446655440000 | jq
```

### Test 2: Manual Task Trigger (Python)

```python
from agent_service.workers.tasks.agent_tasks import invoke_agent_async

# Queue task
task = invoke_agent_async.delay(
    agent_id="simple_llm_agent",
    message="Hello, how are you?",
    user_id="test_user"
)

# Get task ID
print(f"Task ID: {task.id}")

# Wait for result (blocking)
result = task.get(timeout=30)
print(f"Result: {result}")
```

### Test 3: Cleanup Tasks

```python
from agent_service.workers.tasks.cleanup_tasks import cleanup_expired_sessions

# Trigger session cleanup
task = cleanup_expired_sessions.delay()
result = task.get(timeout=60)
print(f"Deleted {result['deleted_count']} sessions")
```

## Step 5: Monitor Tasks

### Option A: Flower UI
1. Open http://localhost:5555
2. View active tasks, worker status, and task history

### Option B: Celery CLI
```bash
# View active tasks
celery -A agent_service.workers.celery_app inspect active

# View registered tasks
celery -A agent_service.workers.celery_app inspect registered

# View worker statistics
celery -A agent_service.workers.celery_app inspect stats
```

### Option C: Python API
```python
from agent_service.workers.celery_app import get_task_info

# Get task information
info = get_task_info("your-task-id-here")
print(info)
```

## Step 6: View API Documentation

Open http://localhost:8000/docs to see:
- Enhanced OpenAPI documentation
- New async endpoints
- Request/response examples
- Authentication schemes

## Common Commands

### Worker Management

```bash
# Start worker with specific queue
celery -A agent_service.workers.celery_app worker -Q agent-tasks --loglevel=info

# Start worker with concurrency
celery -A agent_service.workers.celery_app worker --concurrency=4 --loglevel=info

# Restart worker gracefully
celery -A agent_service.workers.celery_app control shutdown
# Then start again
```

### Task Management

```bash
# Purge all tasks (development only!)
celery -A agent_service.workers.celery_app purge

# Revoke task
celery -A agent_service.workers.celery_app control revoke <task-id>

# Inspect active queues
celery -A agent_service.workers.celery_app inspect active_queues
```

## Troubleshooting

### Redis Connection Failed
```bash
# Check if Redis is running
redis-cli ping

# Check Redis logs
docker logs redis  # If using Docker
tail -f /usr/local/var/log/redis.log  # If using Homebrew
```

### Worker Not Starting
```bash
# Check configuration
celery -A agent_service.workers.celery_app inspect conf

# Run with debug logging
celery -A agent_service.workers.celery_app worker --loglevel=debug
```

### Tasks Not Executing
```bash
# Check if worker is listening to correct queue
celery -A agent_service.workers.celery_app inspect active_queues

# Check task registration
celery -A agent_service.workers.celery_app inspect registered
```

## Next Steps

1. Read `/src/agent_service/workers/README.md` for detailed documentation
2. Read `IMPLEMENTATION_SUMMARY.md` for complete implementation details
3. Configure systemd services for production deployment
4. Set up monitoring and alerting
5. Customize retry policies and rate limits

## File Locations

### Configuration
- Settings: `/src/agent_service/config/settings.py`
- Celery App: `/src/agent_service/workers/celery_app.py`

### Tasks
- Agent Tasks: `/src/agent_service/workers/tasks/agent_tasks.py`
- Cleanup Tasks: `/src/agent_service/workers/tasks/cleanup_tasks.py`

### API Routes
- Agent Routes: `/src/agent_service/api/routes/agents.py`
- API Configuration: `/src/agent_service/api/app.py`

### Documentation
- Workers README: `/src/agent_service/workers/README.md`
- Implementation Summary: `/IMPLEMENTATION_SUMMARY.md`
- This Guide: `/QUICKSTART_CELERY.md`

## Production Checklist

Before deploying to production:

- [ ] Configure systemd services for workers and beat
- [ ] Set up Redis persistence and backups
- [ ] Configure Sentry for error tracking
- [ ] Set up Prometheus metrics
- [ ] Configure proper rate limits
- [ ] Review and adjust worker concurrency
- [ ] Set up log aggregation
- [ ] Configure health checks
- [ ] Test failover scenarios
- [ ] Document operational procedures

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Read the comprehensive documentation in `/src/agent_service/workers/README.md`
3. Review Celery documentation: https://docs.celeryproject.org/
4. Check Redis documentation: https://redis.io/documentation

## Summary

You now have:
- ✅ Background job processing with Celery
- ✅ Async agent invocation endpoint
- ✅ Automated cleanup tasks
- ✅ Task monitoring with Flower
- ✅ Enhanced OpenAPI documentation
- ✅ Production-ready configuration

Happy task processing!
