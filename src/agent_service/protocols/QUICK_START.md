# Protocol Quick Start Guide

## A2A (Agent-to-Agent) Protocol

### Create a Task (Non-Streaming)

```bash
curl -X POST http://localhost:8000/a2a/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "agent_id": "default",
    "message": {
      "role": "user",
      "parts": [
        {
          "type": "text",
          "text": "What is the capital of France?"
        }
      ]
    },
    "context": {},
    "stream": false
  }'
```

**Response:**
```json
{
  "task_id": "uuid-123",
  "agent_id": "default",
  "status": "completed",
  "messages": [
    {
      "role": "user",
      "parts": [{"type": "text", "text": "What is the capital of France?"}]
    },
    {
      "role": "assistant",
      "parts": [{"type": "text", "text": "The capital of France is Paris."}]
    }
  ],
  "created_at": "2025-12-14T10:00:00Z",
  "updated_at": "2025-12-14T10:00:05Z",
  "completed_at": "2025-12-14T10:00:05Z"
}
```

### Stream Task Execution

```bash
curl -X POST http://localhost:8000/a2a/stream \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "agent_id": "default",
    "message": {
      "role": "user",
      "parts": [
        {
          "type": "text",
          "text": "Tell me a story"
        }
      ]
    }
  }'
```

**SSE Events:**
```
data: {"task_id": "uuid-123", "event_type": "status", "data": {"status": "created"}}

data: {"task_id": "uuid-123", "event_type": "status", "data": {"status": "working"}}

data: {"task_id": "uuid-123", "event_type": "message", "data": {"part": {"type": "text", "text": "Once upon"}, "partial": true}}

data: {"task_id": "uuid-123", "event_type": "message", "data": {"part": {"type": "text", "text": " a time..."}, "partial": true}}

data: {"task_id": "uuid-123", "event_type": "complete", "data": {"status": "completed", "task": {...}}}
```

### Get Task Status

```bash
curl http://localhost:8000/a2a/tasks/uuid-123 \
  -H "X-API-Key: your-api-key"
```

### List Tasks

```bash
# All tasks
curl http://localhost:8000/a2a/tasks \
  -H "X-API-Key: your-api-key"

# Filter by status
curl "http://localhost:8000/a2a/tasks?status=completed&limit=10" \
  -H "X-API-Key: your-api-key"

# Filter by agent
curl "http://localhost:8000/a2a/tasks?agent_id=default" \
  -H "X-API-Key: your-api-key"
```

### Add Message to Task

```bash
curl -X POST http://localhost:8000/a2a/tasks/uuid-123/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "role": "user",
    "parts": [
      {
        "type": "text",
        "text": "Tell me more"
      }
    ]
  }'
```

### Agent Discovery

```bash
# Get agent card
curl http://localhost:8000/.well-known/agent.json
```

**Response:**
```json
{
  "name": "Agent Service",
  "description": "Multi-protocol agent service supporting A2A, MCP, and AG-UI protocols",
  "version": "0.1.0",
  "url": "/a2a",
  "capabilities": {
    "streaming": true,
    "taskManagement": true,
    "structuredData": true
  },
  "skills": [
    {
      "name": "echo",
      "description": "Echoes the input message",
      "parameters": {...}
    }
  ]
}
```

## AG-UI (Agent-User Interaction) Protocol

### Stream Agent Execution

```bash
curl -X POST http://localhost:8000/agui/stream \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "message": "Help me write a Python function",
    "context": {
      "user_id": "user-123",
      "session_id": "session-456"
    },
    "include_state": true
  }'
```

**SSE Events:**
```
data: {"event": "run_started", "run_id": "run-789", "agent_name": "default", "input_message": "Help me write a Python function"}

data: {"event": "state_sync", "run_id": "run-789", "state": {}, "version": 1}

data: {"event": "text_message_start", "run_id": "run-789", "message_id": "msg-111", "role": "assistant"}

data: {"event": "text_message_content", "run_id": "run-789", "message_id": "msg-111", "content": "I'll help you", "delta": true}

data: {"event": "text_message_content", "run_id": "run-789", "message_id": "msg-111", "content": " write that function.", "delta": true}

data: {"event": "tool_call_start", "run_id": "run-789", "tool_call_id": "tool-222", "tool_name": "code_generator", "arguments": {"language": "python"}}

data: {"event": "tool_call_end", "run_id": "run-789", "tool_call_id": "tool-222", "result": {"code": "def example():\n    pass"}, "success": true}

data: {"event": "text_message_end", "run_id": "run-789", "message_id": "msg-111", "full_content": "I'll help you write that function."}

data: {"event": "state_sync", "run_id": "run-789", "state": {"current_tool": null}, "version": 2}

data: {"event": "run_finished", "run_id": "run-789", "final_message": "I'll help you write that function."}
```

### Get Current State

```bash
curl http://localhost:8000/agui/state \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "state": {
    "current_tool": null,
    "tool_status": "completed",
    "last_tool_result": {...}
  },
  "version": 5
}
```

### Get Capabilities

