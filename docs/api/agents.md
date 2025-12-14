# Agent API Reference

Complete API reference for agent endpoints.

## Base URL

```
http://localhost:8000/api/v1/agents
```

## Endpoints

### List All Agents

Get a list of all registered agents.

```http
GET /api/v1/agents
```

**Response**:
```json
{
  "agents": [
    {
      "name": "weather-agent",
      "description": "Provides weather information for any location",
      "capabilities": ["invoke", "stream"]
    },
    {
      "name": "simple-llm",
      "description": "Simple OpenAI agent",
      "capabilities": ["invoke", "stream"]
    }
  ],
  "total": 2
}
```

**Example**:
```bash
curl http://localhost:8000/api/v1/agents
```

---

### Get Agent Details

Get detailed information about a specific agent.

```http
GET /api/v1/agents/{agent_name}
```

**Parameters**:
- `agent_name` (path, required): Unique agent identifier

**Response**:
```json
{
  "name": "weather-agent",
  "description": "Provides weather information for any location",
  "capabilities": ["invoke", "stream"],
  "metadata": {
    "version": "1.0.0",
    "author": "Your Team",
    "tools": ["get_weather", "http_request"]
  }
}
```

**Example**:
```bash
curl http://localhost:8000/api/v1/agents/weather-agent
```

**Error Responses**:
- `404 Not Found`: Agent not found
  ```json
  {
    "detail": "Agent 'unknown-agent' not found"
  }
  ```

---

### Invoke Agent

Execute an agent synchronously and get the complete response.

```http
POST /api/v1/agents/{agent_name}/invoke
```

**Parameters**:
- `agent_name` (path, required): Unique agent identifier

**Request Body**:
```json
{
  "message": "string",           // Required: User's message/prompt
  "session_id": "string",        // Optional: Session identifier for context
  "context": {                   // Optional: Additional context
    "user_id": "string",
    "metadata": {}
  }
}
```

**Response**:
```json
{
  "content": "string",           // Agent's response
  "tool_calls": [                // Optional: Tools that were executed
    {
      "name": "get_weather",
      "args": {"location": "London"},
      "result": {"temperature": "15°C"}
    }
  ],
  "metadata": {                  // Optional: Additional metadata
    "model": "gpt-4o-mini",
    "tokens": 234,
    "duration_ms": 1250
  }
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/agents/weather-agent/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the weather in London?",
    "session_id": "user-123"
  }'
```

**Python Example**:
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/agents/weather-agent/invoke",
    json={
        "message": "What is the weather in London?",
        "session_id": "user-123",
        "context": {"user_id": "john@example.com"}
    }
)

result = response.json()
print(result["content"])
```

**JavaScript Example**:
```javascript
const response = await fetch('http://localhost:8000/api/v1/agents/weather-agent/invoke', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: 'What is the weather in London?',
    session_id: 'user-123'
  })
});

const result = await response.json();
console.log(result.content);
```

**Error Responses**:
- `404 Not Found`: Agent not found
- `422 Unprocessable Entity`: Invalid request body
- `500 Internal Server Error`: Agent execution failed

---

### Stream Agent Response

Execute an agent and stream the response in real-time.

```http
POST /api/v1/agents/{agent_name}/stream
```

**Parameters**:
- `agent_name` (path, required): Unique agent identifier

**Request Body**:
```json
{
  "message": "string",
  "session_id": "string",
  "context": {}
}
```

**Response**: Server-Sent Events (SSE) stream

Each event is a JSON object with this structure:
```json
{
  "type": "text",              // text, tool_start, tool_end, error, done
  "content": "string",         // Event content
  "metadata": {}               // Optional metadata
}
```

**Event Types**:
- `text`: Streamed text chunk
- `tool_start`: Tool execution started
- `tool_end`: Tool execution completed
- `error`: Error occurred
- `done`: Stream complete

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/agents/weather-agent/stream \
  -H "Content-Type: application/json" \
  -N \
  -d '{
    "message": "Tell me about the weather in Paris",
    "session_id": "user-123"
  }'
```

**Python Example with SSE Client**:
```python
import requests
import json

response = requests.post(
    "http://localhost:8000/api/v1/agents/weather-agent/stream",
    json={
        "message": "Tell me about the weather in Paris",
        "session_id": "user-123"
    },
    stream=True
)

for line in response.iter_lines():
    if line:
        # Parse SSE format: "data: {json}"
        if line.startswith(b'data: '):
            data = json.loads(line[6:])
            print(data["content"], end="", flush=True)
```

