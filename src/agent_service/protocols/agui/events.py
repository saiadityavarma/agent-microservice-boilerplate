"""
AG-UI event types and dataclasses.

This module defines all event types used in the AG-UI protocol for
communicating agent state, messages, and tool calls to the frontend.
"""
from typing import Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class AGUIEventType(str, Enum):
    """AG-UI event types for frontend communication."""
    # Run lifecycle events
    RUN_STARTED = "run_started"
    RUN_FINISHED = "run_finished"
    RUN_FAILED = "run_failed"

    # Message events
    TEXT_MESSAGE_START = "text_message_start"
    TEXT_MESSAGE_CONTENT = "text_message_content"
    TEXT_MESSAGE_END = "text_message_end"

    # Tool call events
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_PROGRESS = "tool_call_progress"
    TOOL_CALL_END = "tool_call_end"
    TOOL_CALL_ERROR = "tool_call_error"

    # State events
    STATE_SYNC = "state_sync"
    STATE_UPDATE = "state_update"

    # Error events
    ERROR = "error"


class BaseEvent(BaseModel):
    """Base class for all AG-UI events."""
    event: str = Field(..., description="Event type")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    run_id: str | None = Field(None, description="Run identifier")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RunStartedEvent(BaseEvent):
    """Event emitted when agent run starts."""
    event: Literal["run_started"] = "run_started"
    agent_name: str = Field(..., description="Name of the agent")
    input_message: str = Field(..., description="Input message to the agent")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RunFinishedEvent(BaseEvent):
    """Event emitted when agent run completes successfully."""
    event: Literal["run_finished"] = "run_finished"
    final_message: str | None = Field(None, description="Final message from the agent")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Run metadata")


class RunFailedEvent(BaseEvent):
    """Event emitted when agent run fails."""
    event: Literal["run_failed"] = "run_failed"
    error: str = Field(..., description="Error message")
    error_type: str = Field(default="unknown", description="Error type")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Error metadata")


class TextMessageStartEvent(BaseEvent):
    """Event emitted when text message starts."""
    event: Literal["text_message_start"] = "text_message_start"
    message_id: str = Field(..., description="Message identifier")
    role: Literal["user", "assistant", "system"] = Field(..., description="Message role")


class TextMessageContentEvent(BaseEvent):
    """Event emitted for text message content chunks."""
    event: Literal["text_message_content"] = "text_message_content"
    message_id: str = Field(..., description="Message identifier")
    content: str = Field(..., description="Content chunk")
    delta: bool = Field(default=True, description="Whether this is a delta or full content")


class TextMessageEndEvent(BaseEvent):
    """Event emitted when text message ends."""
    event: Literal["text_message_end"] = "text_message_end"
    message_id: str = Field(..., description="Message identifier")
    full_content: str | None = Field(None, description="Full message content")


class ToolCallStartEvent(BaseEvent):
    """Event emitted when tool call starts."""
    event: Literal["tool_call_start"] = "tool_call_start"
    tool_call_id: str = Field(..., description="Tool call identifier")
    tool_name: str = Field(..., description="Name of the tool")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class ToolCallProgressEvent(BaseEvent):
    """Event emitted during tool call execution."""
    event: Literal["tool_call_progress"] = "tool_call_progress"
    tool_call_id: str = Field(..., description="Tool call identifier")
    status: str = Field(..., description="Progress status")
    progress: float | None = Field(None, ge=0.0, le=1.0, description="Progress percentage")
    message: str | None = Field(None, description="Progress message")


class ToolCallEndEvent(BaseEvent):
    """Event emitted when tool call completes."""
    event: Literal["tool_call_end"] = "tool_call_end"
    tool_call_id: str = Field(..., description="Tool call identifier")
    result: Any = Field(..., description="Tool execution result")
    success: bool = Field(default=True, description="Whether the call succeeded")


class ToolCallErrorEvent(BaseEvent):
    """Event emitted when tool call fails."""
    event: Literal["tool_call_error"] = "tool_call_error"
    tool_call_id: str = Field(..., description="Tool call identifier")
    error: str = Field(..., description="Error message")
    error_type: str = Field(default="unknown", description="Error type")


class StateSyncEvent(BaseEvent):
    """Event emitted for full state synchronization."""
    event: Literal["state_sync"] = "state_sync"
    state: dict[str, Any] = Field(..., description="Full state object")
    version: int = Field(default=1, description="State version")


class StateUpdateEvent(BaseEvent):
    """Event emitted for incremental state updates."""
    event: Literal["state_update"] = "state_update"
    updates: dict[str, Any] = Field(..., description="State updates (partial)")
    path: str | None = Field(None, description="JSON path for nested updates")


class ErrorEvent(BaseEvent):
    """Generic error event."""
    event: Literal["error"] = "error"
    error: str = Field(..., description="Error message")
    error_type: str = Field(default="unknown", description="Error type")
    recoverable: bool = Field(default=False, description="Whether the error is recoverable")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Error metadata")


# Union type for all events
AGUIEvent = (
    RunStartedEvent |
    RunFinishedEvent |
    RunFailedEvent |
    TextMessageStartEvent |
    TextMessageContentEvent |
    TextMessageEndEvent |
    ToolCallStartEvent |
    ToolCallProgressEvent |
    ToolCallEndEvent |
    ToolCallErrorEvent |
    StateSyncEvent |
    StateUpdateEvent |
    ErrorEvent
)


def create_event(event_type: AGUIEventType, **kwargs) -> AGUIEvent:
    """
    Factory function to create AG-UI events.

    Args:
        event_type: Type of event to create
        **kwargs: Event-specific parameters

    Returns:
        Appropriate event instance
    """
    event_map = {
        AGUIEventType.RUN_STARTED: RunStartedEvent,
        AGUIEventType.RUN_FINISHED: RunFinishedEvent,
        AGUIEventType.RUN_FAILED: RunFailedEvent,
        AGUIEventType.TEXT_MESSAGE_START: TextMessageStartEvent,
        AGUIEventType.TEXT_MESSAGE_CONTENT: TextMessageContentEvent,
        AGUIEventType.TEXT_MESSAGE_END: TextMessageEndEvent,
        AGUIEventType.TOOL_CALL_START: ToolCallStartEvent,
        AGUIEventType.TOOL_CALL_PROGRESS: ToolCallProgressEvent,
        AGUIEventType.TOOL_CALL_END: ToolCallEndEvent,
        AGUIEventType.TOOL_CALL_ERROR: ToolCallErrorEvent,
        AGUIEventType.STATE_SYNC: StateSyncEvent,
        AGUIEventType.STATE_UPDATE: StateUpdateEvent,
        AGUIEventType.ERROR: ErrorEvent,
    }

    event_class = event_map.get(event_type)
    if not event_class:
        raise ValueError(f"Unknown event type: {event_type}")

    return event_class(**kwargs)
