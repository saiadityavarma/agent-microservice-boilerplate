"""
A2A (Agent-to-Agent) protocol handler implementation.

This handler implements the A2A protocol for agent-to-agent communication,
supporting task lifecycle management, message handling, and streaming responses.
"""
import json
import logging
from typing import Any, AsyncGenerator
from fastapi import Request, HTTPException

from agent_service.interfaces import IProtocolHandler, ProtocolType, IAgent, AgentInput
from agent_service.protocols.a2a.messages import (
    A2AMessage,
    TaskStatus,
    TaskCreateRequest,
    TaskResponse,
    TaskUpdateRequest,
    StreamEvent,
    TextPart,
    DataPart,
)
from agent_service.protocols.a2a.task_manager import get_task_manager
from agent_service.protocols.a2a.discovery import get_agent_discovery

logger = logging.getLogger(__name__)


class A2AHandler(IProtocolHandler):
    """
    A2A protocol handler.

    Implements the Agent-to-Agent protocol with:
    - Task lifecycle: created -> working -> input-required -> completed/failed/cancelled
    - Message handling with parts (text, file, data)
    - Streaming responses via Server-Sent Events
    - Agent card discovery
    """

    def __init__(self):
        """Initialize A2A handler."""
        self.task_manager = get_task_manager()
        self.discovery = get_agent_discovery()

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.A2A

    async def handle_request(self, request: Request, agent: IAgent) -> Any:
        """
        Handle A2A task request.

        Supports:
        - POST /a2a/tasks - Create a new task
        - GET /a2a/tasks/{task_id} - Get task status
        - POST /a2a/tasks/{task_id}/messages - Add message to task

        Args:
            request: FastAPI request
            agent: Agent to invoke

        Returns:
            A2A response format
        """
        try:
            # Parse request path to determine operation
            path = request.url.path

            if path.endswith("/tasks") and request.method == "POST":
                # Create new task
                body = await request.json()
                task_request = TaskCreateRequest(**body)
                return await self._create_task(task_request, agent)

            elif "/tasks/" in path:
                # Extract task_id from path
                parts = path.split("/tasks/")
                if len(parts) > 1:
                    task_parts = parts[1].split("/")
                    task_id = task_parts[0]

                    if len(task_parts) == 1 and request.method == "GET":
                        # Get task
                        return await self._get_task(task_id)

                    elif len(task_parts) > 1 and task_parts[1] == "messages" and request.method == "POST":
                        # Add message to task
                        body = await request.json()
                        message = A2AMessage(**body)
                        return await self._add_message(task_id, message, agent)

            raise HTTPException(status_code=404, detail="Endpoint not found")

        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON")
        except Exception as e:
            logger.error(f"Error handling A2A request: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def handle_stream(self, request: Request, agent: IAgent) -> AsyncGenerator[str, None]:
        """
        Handle A2A streaming request.

        Streams task lifecycle events and agent responses as SSE.

        Args:
            request: FastAPI request
            agent: Agent to invoke

        Yields:
            SSE formatted A2A events
        """
        try:
            body = await request.json()
            task_request = TaskCreateRequest(**body)

            # Create task
            task = await self.task_manager.create_task(
                agent_id=task_request.agent_id,
                message=task_request.message,
                context=task_request.context
            )

            # Emit task created event
            yield self._format_sse_event(StreamEvent(
                task_id=task.task_id,
                event_type="status",
                data={"status": TaskStatus.CREATED}
            ))

            # Update status to working
            await self.task_manager.update_task_status(task.task_id, TaskStatus.WORKING)
            yield self._format_sse_event(StreamEvent(
                task_id=task.task_id,
                event_type="status",
                data={"status": TaskStatus.WORKING}
            ))

            # Extract message text from parts
            message_text = self._extract_text_from_message(task_request.message)

            # Execute agent
            agent_input = AgentInput(
                message=message_text,
                context=task_request.context
            )

            # Stream agent response
            response_parts = []
            async for chunk in agent.stream(agent_input):
                if chunk.type == "text":
                    # Create text part
                    text_part = TextPart(text=chunk.content)
                    response_parts.append(text_part)

                    # Emit message chunk event
                    yield self._format_sse_event(StreamEvent(
                        task_id=task.task_id,
                        event_type="message",
                        data={
                            "part": text_part.model_dump(mode='json'),
                            "partial": True
                        }
                    ))

                elif chunk.type == "tool_start":
                    # Emit tool call event
                    yield self._format_sse_event(StreamEvent(
                        task_id=task.task_id,
                        event_type="message",
                        data={
                            "part": {
                                "type": "data",
                                "data": {
                                    "tool": chunk.metadata.get("tool_name") if chunk.metadata else "unknown",
                                    "status": "started"
                                }
                            },
                            "partial": True
                        }
                    ))

                elif chunk.type == "tool_end":
                    # Emit tool result event
                    tool_result = chunk.metadata.get("result") if chunk.metadata else {}
                    data_part = DataPart(data={"tool_result": tool_result})
                    response_parts.append(data_part)

                    yield self._format_sse_event(StreamEvent(
                        task_id=task.task_id,
                        event_type="message",
                        data={
                            "part": data_part.model_dump(mode='json'),
                            "partial": True
                        }
                    ))

                elif chunk.type == "error":
                    # Update task to failed
                    await self.task_manager.update_task_status(
                        task.task_id,
                        TaskStatus.FAILED,
                        error=chunk.content
                    )

                    yield self._format_sse_event(StreamEvent(
                        task_id=task.task_id,
                        event_type="error",
                        data={"error": chunk.content}
                    ))
                    return

            # Add response message to task
            response_message = A2AMessage(
                role="assistant",
                parts=response_parts
            )
            await self.task_manager.add_message_to_task(task.task_id, response_message)

            # Update status to completed
            await self.task_manager.update_task_status(task.task_id, TaskStatus.COMPLETED)

            # Emit completion event
            yield self._format_sse_event(StreamEvent(
                task_id=task.task_id,
                event_type="complete",
                data={
                    "status": TaskStatus.COMPLETED,
                    "task": (await self.task_manager.get_task(task.task_id)).model_dump(mode='json')
                }
            ))

        except Exception as e:
            logger.error(f"Error in A2A stream: {e}", exc_info=True)
            error_event = StreamEvent(
                task_id="unknown",
                event_type="error",
                data={"error": str(e)}
            )
            yield self._format_sse_event(error_event)

    def get_capability_info(self) -> dict[str, Any]:
        """
        Return A2A agent card.

        Returns:
            Agent card dictionary
        """
        return self.discovery.get_well_known_config(base_url="/a2a")

    async def _create_task(
        self,
        task_request: TaskCreateRequest,
        agent: IAgent
    ) -> TaskResponse:
        """
        Create a new task and optionally execute it.

        Args:
            task_request: Task creation request
            agent: Agent to execute the task

        Returns:
            Created task response
        """
        # Create task
        task = await self.task_manager.create_task(
            agent_id=task_request.agent_id,
            message=task_request.message,
            context=task_request.context
        )

        # If not streaming, execute immediately
        if not task_request.stream:
            try:
                # Update to working
                await self.task_manager.update_task_status(task.task_id, TaskStatus.WORKING)

                # Extract message text
                message_text = self._extract_text_from_message(task_request.message)

                # Execute agent
                agent_input = AgentInput(
                    message=message_text,
                    context=task_request.context
                )
                result = await agent.invoke(agent_input)

                # Add response message
                response_message = A2AMessage(
                    role="assistant",
                    parts=[TextPart(text=result.content)]
                )
                await self.task_manager.add_message_to_task(task.task_id, response_message)

                # Update to completed
                await self.task_manager.update_task_status(task.task_id, TaskStatus.COMPLETED)

            except Exception as e:
                logger.error(f"Error executing task: {e}", exc_info=True)
                await self.task_manager.update_task_status(
                    task.task_id,
                    TaskStatus.FAILED,
                    error=str(e)
                )

        # Return updated task
        return await self.task_manager.get_task(task.task_id)

    async def _get_task(self, task_id: str) -> TaskResponse:
        """
        Get task by ID.

        Args:
            task_id: Task identifier

        Returns:
            Task response

        Raises:
            HTTPException: If task not found
        """
        task = await self.task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return task

    async def _add_message(
        self,
        task_id: str,
        message: A2AMessage,
        agent: IAgent
    ) -> TaskResponse:
        """
        Add a message to a task and process it.

        Args:
            task_id: Task identifier
            message: Message to add
            agent: Agent to process the message

        Returns:
            Updated task response

        Raises:
            HTTPException: If task not found
        """
        task = await self.task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        # Add user message
        await self.task_manager.add_message_to_task(task_id, message)

        # Update to working
        await self.task_manager.update_task_status(task_id, TaskStatus.WORKING)

        try:
            # Extract message text
            message_text = self._extract_text_from_message(message)

            # Execute agent
            agent_input = AgentInput(
                message=message_text,
                context=task.metadata
            )
            result = await agent.invoke(agent_input)

            # Add response message
            response_message = A2AMessage(
                role="assistant",
                parts=[TextPart(text=result.content)]
            )
            await self.task_manager.add_message_to_task(task_id, response_message)

            # Update to completed or input_required based on result
            if result.metadata and result.metadata.get("requires_input"):
                await self.task_manager.update_task_status(task_id, TaskStatus.INPUT_REQUIRED)
            else:
                await self.task_manager.update_task_status(task_id, TaskStatus.COMPLETED)

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await self.task_manager.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error=str(e)
            )

        # Return updated task
        return await self.task_manager.get_task(task_id)

    def _extract_text_from_message(self, message: A2AMessage) -> str:
        """
        Extract text content from message parts.

        Args:
            message: A2A message

        Returns:
            Concatenated text from all text parts
        """
        text_parts = []
        for part in message.parts:
            if isinstance(part, TextPart) or (hasattr(part, 'type') and part.type == "text"):
                text_parts.append(part.text)
            elif isinstance(part, DataPart) or (hasattr(part, 'type') and part.type == "data"):
                # Convert data to text representation
                text_parts.append(json.dumps(part.data, indent=2))

        return "\n".join(text_parts) if text_parts else ""

    def _format_sse_event(self, event: StreamEvent) -> str:
        """
        Format event as Server-Sent Event.

        Args:
            event: Stream event

        Returns:
            SSE formatted string
        """
        event_dict = event.model_dump(mode='json')
        return f"data: {json.dumps(event_dict)}\n\n"
