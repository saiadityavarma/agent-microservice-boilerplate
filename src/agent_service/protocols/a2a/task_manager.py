"""
A2A task manager for managing task lifecycle and storage.

This module provides task management functionality including:
- Creating and tracking tasks
- Updating task status
- Adding messages to tasks
- Storing tasks in Redis or in-memory fallback
"""
import json
import uuid
import logging
from typing import Optional
from datetime import datetime, timedelta

from agent_service.protocols.a2a.messages import (
    A2AMessage,
    TaskResponse,
    TaskStatus,
    TaskCreateRequest,
)
from agent_service.config.settings import get_settings

logger = logging.getLogger(__name__)


class TaskManager:
    """
    Manager for A2A tasks with Redis storage and in-memory fallback.

    Features:
    - Task creation and retrieval
    - Status updates and message appending
    - Automatic task expiration
    - Redis storage with in-memory fallback
    """

    def __init__(self):
        """Initialize task manager."""
        self._redis_client: Optional[object] = None
        self._memory_store: dict[str, TaskResponse] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Redis connection if available."""
        if self._initialized:
            return

        settings = get_settings()
        if settings.redis_url:
            try:
                from agent_service.infrastructure.cache.redis import RedisManager
                redis_manager = RedisManager()
                await redis_manager.initialize()
                self._redis_client = await redis_manager.get_client()
                logger.info("Task manager initialized with Redis storage")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis for task manager: {e}")
                logger.info("Using in-memory task storage (not suitable for production)")
        else:
            logger.info("Redis not configured, using in-memory task storage")

        self._initialized = True

    def _get_task_key(self, task_id: str) -> str:
        """Generate Redis key for task."""
        return f"a2a:task:{task_id}"

    async def create_task(
        self,
        agent_id: str,
        message: A2AMessage,
        context: dict | None = None
    ) -> TaskResponse:
        """
        Create a new task.

        Args:
            agent_id: Identifier of the agent handling the task
            message: Initial message for the task
            context: Optional task context

        Returns:
            Created task response
        """
        await self.initialize()

        task_id = str(uuid.uuid4())
        now = datetime.utcnow()

        task = TaskResponse(
            task_id=task_id,
            agent_id=agent_id,
            status=TaskStatus.CREATED,
            messages=[message],
            created_at=now,
            updated_at=now,
            metadata=context or {}
        )

        await self._save_task(task)
        logger.info(f"Created task {task_id} for agent {agent_id}")
        return task

    async def get_task(self, task_id: str) -> Optional[TaskResponse]:
        """
        Retrieve a task by ID.

        Args:
            task_id: Task identifier

        Returns:
            Task response if found, None otherwise
        """
        await self.initialize()

        if self._redis_client:
            try:
                key = self._get_task_key(task_id)
                data = await self._redis_client.get(key)
                if data:
                    task_dict = json.loads(data)
                    return TaskResponse(**task_dict)
            except Exception as e:
                logger.error(f"Error retrieving task from Redis: {e}")
                # Fallback to memory store
                return self._memory_store.get(task_id)
        else:
            return self._memory_store.get(task_id)

        return None

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        error: Optional[str] = None
    ) -> Optional[TaskResponse]:
        """
        Update task status.

        Args:
            task_id: Task identifier
            status: New task status
            error: Optional error message if status is FAILED

        Returns:
            Updated task response if found, None otherwise
        """
        task = await self.get_task(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found for status update")
            return None

        task.status = status
        task.updated_at = datetime.utcnow()

        if status == TaskStatus.COMPLETED or status == TaskStatus.FAILED:
            task.completed_at = datetime.utcnow()

        if error:
            task.error = error

        await self._save_task(task)
        logger.info(f"Updated task {task_id} status to {status}")
        return task

    async def add_message_to_task(
        self,
        task_id: str,
        message: A2AMessage
    ) -> Optional[TaskResponse]:
        """
        Add a message to a task.

        Args:
            task_id: Task identifier
            message: Message to add

        Returns:
            Updated task response if found, None otherwise
        """
        task = await self.get_task(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found for message addition")
            return None

        task.messages.append(message)
        task.updated_at = datetime.utcnow()

        await self._save_task(task)
        logger.debug(f"Added message to task {task_id}")
        return task

    async def list_tasks(
        self,
        agent_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        limit: int = 20,
        offset: int = 0
    ) -> list[TaskResponse]:
        """
        List tasks with optional filtering.

        Args:
            agent_id: Filter by agent ID
            status: Filter by task status
            limit: Maximum number of tasks to return
            offset: Number of tasks to skip

        Returns:
            List of task responses
        """
        await self.initialize()

        if self._redis_client:
            try:
                # Get all task keys
                pattern = "a2a:task:*"
                keys = []
                async for key in self._redis_client.scan_iter(match=pattern):
                    keys.append(key)

                # Retrieve tasks
                tasks = []
                for key in keys:
                    data = await self._redis_client.get(key)
                    if data:
                        task_dict = json.loads(data)
                        task = TaskResponse(**task_dict)

                        # Apply filters
                        if agent_id and task.agent_id != agent_id:
                            continue
                        if status and task.status != status:
                            continue

                        tasks.append(task)

                # Sort by updated_at descending
                tasks.sort(key=lambda t: t.updated_at, reverse=True)

                # Apply pagination
                return tasks[offset:offset + limit]

            except Exception as e:
                logger.error(f"Error listing tasks from Redis: {e}")
                # Fallback to memory store
                tasks = list(self._memory_store.values())
        else:
            tasks = list(self._memory_store.values())

        # Apply filters
        if agent_id:
            tasks = [t for t in tasks if t.agent_id == agent_id]
        if status:
            tasks = [t for t in tasks if t.status == status]

        # Sort by updated_at descending
        tasks.sort(key=lambda t: t.updated_at, reverse=True)

        # Apply pagination
        return tasks[offset:offset + limit]

    async def delete_task(self, task_id: str) -> bool:
        """
        Delete a task.

        Args:
            task_id: Task identifier

        Returns:
            True if task was deleted, False otherwise
        """
        await self.initialize()

        if self._redis_client:
            try:
                key = self._get_task_key(task_id)
                result = await self._redis_client.delete(key)
                logger.info(f"Deleted task {task_id} from Redis")
                return result > 0
            except Exception as e:
                logger.error(f"Error deleting task from Redis: {e}")
                # Fallback to memory store
                if task_id in self._memory_store:
                    del self._memory_store[task_id]
                    return True
                return False
        else:
            if task_id in self._memory_store:
                del self._memory_store[task_id]
                logger.info(f"Deleted task {task_id} from memory")
                return True
            return False

    async def _save_task(self, task: TaskResponse) -> None:
        """
        Save task to storage.

        Args:
            task: Task to save
        """
        task_dict = task.model_dump(mode='json')

        if self._redis_client:
            try:
                key = self._get_task_key(task.task_id)
                # Store with 24 hour expiration
                await self._redis_client.setex(
                    key,
                    timedelta(hours=24),
                    json.dumps(task_dict, default=str)
                )
            except Exception as e:
                logger.error(f"Error saving task to Redis: {e}")
                # Fallback to memory store
                self._memory_store[task.task_id] = task
        else:
            self._memory_store[task.task_id] = task

    async def cleanup_expired_tasks(self, max_age_hours: int = 24) -> int:
        """
        Cleanup expired tasks (for in-memory storage only).

        Args:
            max_age_hours: Maximum age of tasks in hours

        Returns:
            Number of tasks cleaned up
        """
        if self._redis_client:
            # Redis handles expiration automatically
            return 0

        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        expired_ids = [
            task_id
            for task_id, task in self._memory_store.items()
            if task.updated_at < cutoff
        ]

        for task_id in expired_ids:
            del self._memory_store[task_id]

        if expired_ids:
            logger.info(f"Cleaned up {len(expired_ids)} expired tasks")

        return len(expired_ids)


# Global task manager instance
_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """
    Get the global task manager instance.

    Returns:
        Global TaskManager instance
    """
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager
