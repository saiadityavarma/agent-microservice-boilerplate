"""
Agent UI (AG-UI) protocol handler.

This module provides the AG-UI protocol implementation for real-time
agent-to-UI communication with event emission and state synchronization.
"""
from agent_service.protocols.agui.handler import AGUIHandler
from agent_service.protocols.agui.events import (
    AGUIEventType,
    AGUIEvent,
    RunStartedEvent,
    RunFinishedEvent,
    RunFailedEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    ToolCallStartEvent,
    ToolCallProgressEvent,
    ToolCallEndEvent,
    ToolCallErrorEvent,
    StateSyncEvent,
    StateUpdateEvent,
    ErrorEvent,
    create_event,
)
from agent_service.protocols.agui.state import (
    StateManager,
    RunState,
    get_state_manager,
)

__all__ = [
    # Handler
    "AGUIHandler",

    # Event types
    "AGUIEventType",
    "AGUIEvent",

    # Run events
    "RunStartedEvent",
    "RunFinishedEvent",
    "RunFailedEvent",

    # Message events
    "TextMessageStartEvent",
    "TextMessageContentEvent",
    "TextMessageEndEvent",

    # Tool call events
    "ToolCallStartEvent",
    "ToolCallProgressEvent",
    "ToolCallEndEvent",
    "ToolCallErrorEvent",

    # State events
    "StateSyncEvent",
    "StateUpdateEvent",

    # Error events
    "ErrorEvent",

    # Utilities
    "create_event",

    # State management
    "StateManager",
    "RunState",
    "get_state_manager",
]
