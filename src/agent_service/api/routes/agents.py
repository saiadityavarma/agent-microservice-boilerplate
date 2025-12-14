# src/agent_service/api/routes/agents.py
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent_service.api.dependencies import CurrentAgent, AppSettings
from agent_service.interfaces import AgentInput
from agent_service.auth.dependencies import get_current_user_any
from agent_service.auth.schemas import UserInfo

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================


class AgentInvokeRequest(BaseModel):
    """Request model for agent invocation."""

    message: str = Field(
        ...,
        description="The message to send to the agent",
        min_length=1,
        max_length=10000,
        examples=["What is the weather today?", "Help me write a Python function"]
    )
    session_id: Optional[str] = Field(
        None,
        description="Optional session ID for conversation context",
        examples=["session_abc123"]
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional metadata for the request",
        examples=[{"source": "web_app", "user_tier": "premium"}]
    )


class AgentInvokeResponse(BaseModel):
    """Response model for synchronous agent invocation."""

    response: str = Field(
        ...,
        description="The agent's response content"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata from the agent"
    )


class AsyncInvokeResponse(BaseModel):
    """Response model for async agent invocation."""

    task_id: str = Field(
        ...,
        description="Celery task ID to track the invocation",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    status: str = Field(
        default="queued",
        description="Initial task status",
        examples=["queued", "processing"]
    )
    message: str = Field(
        default="Agent invocation queued successfully",
        description="Status message"
    )
    status_url: str = Field(
        ...,
        description="URL to check task status",
        examples=["/api/v1/agents/tasks/550e8400-e29b-41d4-a716-446655440000"]
    )


class TaskStatusResponse(BaseModel):
    """Response model for task status check."""

    task_id: str = Field(..., description="Task ID")
    state: str = Field(
        ...,
        description="Task state",
        examples=["PENDING", "STARTED", "SUCCESS", "FAILURE", "RETRY"]
    )
    status: str = Field(
        ...,
        description="Human-readable status",
        examples=["queued", "processing", "completed", "failed"]
    )
    progress: Optional[int] = Field(
        None,
        description="Task progress percentage (0-100)",
        ge=0,
        le=100
    )
    result: Optional[Dict[str, Any]] = Field(
        None,
        description="Task result if completed"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if failed"
    )


# ============================================================================
# Agent Invocation Routes
# ============================================================================


@router.post(
    "/invoke",
    response_model=AgentInvokeResponse,
    summary="Invoke agent synchronously",
    description="""
    Invoke an agent synchronously and wait for the response.

    This endpoint blocks until the agent completes processing and returns the result.
    For long-running operations, consider using `/agents/{agent_id}/invoke-async` instead.

    **Authentication Required:** Bearer token or API key

    **Rate Limiting:** 100 requests/minute (free tier), 1000 requests/minute (pro tier)

    **Example Request:**
    ```json
    {
        "message": "What is the capital of France?",
        "session_id": "session_123",
        "metadata": {"source": "web_app"}
    }
    ```

    **Example Response:**
    ```json
    {
        "response": "The capital of France is Paris.",
        "metadata": {
            "model": "gpt-4",
            "tokens_used": 45
        }
    }
    ```
    """,
    responses={
        200: {
            "description": "Agent response returned successfully",
        },
        400: {
            "description": "Invalid request parameters"
        },
        401: {
            "description": "Not authenticated"
        },
        404: {
            "description": "Agent not found"
        },
        429: {
            "description": "Rate limit exceeded"
        },
        504: {
            "description": "Agent invocation timeout"
        }
    },
    tags=["Agents"]
)
async def invoke_agent(
    request: AgentInvokeRequest,
    agent: CurrentAgent,
    settings: AppSettings,
):
    """
    Invoke agent synchronously.

    Returns the agent's response immediately after processing.
    """
    result = await agent.invoke(AgentInput(message=request.message))
    return AgentInvokeResponse(
        response=result.content,
        metadata=result.metadata
    )


@router.post(
    "/stream",
    summary="Invoke agent with streaming response",
    description="""
    Invoke an agent with Server-Sent Events (SSE) streaming.

    The agent will stream responses as they are generated, providing a better
    user experience for long-running operations.

    **Authentication Required:** Bearer token or API key

    **Rate Limiting:** 50 requests/minute

    **Response Format:** Server-Sent Events (text/event-stream)

    Each event contains a chunk of the agent's response:
    ```
    data: Hello
    data:  there
    data: ! How
    data:  can
    data:  I help
    data:  you?
    ```

    **Example Usage (JavaScript):**
    ```javascript
    const eventSource = new EventSource('/api/v1/agents/stream', {
        headers: {'Authorization': 'Bearer YOUR_TOKEN'}
    });

    eventSource.onmessage = (event) => {
        console.log('Chunk:', event.data);
    };
    ```
    """,
    responses={
        200: {
            "description": "Streaming response started",
            "content": {
                "text/event-stream": {
                    "example": "data: Hello! How can I help you today?\n\n"
                }
            }
        },
        401: {
            "description": "Not authenticated"
        },
        404: {
            "description": "Agent not found"
        },
        429: {
            "description": "Rate limit exceeded"
        }
    },
    tags=["Agents"]
)
async def stream_agent(
    request: AgentInvokeRequest,
    agent: CurrentAgent,
):
    """
    Invoke agent with streaming response.

    Returns a Server-Sent Events stream with agent response chunks.
    """
    async def generate():
        async for chunk in agent.stream(AgentInput(message=request.message)):
            yield f"data: {chunk.content}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post(
    "/{agent_id}/invoke-async",
    response_model=AsyncInvokeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Invoke agent asynchronously",
    description="""
    Queue an agent invocation as a background task using Celery.

    This endpoint immediately returns a task ID that can be used to track
    the invocation status and retrieve results when ready.

    **Use Cases:**
    - Long-running agent operations (>30 seconds)
    - Batch processing
    - Operations that can tolerate delayed responses
    - Resource-intensive agent invocations

    **Authentication Required:** Bearer token or API key

    **Rate Limiting:** 100 requests/minute

    **Workflow:**
    1. POST to this endpoint to queue the task
    2. Receive task_id in response
    3. Poll `/agents/tasks/{task_id}` to check status
    4. Retrieve result when task completes

    **Example Request:**
    ```json
    {
        "message": "Analyze this large dataset...",
        "session_id": "session_123",
        "metadata": {"priority": "high"}
    }
    ```

    **Example Response:**
    ```json
    {
        "task_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "queued",
        "message": "Agent invocation queued successfully",
        "status_url": "/api/v1/agents/tasks/550e8400-e29b-41d4-a716-446655440000"
    }
    ```
    """,
    responses={
        202: {
            "description": "Task queued successfully",
        },
        400: {
            "description": "Invalid request parameters"
        },
        401: {
            "description": "Not authenticated"
        },
        404: {
            "description": "Agent not found"
        },
        429: {
            "description": "Rate limit exceeded"
        }
    },
    tags=["Background Jobs"]
)
async def invoke_agent_async(
    agent_id: str,
    request: AgentInvokeRequest,
    user: UserInfo = Depends(get_current_user_any),
):
    """
    Invoke agent asynchronously via Celery task queue.

    Returns immediately with a task ID for tracking.
    """
    try:
        # Import here to avoid circular dependency
        from agent_service.workers.tasks.agent_tasks import invoke_agent_async

        # Queue the task
        task = invoke_agent_async.delay(
            agent_id=agent_id,
            message=request.message,
            user_id=user.id,
            session_id=request.session_id,
            metadata=request.metadata,
        )

        return AsyncInvokeResponse(
            task_id=str(task.id),
            status="queued",
            message="Agent invocation queued successfully",
            status_url=f"/api/v1/agents/tasks/{task.id}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue agent invocation: {str(e)}"
        )


