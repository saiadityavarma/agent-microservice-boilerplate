# A2A and AG-UI Protocol Implementation Summary

## Overview

This document summarizes the complete implementation of A2A (Agent-to-Agent) and AG-UI (Agent-User Interaction) protocols in the agent service.

## A2A Protocol Implementation

### Location: `/src/agent_service/protocols/a2a/`

### Components Implemented

#### 1. **handler.py** - A2A Protocol Handler
Complete implementation with:
- **Task lifecycle management**: created → working → input-required → completed/failed/cancelled
- **Message handling**: Support for text, file, and data parts
- **Streaming responses**: Real-time task updates via Server-Sent Events
- **Request handling**: Create tasks, get tasks, add messages

**Key Features:**
- Non-blocking task execution
- Automatic status transitions
- Error handling with failed status
- SSE event streaming for real-time updates

#### 2. **task_manager.py** - Task Lifecycle Manager
Comprehensive task management with:
- `create_task(agent_id, message, context)` - Create new tasks with CREATED status
- `get_task(task_id)` - Retrieve task by ID
- `update_task_status(task_id, status, error)` - Update task status
- `add_message_to_task(task_id, message)` - Append messages to task history
- `list_tasks(agent_id, status, limit, offset)` - List and filter tasks
- `delete_task(task_id)` - Remove tasks

**Storage:**
- Primary: Redis with 24-hour expiration
- Fallback: In-memory storage
- Automatic cleanup for expired tasks

#### 3. **messages.py** - Message and Task Models
Complete Pydantic models:
- **Message Parts:**
  - `TextPart` - Text content
  - `FilePart` - File references with URL, MIME type, size
  - `DataPart` - Structured JSON data with optional schema

- **Messages:**
  - `A2AMessage` - Multi-part messages with role, parts, timestamp

- **Task Models:**
  - `TaskStatus` enum - created, working, input_required, completed, failed, cancelled
  - `TaskCreateRequest` - Request to create tasks
  - `TaskResponse` - Complete task information
  - `TaskUpdateRequest` - Update task or add messages
  - `TaskListResponse` - Paginated task lists
  - `StreamEvent` - SSE events for streaming

#### 4. **discovery.py** - Agent Card Generation
A2A agent discovery with:
- `generate_agent_card()` - Generate complete agent capabilities
- `get_well_known_config()` - Standard `.well-known/agent.json` endpoint
- `get_skills_manifest()` - Detailed tool/skill information

**Agent Card Includes:**
- Agent name, description, version
- Capabilities (streaming, task management, structured data)
- Skills (automatically from tool registry)
- Authentication requirements
- Metadata (protocols, frameworks, environment)

### API Endpoints Added

#### A2A Task Endpoints (in `/src/agent_service/api/routes/protocols.py`)

1. **`GET /.well-known/agent.json`**
   - Agent card discovery endpoint
   - Returns complete agent capabilities and skills

2. **`POST /a2a/tasks`**
   - Create new task
   - Body: `{agent_id, message, context, stream}`
   - Returns: TaskResponse

3. **`GET /a2a/tasks/{task_id}`**
   - Get task by ID
   - Returns: TaskResponse

4. **`POST /a2a/tasks/{task_id}/messages`**
   - Add message to task
   - Body: A2AMessage
   - Returns: Updated TaskResponse

5. **`GET /a2a/tasks`**
   - List tasks with filtering
   - Query params: `agent_id`, `status`, `limit`, `offset`
   - Returns: TaskListResponse

6. **`POST /a2a/stream`**
   - Stream task execution
   - SSE events for task lifecycle
   - Body: TaskCreateRequest

## AG-UI Protocol Implementation

### Location: `/src/agent_service/protocols/agui/`

### Components Implemented

#### 1. **events.py** - Event Types and Models
Complete event system with:

**Event Types:**
- `RUN_STARTED`, `RUN_FINISHED`, `RUN_FAILED` - Run lifecycle
- `TEXT_MESSAGE_START`, `TEXT_MESSAGE_CONTENT`, `TEXT_MESSAGE_END` - Message streaming
- `TOOL_CALL_START`, `TOOL_CALL_PROGRESS`, `TOOL_CALL_END`, `TOOL_CALL_ERROR` - Tool execution
- `STATE_SYNC`, `STATE_UPDATE` - State synchronization
- `ERROR` - Generic errors

**Event Models (Pydantic):**
- `RunStartedEvent` - Agent run begins with run_id, agent_name, input
- `RunFinishedEvent` - Run completes with final message and metadata
- `RunFailedEvent` - Run fails with error details
- `TextMessageStartEvent` - Message starts with message_id and role
- `TextMessageContentEvent` - Streaming content chunks
- `TextMessageEndEvent` - Message completes with full content
- `ToolCallStartEvent` - Tool invocation with name and arguments
- `ToolCallProgressEvent` - Tool execution progress
- `ToolCallEndEvent` - Tool completion with result
- `ToolCallErrorEvent` - Tool error with details
- `StateSyncEvent` - Full state synchronization with version
- `StateUpdateEvent` - Incremental state updates
- `ErrorEvent` - Generic error events