**JavaScript Example with EventSource**:
```javascript
// Note: EventSource doesn't support POST, use fetch with ReadableStream
const response = await fetch('http://localhost:8000/api/v1/agents/weather-agent/stream', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: 'Tell me about the weather in Paris',
    session_id: 'user-123'
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      console.log(data.content);
    }
  }
}
```

---

## Request/Response Schemas

### AgentInput

```typescript
interface AgentInput {
  message: string;              // Required
  session_id?: string;          // Optional
  context?: {                   // Optional
    [key: string]: any;
  };
}
```

### AgentOutput

```typescript
interface AgentOutput {
  content: string;              // Agent's response
  tool_calls?: ToolCall[];      // Tools that were executed
  metadata?: {                  // Additional metadata
    [key: string]: any;
  };
}

interface ToolCall {
  name: string;
  args: { [key: string]: any };
  result: any;
}
```

### StreamChunk

```typescript
interface StreamChunk {
  type: 'text' | 'tool_start' | 'tool_end' | 'error' | 'done';
  content: string;
  metadata?: {
    [key: string]: any;
  };
}
```

---

## Session Management

Sessions allow maintaining conversation context across multiple requests.

### Creating a Session

```python
import uuid

# Generate unique session ID
session_id = str(uuid.uuid4())

# First message
response1 = requests.post(
    f"http://localhost:8000/api/v1/agents/weather-agent/invoke",
    json={
        "message": "What's the weather in London?",
        "session_id": session_id
    }
)

# Follow-up message (agent remembers context)
response2 = requests.post(
    f"http://localhost:8000/api/v1/agents/weather-agent/invoke",
    json={
        "message": "How about tomorrow?",  # Agent knows we're still talking about London
        "session_id": session_id
    }
)
```

### Session Context

Pass additional context that persists across the session:

```python
response = requests.post(
    f"http://localhost:8000/api/v1/agents/weather-agent/invoke",
    json={
        "message": "What's the weather?",
        "session_id": session_id,
        "context": {
            "user_id": "john@example.com",
            "preferences": {
                "temperature_unit": "celsius",
                "location": "London"
            },
            "metadata": {
                "source": "mobile_app",
                "version": "2.1.0"
            }
        }
    }
)
```

---

## Error Handling

### Standard Error Response

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-12-14T10:30:00.000Z",
  "request_id": "req_abc123"
}
```

### Common Error Codes

| Code | HTTP Status | Description | Solution |
|------|-------------|-------------|----------|
| `AGENT_NOT_FOUND` | 404 | Agent doesn't exist | Check agent name |
| `INVALID_INPUT` | 422 | Invalid request body | Validate request schema |
| `AGENT_ERROR` | 500 | Agent execution failed | Check agent logs |
| `TOOL_ERROR` | 500 | Tool execution failed | Check tool configuration |
| `TIMEOUT` | 504 | Request timeout | Reduce complexity or increase timeout |
| `RATE_LIMITED` | 429 | Too many requests | Wait and retry |

### Error Handling Example

```python
try:
    response = requests.post(
        f"http://localhost:8000/api/v1/agents/weather-agent/invoke",
        json={"message": "Hello", "session_id": "test"}
    )
    response.raise_for_status()
    result = response.json()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 404:
        print("Agent not found")
    elif e.response.status_code == 500:
        error = e.response.json()
        print(f"Agent error: {error['detail']}")
        print(f"Request ID: {error['request_id']}")
    else:
        print(f"HTTP error: {e}")
except requests.exceptions.RequestException as e:
    print(f"Network error: {e}")
```

---

## Rate Limiting

Default rate limits (configurable via environment variables):

- **Authenticated requests**: 100 requests/minute
- **Unauthenticated requests**: 20 requests/minute
- **Streaming requests**: 10 concurrent streams

### Rate Limit Headers

Responses include rate limit information:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1702560000
```

### Handling Rate Limits

```python
import time

response = requests.post(url, json=data)

if response.status_code == 429:
    # Get reset time from header
    reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
    wait_seconds = reset_time - int(time.time())

    print(f"Rate limited. Waiting {wait_seconds} seconds...")
    time.sleep(wait_seconds)

    # Retry request
    response = requests.post(url, json=data)
```

---

## Authentication

All agent endpoints support authentication. See [Authentication Guide](./authentication.md) for details.

### Using Bearer Tokens

```bash
# Azure AD or Cognito token
curl -X POST http://localhost:8000/api/v1/agents/weather-agent/invoke \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "session_id": "test"}'
```

### Using API Keys

```bash
# API key authentication
curl -X POST http://localhost:8000/api/v1/agents/weather-agent/invoke \
  -H "X-API-Key: sk_live_abc123..." \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "session_id": "test"}'
```

---

## Advanced Features

### Agent Metadata

Get extended agent information including capabilities and configuration:

```python
response = requests.get(
    "http://localhost:8000/api/v1/agents/weather-agent/metadata"
)

metadata = response.json()
print(f"Tools available: {metadata['tools']}")
print(f"Supports streaming: {metadata['supports_streaming']}")
print(f"Max context length: {metadata['max_context_length']}")
```

### Agent Health Check

Check if an agent is operational:

```bash
curl http://localhost:8000/api/v1/agents/weather-agent/health
```

Response:
```json
{
  "status": "healthy",
  "latency_ms": 45,
  "last_invocation": "2024-12-14T10:30:00.000Z"
}
```

### Batch Requests

Execute multiple agent requests in parallel:

```python
import asyncio
import aiohttp

async def invoke_agent(session, message):
    async with session.post(
        "http://localhost:8000/api/v1/agents/weather-agent/invoke",
        json={"message": message, "session_id": "batch"}
    ) as response:
        return await response.json()

async def batch_invoke():
    async with aiohttp.ClientSession() as session:
        tasks = [
            invoke_agent(session, "Weather in London?"),
            invoke_agent(session, "Weather in Paris?"),
            invoke_agent(session, "Weather in Tokyo?")
        ]
        results = await asyncio.gather(*tasks)
        return results

results = asyncio.run(batch_invoke())
for result in results:
    print(result["content"])
```

---

## Observability

### Request Tracing

All requests include trace headers for debugging:

```
X-Request-ID: req_abc123def456
X-Trace-ID: trace_xyz789
```

Use these IDs to search logs:

```bash
# Search logs for specific request
docker-compose logs api | grep "req_abc123def456"

# In Grafana/Loki
{app="agent-service"} |= "req_abc123def456"
```

### Metrics

Agent invocation metrics are exposed at `/metrics`:

```bash
curl http://localhost:8000/metrics | grep agent_invocations
```

Key metrics:
- `agent_invocations_total{agent="weather-agent"}`: Total invocations
- `agent_invocations_duration_seconds`: Response time histogram
- `agent_errors_total{agent="weather-agent"}`: Total errors
- `agent_active_sessions`: Active sessions count

---

## Best Practices

### 1. Use Session IDs

Always provide session IDs for conversational agents:

```python
session_id = f"user_{user_id}_{timestamp}"
```

### 2. Handle Streaming Properly

Always close streaming connections:

```python
try:
    response = requests.post(url, json=data, stream=True)
    for line in response.iter_lines():
        # Process line
        pass
finally:
    response.close()
```

### 3. Implement Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def invoke_agent(message):
    response = requests.post(url, json={"message": message})
    response.raise_for_status()
    return response.json()
```

### 4. Use Timeouts

```python
# Set reasonable timeouts
response = requests.post(
    url,
    json=data,
    timeout=(5, 30)  # (connect timeout, read timeout)
)
```

### 5. Monitor Performance

```python
import time

start = time.time()
response = requests.post(url, json=data)
duration = time.time() - start

if duration > 5.0:
    print(f"Warning: Slow response ({duration:.2f}s)")
```

---

## Examples

Complete examples are available in `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/examples/`:

- `invoke_agent.py` - Basic invocation
- `stream_agent.py` - Streaming responses
- `session_management.py` - Session handling
- `error_handling.py` - Error handling patterns
- `batch_requests.py` - Parallel requests

## Next Steps

- [Tool System](./tools.md) - Add tools to your agents
- [Protocols](./protocols.md) - MCP, A2A, AG-UI integration
- [Authentication](./authentication.md) - Secure your agents
