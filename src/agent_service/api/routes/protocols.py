# src/agent_service/api/routes/protocols.py
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from agent_service.protocols.registry import protocol_registry
from agent_service.interfaces import ProtocolType
from agent_service.agent.registry import get_default_agent

router = APIRouter()


@router.get("/.well-known/agent.json")
async def agent_card():
    """A2A agent card endpoint."""
    handler = protocol_registry.get(ProtocolType.A2A)
    if handler:
        return handler.get_capability_info()
    return JSONResponse(status_code=404, content={"error": "A2A not enabled"})


@router.post("/{protocol}/invoke")
async def protocol_invoke(protocol: ProtocolType, request: Request):
    """Generic protocol invoke endpoint."""
    handler = protocol_registry.get(protocol)
    if not handler:
        return JSONResponse(status_code=404, content={"error": f"{protocol} not enabled"})

    agent = get_default_agent()
    return await handler.handle_request(request, agent)


@router.post("/{protocol}/stream")
async def protocol_stream(protocol: ProtocolType, request: Request):
    """Generic protocol stream endpoint."""
    handler = protocol_registry.get(protocol)
    if not handler:
        return JSONResponse(status_code=404, content={"error": f"{protocol} not enabled"})

    agent = get_default_agent()
    return StreamingResponse(
        handler.handle_stream(request, agent),
        media_type="text/event-stream",
    )


# MCP-specific endpoints
@router.get("/mcp")
async def mcp_sse_endpoint(request: Request):
    """
    MCP SSE endpoint for Server-Sent Events.

    This endpoint provides SSE transport for MCP communication.
    """
    handler = protocol_registry.get(ProtocolType.MCP)
    if not handler:
        return JSONResponse(status_code=404, content={"error": "MCP not enabled"})

    agent = get_default_agent()
    return StreamingResponse(
        handler.handle_stream(request, agent),
        media_type="text/event-stream",
    )


