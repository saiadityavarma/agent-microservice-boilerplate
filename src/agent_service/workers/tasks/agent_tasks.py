"""
Agent-related background tasks.

This module provides Celery tasks for long-running agent operations:
- Asynchronous agent invocation
- Streaming response handling
- Progress tracking
- Timeout management
- Result storage

Tasks in this module are designed to handle:
- Large language model calls that may take several seconds/minutes
- Streaming responses that need to be collected and stored
- Timeout scenarios where agents don't respond in time
- Error handling and retry logic
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from agent_service.workers.celery_app import celery_app
from agent_service.agent.registry import get_agent
from agent_service.interfaces.agent import AgentInput, AgentOutput
from agent_service.infrastructure.cache.redis import get_redis_manager


# ============================================================================
# Helper Functions
# ============================================================================

async def _store_result_in_cache(
    task_id: str,
    result: Dict[str, Any],
    ttl: int = 3600,
) -> None:
    """
    Store task result in Redis cache for quick retrieval.

    Args:
        task_id: The Celery task ID
        result: The result data to store
        ttl: Time to live in seconds (default: 1 hour)
    """
    redis_manager = await get_redis_manager()
    if redis_manager.is_available:
        cache_key = f"task_result:{task_id}"
        await redis_manager.set(cache_key, result, ttl=ttl)


async def _update_task_progress(
    task_id: str,
    progress: int,
    status: str = "processing",
    message: Optional[str] = None,
) -> None:
    """
    Update task progress in cache.

    Args:
        task_id: The Celery task ID
        progress: Progress percentage (0-100)
        status: Current status message
        message: Optional additional message
    """
    redis_manager = await get_redis_manager()
    if redis_manager.is_available:
        progress_key = f"task_progress:{task_id}"
        progress_data = {
            "progress": progress,
            "status": status,
            "message": message,
            "updated_at": datetime.utcnow().isoformat(),
        }
        await redis_manager.set(progress_key, progress_data, ttl=3600)


# ============================================================================
# Agent Invocation Tasks
# ============================================================================

@celery_app.task(
    bind=True,
    name="agent_service.workers.tasks.agent_tasks.invoke_agent_async",
    max_retries=3,
    default_retry_delay=60,
    rate_limit="100/m",  # 100 invocations per minute
    time_limit=600,  # 10 minutes hard limit
    soft_time_limit=540,  # 9 minutes soft limit
    track_started=True,
)
def invoke_agent_async(
    self: Task,
    agent_id: str,
    message: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Invoke an agent asynchronously and store the result.

    This task:
    1. Retrieves the agent from the registry
    2. Invokes the agent with the provided message
    3. Stores the result in the cache and result backend
    4. Updates progress during execution
    5. Handles timeouts and errors gracefully

    Args:
        agent_id: The agent identifier
        message: The message to send to the agent
        user_id: Optional user ID for tracking
        session_id: Optional session ID for context
        metadata: Optional metadata dictionary

    Returns:
        Dictionary containing:
            - task_id: The Celery task ID
            - agent_id: The agent identifier
            - result: The agent's response
            - status: Task status
            - started_at: When the task started
            - completed_at: When the task completed
            - error: Error message if failed

    Raises:
        ValueError: If agent not found or invalid input
        TimeoutError: If agent invocation exceeds time limit
    """
    task_id = self.request.id
    started_at = datetime.utcnow()

    try:
        # Update progress: Starting
        asyncio.run(_update_task_progress(
            task_id,
            progress=0,
            status="starting",
            message=f"Starting agent invocation for agent: {agent_id}",
        ))

        # Get the agent from registry
        agent = get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")

        # Update progress: Agent retrieved
        asyncio.run(_update_task_progress(
            task_id,
            progress=20,
            status="processing",
            message="Agent retrieved, preparing invocation",
        ))

        # Prepare agent input
        agent_input = AgentInput(
            message=message,
            metadata=metadata or {},
        )

        # Update progress: Invoking agent
        asyncio.run(_update_task_progress(
            task_id,
            progress=40,
            status="processing",
            message="Invoking agent",
        ))

        # Invoke the agent (async)
        agent_output: AgentOutput = asyncio.run(agent.invoke(agent_input))

        # Update progress: Agent responded
        asyncio.run(_update_task_progress(
            task_id,
            progress=80,
            status="processing",
            message="Agent responded, storing result",
        ))

        # Prepare result
        result = {
            "task_id": task_id,
            "agent_id": agent_id,
            "result": {
                "content": agent_output.content,
                "metadata": agent_output.metadata,
            },
            "status": "success",
            "started_at": started_at.isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "session_id": session_id,
            "error": None,
        }

        # Store result in cache for quick retrieval
        asyncio.run(_store_result_in_cache(task_id, result, ttl=3600))

        # Update progress: Complete
        asyncio.run(_update_task_progress(
            task_id,
            progress=100,
            status="completed",
            message="Task completed successfully",
        ))

        return result

    except SoftTimeLimitExceeded:
        # Soft time limit exceeded - log and continue
        print(f"Task {task_id} soft time limit exceeded, attempting to finish gracefully")

        error_result = {
            "task_id": task_id,
            "agent_id": agent_id,
            "result": None,
            "status": "timeout",
            "started_at": started_at.isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "error": "Agent invocation exceeded time limit",
        }

        asyncio.run(_store_result_in_cache(task_id, error_result, ttl=3600))
        raise TimeoutError("Agent invocation exceeded time limit")

    except ValueError as e:
        # Invalid input or agent not found
        error_result = {
            "task_id": task_id,
            "agent_id": agent_id,
            "result": None,
            "status": "failed",
            "started_at": started_at.isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "error": str(e),
        }

        asyncio.run(_store_result_in_cache(task_id, error_result, ttl=3600))
        raise

    except Exception as e:
        # Unexpected error - log and retry
        print(f"Task {task_id} failed with error: {e}")

        error_result = {
            "task_id": task_id,
            "agent_id": agent_id,
            "result": None,
            "status": "failed",
            "started_at": started_at.isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "error": str(e),
        }

        asyncio.run(_store_result_in_cache(task_id, error_result, ttl=3600))

        # Retry the task
        raise self.retry(exc=e, countdown=self.default_retry_delay)