@router.get(
    "/tasks/{task_id}",
    response_model=TaskStatusResponse,
    summary="Get task status",
    description="""
    Get the status and result of an async agent invocation task.

    Poll this endpoint to track task progress and retrieve results.

    **Task States:**
    - `PENDING`: Task queued, not started yet
    - `STARTED`: Task is currently running
    - `SUCCESS`: Task completed successfully (result available)
    - `FAILURE`: Task failed (error message available)
    - `RETRY`: Task is being retried after failure

    **Example Response (In Progress):**
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

    **Example Response (Completed):**
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
    """,
    responses={
        200: {
            "description": "Task status retrieved successfully"
        },
        404: {
            "description": "Task not found"
        }
    },
    tags=["Background Jobs"]
)
async def get_task_status(
    task_id: str,
):
    """
    Get status and result of an async agent invocation task.

    Returns current task state, progress, and result if completed.
    """
    try:
        from agent_service.workers.celery_app import get_task_info

        task_info = get_task_info(task_id)

        # Map Celery states to human-readable status
        state_to_status = {
            "PENDING": "queued",
            "STARTED": "processing",
            "SUCCESS": "completed",
            "FAILURE": "failed",
            "RETRY": "retrying",
        }

        # Get progress from task metadata if available
        progress = None
        if isinstance(task_info.get("info"), dict):
            progress = task_info["info"].get("progress")

        return TaskStatusResponse(
            task_id=task_id,
            state=task_info["state"],
            status=state_to_status.get(task_info["state"], "unknown"),
            progress=progress,
            result=task_info.get("result") if task_info["successful"] else None,
            error=str(task_info.get("result")) if task_info.get("failed") else None,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}"
        )