```bash
curl http://localhost:8000/agui/capabilities \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "protocol": "ag-ui",
  "version": "1.0",
  "capabilities": {
    "streaming": true,
    "stateManagement": true,
    "toolCalls": true,
    "eventTypes": [
      "run_started",
      "run_finished",
      "text_message_start",
      "text_message_content",
      "tool_call_start",
      "tool_call_end",
      "state_sync"
    ]
  },
  "endpoints": {
    "stream": "/agui/stream",
    "state": "/agui/state",
    "capabilities": "/agui/capabilities"
  },
  "events": {
    "run": ["run_started", "run_finished", "run_failed"],
    "message": ["text_message_start", "text_message_content", "text_message_end"],
    "tool": ["tool_call_start", "tool_call_progress", "tool_call_end", "tool_call_error"],
    "state": ["state_sync", "state_update"]
  }
}
```

## Python Client Examples

### A2A Client Example

```python
import requests
import json

# Create task
response = requests.post(
    "http://localhost:8000/a2a/tasks",
    headers={"X-API-Key": "your-api-key"},
    json={
        "agent_id": "default",
        "message": {
            "role": "user",
            "parts": [
                {"type": "text", "text": "Hello, agent!"}
            ]
        },
        "stream": False
    }
)

task = response.json()
print(f"Task ID: {task['task_id']}")
print(f"Status: {task['status']}")

# Stream task execution
response = requests.post(
    "http://localhost:8000/a2a/stream",
    headers={"X-API-Key": "your-api-key"},
    json={
        "agent_id": "default",
        "message": {
            "role": "user",
            "parts": [{"type": "text", "text": "Stream me a story"}]
        }
    },
    stream=True
)

for line in response.iter_lines():
    if line:
        event = json.loads(line.decode('utf-8').replace('data: ', ''))
        print(f"Event: {event['event_type']}")
```

### AG-UI Client Example

```python
import requests
import json

# Stream agent execution
response = requests.post(
    "http://localhost:8000/agui/stream",
    headers={"X-API-Key": "your-api-key"},
    json={
        "message": "Help me with this task",
        "context": {"user_id": "123"},
        "include_state": True
    },
    stream=True
)

for line in response.iter_lines():
    if line:
        event = json.loads(line.decode('utf-8').replace('data: ', ''))
        event_type = event.get('event')

        if event_type == 'run_started':
            print(f"Run started: {event['run_id']}")

        elif event_type == 'text_message_content':
            print(event['content'], end='', flush=True)

        elif event_type == 'tool_call_start':
            print(f"\n[Tool: {event['tool_name']}]")

        elif event_type == 'tool_call_end':
            print(f"[Result: {event['result']}]")

        elif event_type == 'run_finished':
            print(f"\nRun finished")

# Get state
response = requests.get(
    "http://localhost:8000/agui/state",
    headers={"X-API-Key": "your-api-key"}
)
state = response.json()
print(f"Current state version: {state['version']}")
```

## JavaScript/TypeScript Client Examples

### A2A Client (JavaScript)

```javascript
// Create task
const response = await fetch('http://localhost:8000/a2a/tasks', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify({
    agent_id: 'default',
    message: {
      role: 'user',
      parts: [
        { type: 'text', text: 'Hello, agent!' }
      ]
    },
    stream: false
  })
});

const task = await response.json();
console.log(`Task ID: ${task.task_id}`);
console.log(`Status: ${task.status}`);

// Stream task execution
const eventSource = new EventSource('http://localhost:8000/a2a/stream');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Event: ${data.event_type}`, data);
};
```

### AG-UI Client (React)

```typescript
import { useEffect, useState } from 'react';

function AgentChat() {
  const [messages, setMessages] = useState<string[]>([]);
  const [isRunning, setIsRunning] = useState(false);

  const runAgent = async (message: string) => {
    setIsRunning(true);

    const response = await fetch('http://localhost:8000/agui/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'your-api-key'
      },
      body: JSON.stringify({
        message,
        context: { user_id: '123' },
        include_state: true
      })
    });

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    while (reader) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const event = JSON.parse(line.slice(6));

          if (event.event === 'text_message_content') {
            setMessages(prev => [...prev, event.content]);
          } else if (event.event === 'run_finished') {
            setIsRunning(false);
          }
        }
      }
    }
  };

  return (
    <div>
      <div>{messages.join('')}</div>
      <button
        onClick={() => runAgent('Hello!')}
        disabled={isRunning}
      >
        Send Message
      </button>
    </div>
  );
}
```

## Configuration

Enable/disable protocols in `.env`:

```env
# Protocol Feature Flags
ENABLE_MCP=true
ENABLE_A2A=true
ENABLE_AGUI=true

# Redis for A2A task storage (optional)
REDIS_URL=redis://localhost:6379/0

# Authentication
SECRET_KEY=your-secret-key
```

## Troubleshooting

### A2A Tasks Not Persisting
- Check Redis connection: `REDIS_URL` in settings
- Tasks are stored in memory if Redis unavailable
- Tasks expire after 24 hours

### AG-UI Events Not Streaming
- Verify agent implements `IAgent.stream()` method
- Check that agent emits `StreamChunk` objects
- Ensure Content-Type is `text/event-stream`

### Agent Not Found
- Register agent: `agent_registry.register(agent, default=True)`
- Check agent name matches request

### Protocol Not Enabled
- Verify feature flags: `enable_a2a`, `enable_agui`
- Check protocol registry: `/mcp/info`, `/agui/capabilities`

## Next Steps

1. Implement your agent by extending `IAgent`
2. Register custom tools with `tool_registry`
3. Configure authentication and rate limiting
4. Add monitoring and logging
5. Deploy with Redis for production
