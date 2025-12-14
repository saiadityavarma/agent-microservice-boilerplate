# Agent Service - OpenAPI Enhancement & Background Jobs Implementation

This document summarizes the enhanced OpenAPI documentation and new Celery background jobs system implemented for the Agent Service.

## Overview

This implementation adds:

1. **Enhanced OpenAPI Documentation** with comprehensive metadata, tags, and examples
2. **Celery Background Jobs System** for asynchronous task processing
3. **New Async Agent Invocation Endpoint** for long-running operations
4. **Scheduled Cleanup Tasks** for maintenance operations

## 1. Enhanced OpenAPI Documentation

### Location
- `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/api/app.py`

### Enhancements

#### API Metadata
```python
app = FastAPI(
    title="Agent Service",
    version="0.1.0",
    description="""
    # Agent Service API

    A comprehensive, production-ready API service for managing AI agents...
    """,
    contact={
        "name": "API Support Team",
        "url": "https://example.com/support",
        "email": "support@example.com",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
    openapi_tags=[...]
)
```

#### Features Added
- **Detailed API Description**: Markdown-formatted description with features, authentication methods, and getting started guide
- **License Information**: Apache 2.0 license with URL
- **Contact Information**: Placeholder for support team contact
- **Organized Tags**: Each route group has descriptive tags:
  - Health
  - Authentication
  - Agents
  - API Keys
  - Protocols
  - Audit Logs
  - Background Jobs

#### Authentication Documentation

Two methods documented in OpenAPI:

1. **Bearer Token (JWT)**
   ```
   Authorization: Bearer <your-jwt-token>
   ```

2. **API Key**
   ```
   X-API-Key: sk_live_your_api_key
   ```

#### Enhanced Route Documentation

All routes now include:
- Detailed descriptions with examples
- Request/response schemas with examples
- Error response documentation (400, 401, 404, 429, etc.)
- Rate limiting information
- Authentication requirements

## 2. Celery Configuration

### Location
- `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/workers/celery_app.py`

### Features

#### Core Configuration
```python
celery_app = Celery(
    "agent_service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
```

#### Queue System
Three dedicated queues:
1. **agent-service** (default): General purpose
2. **agent-tasks**: Agent invocations (priority: 10)
3. **cleanup-tasks**: Maintenance tasks (priority: 5)

#### Task Configuration
- JSON serialization
- UTC timezone
- Task acknowledgment after completion
- Task rejection on worker loss
- 1-hour result expiration

#### Rate Limiting
- Global: 1000 tasks/minute
- Agent tasks: 100/minute
- Cleanup tasks: No specific limit

#### Retry Configuration
- Max retries: 3 (configurable)
- Exponential backoff
- Backoff max: 10 minutes
- Jitter enabled

#### Custom Base Task Class
```python
class BaseTask(Task):
    autoretry_for = (Exception,)
    max_retries = 3
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
```

Includes hooks:
- `on_failure()`: Error tracking
- `on_retry()`: Retry logging
- `on_success()`: Success logging

#### Signal Handlers
- `task_prerun`: Setup before execution
- `task_postrun`: Cleanup after execution
- `task_failure`: Error reporting
- `task_retry`: Retry tracking

#### Periodic Tasks (Beat Schedule)

| Task | Schedule | Purpose |
|------|----------|---------|
| cleanup_expired_sessions | Every hour | Delete expired sessions |
| archive_old_audit_logs | Daily at 2 AM | Archive old audit logs |
| cleanup_token_blacklist | Every 6 hours | Remove expired tokens |
| cleanup_temp_files | Daily at 3 AM | Delete old temp files |

## 3. Settings Configuration

### Location
- `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/config/settings.py`

### New Settings

```python
# Celery Background Jobs Settings
celery_broker_url: str = "redis://localhost:6379/1"
celery_result_backend: str = "redis://localhost:6379/2"
celery_task_default_queue: str = "agent-service"
celery_task_default_retry_delay: int = 60
celery_task_max_retries: int = 3
celery_task_time_limit: int = 600  # 10 minutes
celery_task_soft_time_limit: int = 540  # 9 minutes
celery_worker_prefetch_multiplier: int = 4
celery_worker_max_tasks_per_child: int = 1000
```

### Environment Variables

Add to `.env`:
```bash
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
CELERY_TASK_DEFAULT_QUEUE=agent-service
CELERY_TASK_DEFAULT_RETRY_DELAY=60
CELERY_TASK_MAX_RETRIES=3
CELERY_TASK_TIME_LIMIT=600
CELERY_TASK_SOFT_TIME_LIMIT=540
CELERY_WORKER_PREFETCH_MULTIPLIER=4
CELERY_WORKER_MAX_TASKS_PER_CHILD=1000
```

