"""
A2A (Agent-to-Agent) message models.

This module defines the message structure for A2A protocol communication,
including message parts (text, file, data) and request/response models.
"""
from typing import Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class MessagePartType(str, Enum):
    """Types of message parts in A2A protocol."""
    TEXT = "text"
    FILE = "file"
    DATA = "data"


class TextPart(BaseModel):
    """Text message part."""
    type: Literal["text"] = "text"
    text: str = Field(..., description="Text content")


class FilePart(BaseModel):
    """File message part."""
    type: Literal["file"] = "file"
    url: str = Field(..., description="URL to the file")
    mimeType: str | None = Field(None, description="MIME type of the file")
    filename: str | None = Field(None, description="Original filename")
    size: int | None = Field(None, description="File size in bytes")


class DataPart(BaseModel):
    """Structured data message part."""
    type: Literal["data"] = "data"
    data: dict[str, Any] = Field(..., description="Structured data payload")
    schema: str | None = Field(None, description="JSON schema URL or identifier")


MessagePart = TextPart | FilePart | DataPart


class A2AMessage(BaseModel):
    """A2A message structure."""
    role: Literal["user", "assistant", "system"] = Field(..., description="Message sender role")
    parts: list[MessagePart] = Field(..., description="Message parts")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskStatus(str, Enum):
    """Task lifecycle states."""
    CREATED = "created"
    WORKING = "working"
    INPUT_REQUIRED = "input_required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskCreateRequest(BaseModel):
    """Request to create a new task."""
    agent_id: str = Field(..., description="Target agent identifier")
    message: A2AMessage = Field(..., description="Initial message")
    context: dict[str, Any] = Field(default_factory=dict, description="Task context")
    stream: bool = Field(default=False, description="Whether to stream responses")


class TaskResponse(BaseModel):
    """Response containing task information."""
    task_id: str = Field(..., description="Unique task identifier")
    agent_id: str = Field(..., description="Agent handling the task")
    status: TaskStatus = Field(..., description="Current task status")
    messages: list[A2AMessage] = Field(default_factory=list, description="Task messages")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    completed_at: datetime | None = Field(None, description="Completion timestamp")
    error: str | None = Field(None, description="Error message if failed")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Task metadata")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskUpdateRequest(BaseModel):
    """Request to update a task."""
    message: A2AMessage | None = Field(None, description="New message to add")
    status: TaskStatus | None = Field(None, description="New task status")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata to update")


class TaskListResponse(BaseModel):
    """Response containing list of tasks."""
    tasks: list[TaskResponse] = Field(..., description="List of tasks")
    total: int = Field(..., description="Total number of tasks")
    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=20, description="Items per page")


class StreamEvent(BaseModel):
    """Streaming event for task updates."""
    task_id: str = Field(..., description="Task identifier")
    event_type: Literal["status", "message", "error", "complete"] = Field(
        ..., description="Event type"
    )
    data: dict[str, Any] = Field(..., description="Event data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