**Utilities:**
- `create_event(event_type, **kwargs)` - Factory for event creation

#### 2. **state.py** - State Management
Sophisticated state synchronization:

**StateManager:**
- `get_state()` - Get current state
- `set_state(state)` - Full state replacement
- `update_state(updates, path)` - Incremental updates
- `get_value(path)` - Get nested values by JSON path
- `set_value(path, value)` - Set nested values
- `delete_value(path)` - Remove values
- `merge_state(updates)` - Deep merge updates
- `reset_state()` - Clear all state
- `get_history(limit)` - State change history

**RunState:**
- Per-run state management
- Run metadata tracking (started_at, finished_at, status)
- Scoped state manager per run

**Features:**
- JSON path support for nested updates (e.g., "user.settings.theme")
- State versioning for synchronization
- State history with configurable limit
- Deep merge for complex updates

#### 3. **handler.py** - AG-UI Protocol Handler
Complete streaming implementation:

**Event Emission Sequence:**
1. `RUN_STARTED` - Run begins
2. `STATE_SYNC` - Initial state (optional)
3. `TEXT_MESSAGE_START` - Message starts
4. `TEXT_MESSAGE_CONTENT` - Content chunks (streaming)
5. `TOOL_CALL_START` - Tool execution begins
6. `TOOL_CALL_END` - Tool completes
7. `STATE_UPDATE` - State changes during execution
8. `TEXT_MESSAGE_END` - Message completes
9. `STATE_SYNC` - Final state (optional)
10. `RUN_FINISHED` - Run completes

**Features:**
- Real-time event streaming via SSE
- Automatic state updates during tool calls
- Error handling with appropriate events
- Run tracking and cleanup
- State synchronization control

**Non-streaming Endpoints:**
- State queries (`/agui/state`)
- Capabilities info (`/agui/capabilities`)

### API Endpoints Added

#### AG-UI Endpoints (in `/src/agent_service/api/routes/protocols.py`)

1. **`POST /agui/stream`**
   - Stream agent execution with events
   - Body: `{message, context, include_state}`
   - Returns: SSE stream

2. **`GET /agui/state`**
   - Get current global state
   - Returns: `{state, version}`

3. **`GET /agui/capabilities`**
   - Get AG-UI capabilities
   - Returns: Event types, endpoints, capabilities

## Integration with Existing System

### Protocol Registry
Both protocols are auto-registered in `/src/agent_service/protocols/registry.py`:
- A2A handler registered when `enable_a2a=True`
- AG-UI handler registered when `enable_agui=True`

### Settings (config/settings.py)
Feature flags already present:
```python
enable_mcp: bool = True
enable_a2a: bool = True
enable_agui: bool = True
```

### Agent Integration
Both protocols work with any agent implementing `IAgent`:
- Uses `agent.invoke()` for synchronous execution
- Uses `agent.stream()` for streaming responses
- Supports `StreamChunk` types: text, tool_start, tool_end, error

### Tool Integration
Both protocols integrate with the tool registry:
- A2A: Exposes tools as "skills" in agent card
- AG-UI: Emits tool call events during execution

## Usage Examples

### A2A - Create and Execute Task

```bash
# Create task (non-streaming)
curl -X POST http://localhost:8000/a2a/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "default",
    "message": {
      "role": "user",
      "parts": [
        {"type": "text", "text": "What is the weather?"}
      ]
    },
    "context": {"location": "San Francisco"},
    "stream": false
  }'

# Get task status
curl http://localhost:8000/a2a/tasks/{task_id}

# List tasks
curl "http://localhost:8000/a2a/tasks?status=completed&limit=10"

# Stream task execution
curl -X POST http://localhost:8000/a2a/stream \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "default",
    "message": {
      "role": "user",
      "parts": [{"type": "text", "text": "Analyze this data"}]
    }
  }'
```

### AG-UI - Stream Agent Execution

```bash
# Stream with events
curl -X POST http://localhost:8000/agui/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Help me with this task",
    "context": {"user_id": "123"},
    "include_state": true
  }'

# Get current state
curl http://localhost:8000/agui/state

# Get capabilities
curl http://localhost:8000/agui/capabilities
```

### Event Stream Example (AG-UI)

```json
data: {"event": "run_started", "run_id": "uuid-123", "agent_name": "default", "input_message": "Hello"}

data: {"event": "state_sync", "run_id": "uuid-123", "state": {}, "version": 1}

data: {"event": "text_message_start", "run_id": "uuid-123", "message_id": "msg-456", "role": "assistant"}

data: {"event": "text_message_content", "run_id": "uuid-123", "message_id": "msg-456", "content": "Hello! ", "delta": true}

data: {"event": "tool_call_start", "run_id": "uuid-123", "tool_call_id": "tool-789", "tool_name": "search", "arguments": {"query": "weather"}}

data: {"event": "tool_call_end", "run_id": "uuid-123", "tool_call_id": "tool-789", "result": {"temperature": 72}, "success": true}

data: {"event": "text_message_end", "run_id": "uuid-123", "message_id": "msg-456", "full_content": "Hello! The weather is 72 degrees."}

data: {"event": "run_finished", "run_id": "uuid-123", "final_message": "Hello! The weather is 72 degrees."}
```