## 4. Agent Tasks

### Location
- `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/workers/tasks/agent_tasks.py`

### Tasks Implemented

#### 4.1 Async Agent Invocation

**Task:** `invoke_agent_async`

```python
@celery_app.task(
    bind=True,
    name="agent_service.workers.tasks.agent_tasks.invoke_agent_async",
    max_retries=3,
    rate_limit="100/m",
    time_limit=600,
    soft_time_limit=540,
)
def invoke_agent_async(
    self: Task,
    agent_id: str,
    message: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ...
```

**Features:**
- Retrieves agent from registry
- Invokes agent asynchronously
- Tracks progress (0%, 20%, 40%, 80%, 100%)
- Stores result in Redis cache
- Handles timeouts gracefully
- Returns structured result with metadata

**Usage:**
```python
from agent_service.workers.tasks.agent_tasks import invoke_agent_async

task = invoke_agent_async.delay(
    agent_id="simple_llm_agent",
    message="What is the capital of France?",
    user_id="user123"
)

print(f"Task ID: {task.id}")
```

#### 4.2 Streaming Agent Invocation

**Task:** `invoke_agent_with_streaming`

```python
@celery_app.task(
    bind=True,
    name="agent_service.workers.tasks.agent_tasks.invoke_agent_with_streaming",
    max_retries=3,
    rate_limit="50/m",
    time_limit=900,
    soft_time_limit=840,
)
def invoke_agent_with_streaming(...):
    ...
```

**Features:**
- Collects streaming chunks
- Updates progress every 10 chunks
- Stores intermediate chunks in cache
- Returns complete response with all chunks
- Handles partial responses on timeout

## 5. Cleanup Tasks

### Location
- `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/workers/tasks/cleanup_tasks.py`

### Tasks Implemented

#### 5.1 Session Cleanup

**Task:** `cleanup_expired_sessions`

**Schedule:** Every hour

**Purpose:** Delete sessions older than `session_expiry_hours` (default: 24)

**Returns:**
```json
{
  "deleted_count": 42,
  "cutoff_time": "2025-12-12T00:00:00",
  "status": "success",
  "started_at": "2025-12-13T01:00:00",
  "completed_at": "2025-12-13T01:00:15"
}
```

#### 5.2 Audit Log Archival

**Task:** `archive_old_audit_logs`

**Schedule:** Daily at 2:00 AM

**Purpose:** Archive logs older than `audit_log_retention_days` (default: 90)

**Features:**
- Exports logs to JSONL format
- Stores in `/tmp/audit_logs_archive/`
- Deletes archived logs from database
- Returns archival statistics

#### 5.3 Token Blacklist Cleanup

**Task:** `cleanup_token_blacklist`

**Schedule:** Every 6 hours

**Purpose:** Remove expired tokens from Redis blacklist

**Features:**
- Scans `blacklist:token:*` keys
- Removes expired entries
- Returns cleanup statistics

#### 5.4 Temp File Cleanup

**Task:** `cleanup_temp_files`

**Schedule:** Daily at 3:00 AM

**Purpose:** Delete temporary files older than threshold

**Default:** Deletes files older than 24 hours from `/tmp/agent_service`

**Returns:**
```json
{
  "deleted_files": 128,
  "deleted_dirs": 15,
  "freed_bytes": 1048576,
  "freed_mb": 1.0,
  "status": "success"
}
```

## 6. Enhanced Agent Routes

### Location
- `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/src/agent_service/api/routes/agents.py`

### New Endpoints

#### 6.1 POST /api/v1/agents/invoke

**Enhanced Features:**
- Comprehensive OpenAPI documentation
- Request/response models with validation
- Error response documentation
- Rate limiting information
- Example requests/responses

**Request:**
```json
{
  "message": "What is the capital of France?",
  "session_id": "session_123",
  "metadata": {"source": "web_app"}
}
```

**Response:**
```json
{
  "response": "The capital of France is Paris.",
  "metadata": {
    "model": "gpt-4",
    "tokens_used": 45
  }
}
```

#### 6.2 POST /api/v1/agents/stream

**Enhanced Features:**
- SSE streaming documentation
- JavaScript usage examples
- Content-type documentation

#### 6.3 POST /api/v1/agents/{agent_id}/invoke-async (NEW)