@router.post("/mcp/tools/{tool_name}")
async def mcp_direct_tool_invocation(tool_name: str, request: Request):
    """
    Direct tool invocation via MCP.

    Args:
        tool_name: Name of the tool to invoke
        request: Request containing tool arguments

    Returns:
        Tool execution result
    """
    from agent_service.tools.registry import tool_registry

    if not protocol_registry.is_registered("mcp"):
        return JSONResponse(status_code=404, content={"error": "MCP not enabled"})

    try:
        body = await request.json()
        arguments = body.get("arguments", {})

        # Execute tool
        result = await tool_registry.execute(tool_name, **arguments)

        return {
            "success": True,
            "tool": tool_name,
            "result": result
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")


@router.get("/mcp/tools")
async def list_mcp_tools():
    """
    List all available MCP tools.

    Returns:
        List of tool schemas in MCP format
    """
    if not protocol_registry.is_registered("mcp"):
        return JSONResponse(status_code=404, content={"error": "MCP not enabled"})

    from agent_service.tools.registry import tool_registry

    tools = []
    for tool_schema in tool_registry.list_tools():
        tools.append({
            "name": tool_schema.name,
            "description": tool_schema.description,
            "inputSchema": tool_schema.parameters
        })

    return {"tools": tools}


@router.get("/mcp/info")
async def mcp_info():
    """
    Get MCP server information.

    Returns:
        MCP server capabilities and metadata
    """
    handler = protocol_registry.get(ProtocolType.MCP)
    if not handler:
        return JSONResponse(status_code=404, content={"error": "MCP not enabled"})

    return handler.get_capability_info()


# A2A-specific endpoints
@router.post("/a2a/tasks")
async def create_a2a_task(request: Request):
    """
    Create a new A2A task.

    Args:
        request: Request containing task creation data

    Returns:
        Created task response
    """
    handler = protocol_registry.get(ProtocolType.A2A)
    if not handler:
        return JSONResponse(status_code=404, content={"error": "A2A not enabled"})

    agent = get_default_agent()
    return await handler.handle_request(request, agent)


@router.get("/a2a/tasks/{task_id}")
async def get_a2a_task(task_id: str):
    """
    Get A2A task by ID.

    Args:
        task_id: Task identifier

    Returns:
        Task response
    """
    from agent_service.protocols.a2a.task_manager import get_task_manager

    if not protocol_registry.is_registered("a2a"):
        return JSONResponse(status_code=404, content={"error": "A2A not enabled"})

    task_manager = get_task_manager()
    task = await task_manager.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return task


@router.post("/a2a/tasks/{task_id}/messages")
async def add_a2a_message(task_id: str, request: Request):
    """
    Add a message to an A2A task.

    Args:
        task_id: Task identifier
        request: Request containing message data

    Returns:
        Updated task response
    """
    handler = protocol_registry.get(ProtocolType.A2A)
    if not handler:
        return JSONResponse(status_code=404, content={"error": "A2A not enabled"})

    agent = get_default_agent()
    return await handler.handle_request(request, agent)


@router.get("/a2a/tasks")
async def list_a2a_tasks(
    agent_id: str | None = None,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0
):
    """
    List A2A tasks with optional filtering.

    Args:
        agent_id: Filter by agent ID
        status: Filter by task status
        limit: Maximum number of tasks to return
        offset: Number of tasks to skip

    Returns:
        List of task responses
    """
    from agent_service.protocols.a2a.task_manager import get_task_manager
    from agent_service.protocols.a2a.messages import TaskStatus

    if not protocol_registry.is_registered("a2a"):
        return JSONResponse(status_code=404, content={"error": "A2A not enabled"})

    task_manager = get_task_manager()

    # Convert status string to enum if provided
    status_enum = None
    if status:
        try:
            status_enum = TaskStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    tasks = await task_manager.list_tasks(
        agent_id=agent_id,
        status=status_enum,
        limit=limit,
        offset=offset
    )

    return {
        "tasks": tasks,
        "total": len(tasks),
        "page": (offset // limit) + 1 if limit > 0 else 1,
        "page_size": limit
    }


@router.post("/a2a/stream")
async def a2a_stream(request: Request):
    """
    A2A streaming endpoint.

    Streams task lifecycle events and agent responses via SSE.

    Args:
        request: Request containing task creation data

    Returns:
        StreamingResponse with SSE events
    """
    handler = protocol_registry.get(ProtocolType.A2A)
    if not handler:
        return JSONResponse(status_code=404, content={"error": "A2A not enabled"})

    agent = get_default_agent()
    return StreamingResponse(
        handler.handle_stream(request, agent),
        media_type="text/event-stream",
    )


# AG-UI-specific endpoints
@router.post("/agui/stream")
async def agui_stream(request: Request):
    """
    AG-UI streaming endpoint.

    Streams agent events including RUN_*, TEXT_MESSAGE_*, TOOL_CALL_*, and STATE_* events.

    Args:
        request: Request containing message and context

    Returns:
        StreamingResponse with SSE events
    """
    handler = protocol_registry.get(ProtocolType.AGUI)
    if not handler:
        return JSONResponse(status_code=404, content={"error": "AG-UI not enabled"})

    agent = get_default_agent()
    return StreamingResponse(
        handler.handle_stream(request, agent),
        media_type="text/event-stream",
    )


@router.get("/agui/state")
async def agui_state():
    """
    Get current AG-UI state.

    Returns:
        Current state and version
    """
    from agent_service.protocols.agui.state import get_state_manager

    if not protocol_registry.is_registered("agui"):
        return JSONResponse(status_code=404, content={"error": "AG-UI not enabled"})

    state_manager = get_state_manager()
    return {
        "state": state_manager.get_state(),
        "version": state_manager.get_version()
    }


@router.get("/agui/capabilities")
async def agui_capabilities():
    """
    Get AG-UI server capabilities.

    Returns:
        AG-UI capabilities and metadata
    """
    handler = protocol_registry.get(ProtocolType.AGUI)
    if not handler:
        return JSONResponse(status_code=404, content={"error": "AG-UI not enabled"})

    return handler.get_capability_info()
