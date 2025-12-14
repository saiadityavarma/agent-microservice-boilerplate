"""
Agent-to-Agent (A2A) protocol handler.

This module provides the A2A protocol implementation for agent-to-agent
communication with task lifecycle management and message handling.
"""
from agent_service.protocols.a2a.handler import A2AHandler
from agent_service.protocols.a2a.messages import (
    MessagePartType,
    TextPart,
    FilePart,
    DataPart,
    MessagePart,
    A2AMessage,
    TaskStatus,
    TaskCreateRequest,
    TaskResponse,
    TaskUpdateRequest,
    TaskListResponse,
    StreamEvent,
)
from agent_service.protocols.a2a.task_manager import (
    TaskManager,
    get_task_manager,
)
from agent_service.protocols.a2a.discovery import (
    AgentSkill,
    AgentCard,
    AgentDiscovery,
    get_agent_discovery,
)

__all__ = [
    # Handler
    "A2AHandler",

    # Message parts
    "MessagePartType",
    "TextPart",
    "FilePart",
    "DataPart",
    "MessagePart",

    # Messages
    "A2AMessage",
    "TaskStatus",
    "TaskCreateRequest",
    "TaskResponse",
    "TaskUpdateRequest",
    "TaskListResponse",
    "StreamEvent",

    # Task management
    "TaskManager",
    "get_task_manager",

    # Discovery
    "AgentSkill",
    "AgentCard",
    "AgentDiscovery",
    "get_agent_discovery",
]