@celery_app.task(
    bind=True,
    name="agent_service.workers.tasks.agent_tasks.invoke_agent_with_streaming",
    max_retries=3,
    default_retry_delay=60,
    rate_limit="50/m",  # 50 streaming invocations per minute
    time_limit=900,  # 15 minutes hard limit for streaming
    soft_time_limit=840,  # 14 minutes soft limit
    track_started=True,
)
def invoke_agent_with_streaming(
    self: Task,
    agent_id: str,
    message: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Invoke an agent with streaming and collect all chunks.

    This task:
    1. Invokes the agent with streaming enabled
    2. Collects all streaming chunks
    3. Stores chunks progressively in cache
    4. Returns complete response when done

    Args:
        agent_id: The agent identifier
        message: The message to send to the agent
        user_id: Optional user ID for tracking
        session_id: Optional session ID for context
        metadata: Optional metadata dictionary

    Returns:
        Dictionary containing:
            - task_id: The Celery task ID
            - agent_id: The agent identifier
            - result: Complete agent response (all chunks combined)
            - chunks: List of all streaming chunks
            - status: Task status
            - started_at: When the task started
            - completed_at: When the task completed

    Raises:
        ValueError: If agent not found or doesn't support streaming
        TimeoutError: If streaming exceeds time limit
    """
    task_id = self.request.id
    started_at = datetime.utcnow()
    chunks = []

    async def collect_streaming_response():
        """Helper function to collect streaming response."""
        nonlocal chunks

        # Get the agent
        agent = get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")

        # Prepare input
        agent_input = AgentInput(
            message=message,
            metadata=metadata or {},
        )

        # Update progress
        await _update_task_progress(
            task_id,
            progress=10,
            status="streaming",
            message="Starting streaming response",
        )

        # Stream the response
        chunk_count = 0
        async for chunk in agent.stream(agent_input):
            chunk_count += 1
            chunks.append({
                "index": chunk_count,
                "content": chunk.content,
                "metadata": chunk.metadata,
                "timestamp": datetime.utcnow().isoformat(),
            })

            # Update progress every 10 chunks
            if chunk_count % 10 == 0:
                progress = min(90, 10 + (chunk_count * 2))  # Cap at 90%
                await _update_task_progress(
                    task_id,
                    progress=progress,
                    status="streaming",
                    message=f"Received {chunk_count} chunks",
                )

                # Store intermediate chunks in cache
                cache_key = f"task_chunks:{task_id}"
                redis_manager = await get_redis_manager()
                if redis_manager.is_available:
                    await redis_manager.set(cache_key, chunks, ttl=3600)

        return chunks

    try:
        # Collect all streaming chunks
        chunks = asyncio.run(collect_streaming_response())

        # Combine all chunk content
        complete_content = "".join([chunk["content"] for chunk in chunks])

        # Prepare result
        result = {
            "task_id": task_id,
            "agent_id": agent_id,
            "result": {
                "content": complete_content,
                "chunks": chunks,
                "chunk_count": len(chunks),
            },
            "status": "success",
            "started_at": started_at.isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "session_id": session_id,
            "error": None,
        }

        # Store result in cache
        asyncio.run(_store_result_in_cache(task_id, result, ttl=3600))

        # Update progress: Complete
        asyncio.run(_update_task_progress(
            task_id,
            progress=100,
            status="completed",
            message=f"Streaming completed with {len(chunks)} chunks",
        ))

        return result

    except SoftTimeLimitExceeded:
        print(f"Task {task_id} soft time limit exceeded during streaming")

        error_result = {
            "task_id": task_id,
            "agent_id": agent_id,
            "result": {
                "content": "".join([c["content"] for c in chunks]),
                "chunks": chunks,
                "chunk_count": len(chunks),
                "partial": True,
            },
            "status": "timeout",
            "started_at": started_at.isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "error": f"Streaming timeout after {len(chunks)} chunks",
        }

        asyncio.run(_store_result_in_cache(task_id, error_result, ttl=3600))
        raise TimeoutError(f"Streaming timeout after {len(chunks)} chunks")

    except Exception as e:
        print(f"Task {task_id} failed during streaming: {e}")

        error_result = {
            "task_id": task_id,
            "agent_id": agent_id,
            "result": None,
            "status": "failed",
            "started_at": started_at.isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "error": str(e),
        }

        asyncio.run(_store_result_in_cache(task_id, error_result, ttl=3600))
        raise self.retry(exc=e, countdown=self.default_retry_delay)


# ============================================================================
# Task Exports
# ============================================================================

__all__ = [
    "invoke_agent_async",
    "invoke_agent_with_streaming",
]