**Purpose:** Queue agent invocation as background task

**Request:**
```json
{
  "message": "Analyze this large dataset...",
  "session_id": "session_123",
  "metadata": {"priority": "high"}
}
```

**Response (202 Accepted):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Agent invocation queued successfully",
  "status_url": "/api/v1/agents/tasks/550e8400-e29b-41d4-a716-446655440000"
}
```

**Features:**
- Returns immediately with task ID
- Queues task to Celery
- Provides status URL for polling
- Tracks user_id and session_id
- Supports metadata

#### 6.4 GET /api/v1/agents/tasks/{task_id} (NEW)

**Purpose:** Check task status and retrieve results

**Response (Processing):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "STARTED",
  "status": "processing",
  "progress": 45,
  "result": null,
  "error": null
}
```

**Response (Completed):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "SUCCESS",
  "status": "completed",
  "progress": 100,
  "result": {
    "content": "The agent's response...",
    "metadata": {"tokens_used": 150}
  },
  "error": null
}
```

**Task States:**
- `PENDING`: Queued, not started
- `STARTED`: Currently running
- `SUCCESS`: Completed successfully
- `FAILURE`: Failed with error
- `RETRY`: Being retried

## 7. Directory Structure

```
src/agent_service/
├── api/
│   ├── app.py                     # Enhanced with OpenAPI metadata
│   └── routes/
│       └── agents.py              # Enhanced with async endpoint
├── config/
│   └── settings.py                # Added Celery settings
└── workers/                       # NEW
    ├── __init__.py
    ├── celery_app.py              # Celery configuration
    ├── README.md                  # Comprehensive documentation
    └── tasks/
        ├── __init__.py
        ├── agent_tasks.py         # Agent invocation tasks
        └── cleanup_tasks.py       # Maintenance tasks
```

## 8. Running the System

### Prerequisites

```bash
# Install dependencies
pip install celery[redis] redis flower

# Start Redis
brew services start redis  # macOS
# OR
docker run -d -p 6379:6379 redis:alpine
```

### Start Services

```bash
# Terminal 1: Start FastAPI server
uvicorn agent_service.main:app --reload

# Terminal 2: Start Celery worker
celery -A agent_service.workers.celery_app worker --loglevel=info

# Terminal 3: Start Celery beat (periodic tasks)
celery -A agent_service.workers.celery_app beat --loglevel=info

# Terminal 4: Start Flower monitoring (optional)
celery -A agent_service.workers.celery_app flower
```

### Access Points

- **API Documentation**: http://localhost:8000/docs
- **Flower Monitoring**: http://localhost:5555
- **API Endpoint**: http://localhost:8000/api/v1

## 9. Usage Examples

### Async Agent Invocation (curl)

```bash
# Queue task
curl -X POST http://localhost:8000/api/v1/agents/simple_llm_agent/invoke-async \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the capital of France?",
    "session_id": "session_123"
  }'

# Response:
# {
#   "task_id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "queued",
#   "status_url": "/api/v1/agents/tasks/550e8400-e29b-41d4-a716-446655440000"
# }

# Check status
curl http://localhost:8000/api/v1/agents/tasks/550e8400-e29b-41d4-a716-446655440000
```

### Async Agent Invocation (Python)

```python
import httpx
import time

# Queue task
response = httpx.post(
    "http://localhost:8000/api/v1/agents/simple_llm_agent/invoke-async",
    json={"message": "What is the capital of France?"},
    headers={"X-API-Key": "your-api-key"}
)
data = response.json()
task_id = data["task_id"]

# Poll for result
while True:
    status_response = httpx.get(
        f"http://localhost:8000/api/v1/agents/tasks/{task_id}"
    )
    status_data = status_response.json()

    if status_data["status"] == "completed":
        print(f"Result: {status_data['result']}")
        break
    elif status_data["status"] == "failed":
        print(f"Error: {status_data['error']}")
        break

    print(f"Progress: {status_data.get('progress', 0)}%")
    time.sleep(2)
```

### Manual Task Execution (Python)

```python
from agent_service.workers.tasks.agent_tasks import invoke_agent_async
from agent_service.workers.tasks.cleanup_tasks import cleanup_expired_sessions

# Queue agent task
task = invoke_agent_async.delay(
    agent_id="simple_llm_agent",
    message="Hello!",
    user_id="user123"
)
print(f"Task ID: {task.id}")

# Wait for result (blocking)
result = task.get(timeout=60)
print(f"Result: {result}")

