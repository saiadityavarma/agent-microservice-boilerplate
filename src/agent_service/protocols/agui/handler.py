"""
AG-UI (Agent-User Interaction) protocol handler.

This handler implements the AG-UI protocol for real-time agent-UI communication,
supporting event emission, state synchronization, and streaming responses.
"""
import json
import uuid
import logging
from typing import Any, AsyncGenerator
from fastapi import Request, HTTPException

from agent_service.interfaces import IProtocolHandler, ProtocolType, IAgent, AgentInput
from agent_service.protocols.agui.events import (
    AGUIEventType,
    RunStartedEvent,
    RunFinishedEvent,
    RunFailedEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    ToolCallStartEvent,
    ToolCallEndEvent,
    ToolCallErrorEvent,
    StateSyncEvent,
    create_event,
)
from agent_service.protocols.agui.state import RunState, get_state_manager

logger = logging.getLogger(__name__)


class AGUIHandler(IProtocolHandler):
    """
    AG-UI protocol handler for frontend integration.

    Features:
    - Event emission (RUN_*, TEXT_MESSAGE_*, TOOL_CALL_*, STATE_*)
    - Streaming via Server-Sent Events
    - State synchronization with frontend
    - Tool call event tracking
    """

    def __init__(self):
        """Initialize AG-UI handler."""
        self.state_manager = get_state_manager()
        self._active_runs: dict[str, RunState] = {}

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.AGUI

    async def handle_request(self, request: Request, agent: IAgent) -> Any:
        """
        Non-streaming request handling.

        AG-UI typically uses streaming, but this can be used for state queries.
        """
        try:
            # Parse request
            path = request.url.path

            # Handle state sync request
            if path.endswith("/state"):
                return {
                    "state": self.state_manager.get_state(),
                    "version": self.state_manager.get_version()
                }

            # Handle capabilities request
            if path.endswith("/capabilities"):
                return self.get_capability_info()

            raise HTTPException(
                status_code=404,
                detail="AG-UI primarily uses streaming. Use /agui/stream endpoint."
            )

        except Exception as e:
            logger.error(f"Error handling AG-UI request: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def handle_stream(self, request: Request, agent: IAgent) -> AsyncGenerator[str, None]:
        """
        Handle AG-UI streaming request.

        Emits events in the following sequence:
        1. RUN_STARTED - Agent run begins
        2. TEXT_MESSAGE_START - Message starts
        3. TEXT_MESSAGE_CONTENT - Content chunks (streaming)
        4. TOOL_CALL_* - Tool execution events
        5. STATE_* - State updates
        6. TEXT_MESSAGE_END - Message ends
        7. RUN_FINISHED - Agent run completes

        Args:
            request: FastAPI request
            agent: Agent to invoke

        Yields:
            SSE formatted AG-UI events
        """
        run_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        run_state = RunState(run_id)
        self._active_runs[run_id] = run_state

        try:
            # Parse request body
            body = await request.json()
            message = body.get("message", "")
            context = body.get("context", {})
            include_state = body.get("include_state", True)

            # Emit RUN_STARTED
            run_started = RunStartedEvent(
                run_id=run_id,
                agent_name=agent.name,
                input_message=message,
                metadata={"context": context}
            )
            yield self._format_sse_event(run_started)

            # Emit initial state sync if requested
            if include_state:
                state_sync = StateSyncEvent(
                    run_id=run_id,
                    state=run_state.state_manager.get_state(),
                    version=run_state.state_manager.get_version()
                )
                yield self._format_sse_event(state_sync)

            # Emit TEXT_MESSAGE_START
            message_start = TextMessageStartEvent(
                run_id=run_id,
                message_id=message_id,
                role="assistant"
            )
            yield self._format_sse_event(message_start)

            # Execute agent with streaming
            agent_input = AgentInput(
                message=message,
                context=context
            )

            full_content = []
            current_tool_call_id = None

            async for chunk in agent.stream(agent_input):
                if chunk.type == "text":
                    # Emit TEXT_MESSAGE_CONTENT
                    content_event = TextMessageContentEvent(
                        run_id=run_id,
                        message_id=message_id,
                        content=chunk.content,
                        delta=True
                    )
                    yield self._format_sse_event(content_event)
                    full_content.append(chunk.content)

                elif chunk.type == "tool_start":
                    # Emit TOOL_CALL_START
                    current_tool_call_id = str(uuid.uuid4())
                    tool_name = chunk.metadata.get("tool_name", "unknown") if chunk.metadata else "unknown"
                    tool_args = chunk.metadata.get("arguments", {}) if chunk.metadata else {}

                    tool_start = ToolCallStartEvent(
                        run_id=run_id,
                        tool_call_id=current_tool_call_id,
                        tool_name=tool_name,
                        arguments=tool_args
                    )
                    yield self._format_sse_event(tool_start)

                    # Update state
                    run_state.state_manager.update_state({
                        "current_tool": tool_name,
                        "tool_status": "running"
                    })

                elif chunk.type == "tool_end":
                    # Emit TOOL_CALL_END
                    if current_tool_call_id:
                        tool_result = chunk.metadata.get("result") if chunk.metadata else None

                        tool_end = ToolCallEndEvent(
                            run_id=run_id,
                            tool_call_id=current_tool_call_id,
                            result=tool_result,
                            success=True
                        )
                        yield self._format_sse_event(tool_end)

                        # Update state
                        run_state.state_manager.update_state({
                            "current_tool": None,
                            "tool_status": "completed",
                            "last_tool_result": tool_result
                        })

                        current_tool_call_id = None

                elif chunk.type == "error":
                    # Emit TOOL_CALL_ERROR if in tool, otherwise emit TEXT_MESSAGE_END
                    if current_tool_call_id:
                        tool_error = ToolCallErrorEvent(
                            run_id=run_id,
                            tool_call_id=current_tool_call_id,
                            error=chunk.content,
                            error_type="execution_error"
                        )
                        yield self._format_sse_event(tool_error)
                        current_tool_call_id = None

                    # Mark run as failed
                    run_state.finish(error=chunk.content)

                    # Emit RUN_FAILED
                    run_failed = RunFailedEvent(
                        run_id=run_id,
                        error=chunk.content,
                        error_type="agent_error"
                    )
                    yield self._format_sse_event(run_failed)
                    return

            # Emit TEXT_MESSAGE_END
            final_content = "".join(full_content)
            message_end = TextMessageEndEvent(
                run_id=run_id,
                message_id=message_id,
                full_content=final_content
            )
            yield self._format_sse_event(message_end)

            # Mark run as finished
            run_state.finish()

            # Emit final state sync
            if include_state:
                final_state_sync = StateSyncEvent(
                    run_id=run_id,
                    state=run_state.state_manager.get_state(),
                    version=run_state.state_manager.get_version()
                )
                yield self._format_sse_event(final_state_sync)

            # Emit RUN_FINISHED
            run_finished = RunFinishedEvent(
                run_id=run_id,
                final_message=final_content,
                metadata=run_state.get_metadata()
            )
            yield self._format_sse_event(run_finished)

        except Exception as e:
            logger.error(f"Error in AG-UI stream: {e}", exc_info=True)

            # Mark run as failed
            run_state.finish(error=str(e))

            # Emit RUN_FAILED
            run_failed = RunFailedEvent(
                run_id=run_id,
                error=str(e),
                error_type="internal_error",
                metadata=run_state.get_metadata()
            )
            yield self._format_sse_event(run_failed)

        finally:
            # Cleanup
            if run_id in self._active_runs:
                del self._active_runs[run_id]

    def get_capability_info(self) -> dict[str, Any]:
        """
        Return AG-UI server capabilities.

        Returns:
            Capabilities dictionary
        """
        return {
            "protocol": "ag-ui",
            "version": "1.0",
            "capabilities": {
                "streaming": True,
                "stateManagement": True,
                "toolCalls": True,
                "eventTypes": [event_type.value for event_type in AGUIEventType],
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

    def get_active_runs(self) -> dict[str, dict[str, Any]]:
        """
        Get information about active runs.

        Returns:
            Dictionary of run_id -> run metadata
        """
        return {
            run_id: run_state.get_metadata()
            for run_id, run_state in self._active_runs.items()
        }

    def _format_sse_event(self, event: Any) -> str:
        """
        Format event as Server-Sent Event.

        Args:
            event: Event object

        Returns:
            SSE formatted string
        """
        event_dict = event.model_dump(mode='json')
        return f"data: {json.dumps(event_dict)}\n\n"
