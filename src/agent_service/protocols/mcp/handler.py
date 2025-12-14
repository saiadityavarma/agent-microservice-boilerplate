"""
MCP (Model Context Protocol) handler implementation.

SDK: pip install fastmcp
Docs: https://github.com/jlowin/fastmcp
"""
from typing import Any, AsyncGenerator
import json
from fastapi import Request, HTTPException

from agent_service.interfaces import IProtocolHandler, ProtocolType, IAgent, AgentInput
from agent_service.protocols.mcp.server import get_mcp_server


class MCPHandler(IProtocolHandler):
    """
    MCP protocol handler.

    Key concepts:
    - Tools: Functions the LLM can call
    - Resources: Data the LLM can read
    - Prompts: Reusable prompt templates

    This handler integrates with FastMCP to expose agent tools via MCP protocol.
    """

    def __init__(self):
        """Initialize MCP handler."""
        self._mcp_server = None

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.MCP

    @property
    def mcp_server(self):
        """Lazy-load MCP server."""
        if self._mcp_server is None:
            self._mcp_server = get_mcp_server()
        return self._mcp_server

    async def handle_request(self, request: Request, agent: IAgent) -> Any:
        """
        Handle MCP request.

        MCP requests can be:
        1. Tool listing (list_tools)
        2. Tool execution (call_tool)
        3. Resource listing (list_resources)
        4. Resource reading (read_resource)
        5. Prompt listing (list_prompts)
        6. Prompt getting (get_prompt)

        Args:
            request: FastAPI request
            agent: Agent to invoke

        Returns:
            MCP response format
        """
        try:
            body = await request.json()
            method = body.get("method")

            if method == "list_tools":
                return await self._list_tools()
            elif method == "call_tool":
                return await self._call_tool(body.get("params", {}), agent)
            elif method == "list_resources":
                return await self._list_resources()
            elif method == "read_resource":
                return await self._read_resource(body.get("params", {}))
            elif method == "list_prompts":
                return await self._list_prompts()
            elif method == "get_prompt":
                return await self._get_prompt(body.get("params", {}))
            else:
                raise HTTPException(status_code=400, detail=f"Unknown method: {method}")

        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def handle_stream(self, request: Request, agent: IAgent) -> AsyncGenerator[str, None]:
        """
        Handle MCP streaming request.

        Streams agent responses as SSE events in MCP format.

        Args:
            request: FastAPI request
            agent: Agent to invoke

        Yields:
            SSE formatted MCP events
        """
        try:
            body = await request.json()
            message = body.get("message", "")
            session_id = body.get("session_id")
            context = body.get("context", {})

            agent_input = AgentInput(
                message=message,
                session_id=session_id,
                context=context
            )

            # Stream agent response
            async for chunk in agent.stream(agent_input):
                # Format as MCP SSE event
                event_data = {
                    "type": chunk.type,
                    "content": chunk.content,
                    "metadata": chunk.metadata or {}
                }
                yield f"data: {json.dumps(event_data)}\n\n"

            # Send completion event
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            error_event = {
                "type": "error",
                "content": str(e),
                "metadata": {}
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    def get_capability_info(self) -> dict[str, Any]:
        """
        Return MCP server info for discovery.

        Returns:
            MCP server capabilities
        """
        return {
            "name": "Agent Service MCP",
            "version": "1.0.0",
            "description": "MCP server exposing agent tools and resources",
            "capabilities": {
                "tools": True,
                "resources": True,
                "prompts": True,
            },
            "authentication": {
                "required": True,
                "methods": ["bearer", "api_key"]
            }
        }

    async def _list_tools(self) -> dict[str, Any]:
        """
        List available tools.

        Returns:
            MCP tools list response
        """
        from agent_service.tools.registry import tool_registry

        tools = []
        for tool_schema in tool_registry.list_tools():
            tools.append({
                "name": tool_schema.name,
                "description": tool_schema.description,
                "inputSchema": tool_schema.parameters
            })

        return {
            "tools": tools
        }

    async def _call_tool(self, params: dict[str, Any], agent: IAgent) -> dict[str, Any]:
        """
        Execute a tool.

        Args:
            params: Tool execution parameters
            agent: Agent instance

        Returns:
            MCP tool call response
        """
        from agent_service.tools.registry import tool_registry

        tool_name = params.get("name")
        tool_args = params.get("arguments", {})

        if not tool_name:
            raise ValueError("Tool name is required")

        try:
            result = await tool_registry.execute(tool_name, **tool_args)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": str(result)
                    }
                ]
            }
        except Exception as e:
            return {
                "isError": True,
                "content": [
                    {
                        "type": "text",
                        "text": f"Error executing tool: {str(e)}"
                    }
                ]
            }

    async def _list_resources(self) -> dict[str, Any]:
        """
        List available resources.

        Returns:
            MCP resources list response
        """
        # Default resources - can be extended
        resources = [
            {
                "uri": "file:///system/info",
                "name": "System Information",
                "description": "System and service information",
                "mimeType": "application/json"
            }
        ]

        return {
            "resources": resources
        }

    async def _read_resource(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Read a resource.

        Args:
            params: Resource read parameters

        Returns:
            MCP resource read response
        """
        uri = params.get("uri")

        if not uri:
            raise ValueError("Resource URI is required")

        # Handle system info resource
        if uri == "file:///system/info":
            from agent_service.config.settings import get_settings
            settings = get_settings()

            info = {
                "service": settings.app_name,
                "version": settings.app_version,
                "environment": settings.environment
            }

            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(info, indent=2)
                    }
                ]
            }

        raise ValueError(f"Unknown resource URI: {uri}")

    async def _list_prompts(self) -> dict[str, Any]:
        """
        List available prompts.

        Returns:
            MCP prompts list response
        """
        prompts = [
            {
                "name": "agent_invoke",
                "description": "Invoke the agent with a message",
                "arguments": [
                    {
                        "name": "message",
                        "description": "Message to send to the agent",
                        "required": True
                    }
                ]
            }
        ]

        return {
            "prompts": prompts
        }

    async def _get_prompt(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Get a prompt template.

        Args:
            params: Prompt get parameters

        Returns:
            MCP prompt get response
        """
        prompt_name = params.get("name")
        arguments = params.get("arguments", {})

        if not prompt_name:
            raise ValueError("Prompt name is required")

        if prompt_name == "agent_invoke":
            message = arguments.get("message", "")
            return {
                "description": "Invoke the agent",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": message
                        }
                    }
                ]
            }

        raise ValueError(f"Unknown prompt: {prompt_name}")