# Trigger cleanup manually
cleanup_task = cleanup_expired_sessions.delay()
cleanup_result = cleanup_task.get()
print(f"Cleaned up {cleanup_result['deleted_count']} sessions")
```

## 10. Monitoring & Debugging

### Flower UI

Access at http://localhost:5555:
- View active tasks
- Monitor worker status
- Inspect task results
- View task graphs
- Configure alerts

### Celery CLI

```bash
# Inspect active tasks
celery -A agent_service.workers.celery_app inspect active

# View registered tasks
celery -A agent_service.workers.celery_app inspect registered

# Check worker stats
celery -A agent_service.workers.celery_app inspect stats

# Purge all tasks (development only!)
celery -A agent_service.workers.celery_app purge
```

### Task Information API

```python
from agent_service.workers.celery_app import get_task_info, revoke_task

# Get task info
info = get_task_info("task-id")
print(info)

# Revoke task
revoke_task("task-id", terminate=False)
```

## 11. Testing

### Test Async Endpoint

```bash
# Start services first

# Test async invocation
curl -X POST http://localhost:8000/api/v1/agents/simple_llm_agent/invoke-async \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}' \
  | jq

# Check OpenAPI docs
open http://localhost:8000/docs
```

### Test Cleanup Tasks

```python
# Manually trigger cleanup tasks
from agent_service.workers.tasks import cleanup_tasks

# Session cleanup
result = cleanup_tasks.cleanup_expired_sessions.delay()
print(result.get())

# Temp file cleanup
result = cleanup_tasks.cleanup_temp_files.delay()
print(result.get())
```

## 12. Production Deployment

### systemd Services

1. **Celery Worker** (`/etc/systemd/system/celery-worker.service`)
2. **Celery Beat** (`/etc/systemd/system/celery-beat.service`)

See `/src/agent_service/workers/README.md` for complete systemd configuration.

### Docker Compose

```yaml
services:
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

  celery-worker:
    build: .
    command: celery -A agent_service.workers.celery_app worker --loglevel=info
    depends_on:
      - redis
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2

  celery-beat:
    build: .
    command: celery -A agent_service.workers.celery_app beat --loglevel=info
    depends_on:
      - redis
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/1

  flower:
    build: .
    command: celery -A agent_service.workers.celery_app flower
    ports:
      - "5555:5555"
    depends_on:
      - redis
```

## 13. Security Considerations

1. **Authentication**: All async endpoints require authentication (Bearer token or API key)
2. **Rate Limiting**: Configured per endpoint and task type
3. **Task Isolation**: Separate queues for different task types
4. **Result Expiration**: Task results expire after 1 hour
5. **Error Tracking**: Integration with Sentry for error monitoring

## 14. Performance Optimization

1. **Worker Concurrency**: Configure based on workload
2. **Task Prioritization**: Agent tasks have higher priority
3. **Result Backend**: Redis for fast result retrieval
4. **Cache Integration**: Results cached in Redis for quick access
5. **Connection Pooling**: Efficient database and Redis connections

## 15. Next Steps

### Recommended Enhancements

1. **WebSocket Support**: Real-time task progress updates
2. **Task Chaining**: Complex workflows with multiple tasks
3. **Result Pagination**: For tasks with large result sets
4. **Task Scheduling**: User-scheduled agent invocations
5. **Advanced Monitoring**: Prometheus metrics, Grafana dashboards
6. **Task Cancellation**: User-initiated task cancellation endpoint
7. **Batch Processing**: Bulk agent invocations
8. **Result Export**: Download task results as files

### Integration Points

1. **Frontend Integration**: WebSocket client for real-time updates
2. **Metrics Collection**: Prometheus exporter for Celery
3. **Alert System**: Alert on task failures or queue buildup
4. **Audit Logging**: Track all async invocations
5. **Cost Tracking**: Monitor resource usage per task

## 16. Documentation References

- **Workers Module**: `/src/agent_service/workers/README.md`
- **OpenAPI Docs**: http://localhost:8000/docs (when running)
- **Celery Docs**: https://docs.celeryproject.org/
- **Flower Docs**: https://flower.readthedocs.io/

## Summary

This implementation provides:

1. Production-ready OpenAPI documentation with comprehensive metadata
2. Robust background job processing with Celery
3. Async agent invocation for long-running operations
4. Automated maintenance tasks for system health
5. Comprehensive monitoring and debugging tools
6. Scalable architecture for high-throughput scenarios

All components are production-ready with proper error handling, retry logic, monitoring, and documentation.