## Testing

### Manual Testing

1. **A2A Task Creation:**
   ```bash
   pytest tests/test_a2a_handler.py::test_create_task
   ```

2. **A2A Streaming:**
   ```bash
   pytest tests/test_a2a_handler.py::test_stream_task
   ```

3. **AG-UI Streaming:**
   ```bash
   pytest tests/test_agui_handler.py::test_stream_with_events
   ```

4. **State Management:**
   ```bash
   pytest tests/test_agui_state.py::test_state_sync
   ```

### Integration Testing

Both protocols integrate with existing agents. To test:

1. Register a test agent:
   ```python
   from agent_service.agent.registry import agent_registry
   agent_registry.register(your_agent, default=True)
   ```

2. Make requests to the protocol endpoints

3. Verify task lifecycle (A2A) or event emission (AG-UI)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Application                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │           Protocol Registry                      │  │
│  │  - Auto-registers handlers from settings        │  │
│  └──────────────────────────────────────────────────┘  │
│         │              │              │                 │
│    ┌────▼────┐    ┌───▼────┐    ┌───▼────┐           │
│    │   MCP   │    │  A2A   │    │  AGUI  │           │
│    └────┬────┘    └───┬────┘    └───┬────┘           │
│         │             │              │                 │
│         │    ┌────────▼──────────────▼───┐            │
│         │    │    Task Manager (A2A)     │            │
│         │    │  - Redis/Memory storage   │            │
│         │    │  - Task lifecycle         │            │
│         │    └───────────────────────────┘            │
│         │             │                                │
│         │    ┌────────▼──────────────────┐            │
│         │    │   State Manager (AGUI)    │            │
│         │    │  - Per-run state          │            │
│         │    │  - State versioning       │            │
│         │    └───────────────────────────┘            │
│         │                                              │
│    ┌────▼─────────────┐                               │
│    │  Agent Registry  │                               │
│    │  - IAgent impls  │                               │
│    └────┬─────────────┘                               │
│         │                                              │
│    ┌────▼─────────────┐                               │
│    │  Tool Registry   │                               │
│    │  - echo          │                               │
│    │  - http_request  │                               │
│    │  - custom tools  │                               │
│    └──────────────────┘                               │
└─────────────────────────────────────────────────────────┘
```

## Key Design Decisions

1. **Task Storage**: Redis with in-memory fallback for A2A tasks
   - Enables distributed deployments
   - Automatic expiration (24 hours)
   - Graceful degradation

2. **Event Streaming**: Server-Sent Events (SSE) for both protocols
   - Standard HTTP/1.1 compatible
   - Easy to consume from browsers and clients
   - Built-in browser reconnection

3. **State Management**: Per-run state isolation in AG-UI
   - Prevents state conflicts between concurrent runs
   - Automatic cleanup
   - State versioning for sync

4. **Message Parts**: Flexible content types in A2A
   - Text, file references, structured data
   - Extensible for future types
   - JSON schema validation

5. **Protocol Independence**: Each protocol is self-contained
   - Can be enabled/disabled independently
   - Minimal shared code
   - Clear separation of concerns

## Files Modified/Created

### Created Files:
1. `/src/agent_service/protocols/agui/events.py` - Event types and models
2. `/src/agent_service/protocols/agui/state.py` - State management
3. `/src/agent_service/protocols/IMPLEMENTATION_SUMMARY.md` - This file

### Modified Files:
1. `/src/agent_service/protocols/agui/handler.py` - Complete AG-UI implementation
2. `/src/agent_service/protocols/agui/__init__.py` - Export all AG-UI components
3. `/src/agent_service/protocols/a2a/__init__.py` - Export all A2A components
4. `/src/agent_service/api/routes/protocols.py` - Added A2A and AG-UI endpoints

### Existing Files (already complete):
1. `/src/agent_service/protocols/a2a/handler.py` - A2A handler
2. `/src/agent_service/protocols/a2a/task_manager.py` - Task management
3. `/src/agent_service/protocols/a2a/messages.py` - Message models
4. `/src/agent_service/protocols/a2a/discovery.py` - Agent discovery
5. `/src/agent_service/protocols/registry.py` - Protocol registry

## Next Steps

1. **Testing**: Add comprehensive unit and integration tests
2. **Documentation**: Add OpenAPI/Swagger documentation for endpoints
3. **Monitoring**: Add metrics for task lifecycle and event emission
4. **Persistence**: Consider persistent storage option for tasks beyond Redis
5. **File Handling**: Implement file upload/download for FilePart in A2A
6. **WebSockets**: Consider WebSocket transport as alternative to SSE
7. **Authentication**: Add protocol-specific authentication if needed
8. **Rate Limiting**: Add per-protocol rate limits

## Conclusion

Both A2A and AG-UI protocols are now fully implemented and integrated with the existing agent service architecture. They work seamlessly with registered agents and tools, providing standardized interfaces for agent-to-agent communication and real-time UI integration.
