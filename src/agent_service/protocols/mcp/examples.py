"""
Example usage of MCP protocol implementation.

These examples demonstrate how to use the MCP handler, server, and tools.
"""
import asyncio
from typing import Any


async def example_list_tools():
    """Example: List all available MCP tools."""
    from agent_service.protocols.mcp import MCPHandler
    from agent_service.tools.registry import tool_registry
    from agent_service.tools.examples.echo import EchoTool
    from agent_service.tools.examples.http_request import HTTPRequestTool

    # Register example tools
    tool_registry.register(EchoTool())
    tool_registry.register(HTTPRequestTool())

    # Create handler
    handler = MCPHandler()

    # List tools
    result = await handler._list_tools()
    print("Available MCP Tools:")
    for tool in result["tools"]:
        print(f"  - {tool['name']}: {tool['description']}")

    return result


async def example_call_tool():
    """Example: Call a tool via MCP."""
    from agent_service.protocols.mcp import MCPHandler
    from agent_service.tools.registry import tool_registry
    from agent_service.tools.examples.echo import EchoTool

    # Register tool
    tool_registry.register(EchoTool())

    # Create handler
    handler = MCPHandler()

    # Call tool
    params = {
        "name": "echo",
        "arguments": {"message": "Hello from MCP!"}
    }
    result = await handler._call_tool(params, agent=None)

    print("Tool Result:")
    print(f"  {result['content'][0]['text']}")

    return result


async def example_list_resources():
    """Example: List available resources."""
    from agent_service.protocols.mcp import MCPHandler

    handler = MCPHandler()
    result = await handler._list_resources()

    print("Available Resources:")
    for resource in result["resources"]:
        print(f"  - {resource['name']}: {resource['uri']}")

    return result


async def example_read_resource():
    """Example: Read a resource."""
    from agent_service.protocols.mcp import MCPHandler

    handler = MCPHandler()
    params = {"uri": "file:///system/info"}
    result = await handler._read_resource(params)

    print("System Info Resource:")
    print(result["contents"][0]["text"])

    return result


async def example_list_prompts():
    """Example: List available prompts."""
    from agent_service.protocols.mcp import MCPHandler

    handler = MCPHandler()
    result = await handler._list_prompts()

    print("Available Prompts:")
    for prompt in result["prompts"]:
        print(f"  - {prompt['name']}: {prompt['description']}")

    return result


async def example_get_prompt():
    """Example: Get a prompt template."""
    from agent_service.protocols.mcp import MCPHandler

    handler = MCPHandler()
    params = {
        "name": "agent_invoke",
        "arguments": {"message": "What is the weather?"}
    }
    result = await handler._get_prompt(params)

    print("Prompt Template:")
    print(f"  Description: {result['description']}")
    print(f"  Message: {result['messages'][0]['content']['text']}")

    return result


async def example_full_mcp_workflow():
    """Example: Complete MCP workflow."""
    from agent_service.protocols.mcp import MCPHandler
    from agent_service.tools.registry import tool_registry
    from agent_service.tools.examples.echo import EchoTool

    # Setup
    tool_registry.register(EchoTool())
    handler = MCPHandler()

    print("=== MCP Workflow Example ===\n")

    # 1. Get server capabilities
    print("1. Server Capabilities:")
    capabilities = handler.get_capability_info()
    print(f"   Name: {capabilities['name']}")
    print(f"   Version: {capabilities['version']}")
    print(f"   Capabilities: {list(capabilities['capabilities'].keys())}\n")

    # 2. List tools
    print("2. Available Tools:")
    tools = await handler._list_tools()
    for tool in tools["tools"]:
        print(f"   - {tool['name']}")

    # 3. List resources
    print("\n3. Available Resources:")
    resources = await handler._list_resources()
    for resource in resources["resources"]:
        print(f"   - {resource['name']}")

    # 4. Call a tool
    print("\n4. Execute Tool:")
    result = await handler._call_tool(
        {"name": "echo", "arguments": {"message": "MCP is working!"}},
        agent=None
    )
    print(f"   Result: {result['content'][0]['text']}")

    # 5. Read a resource
    print("\n5. Read Resource:")
    resource_data = await handler._read_resource({"uri": "file:///system/info"})
    print(f"   Data: {resource_data['contents'][0]['text'][:100]}...")

    print("\n=== Workflow Complete ===")


async def example_tool_validation():
    """Example: Validate tool arguments before execution."""
    from agent_service.protocols.mcp.tools import validate_tool_arguments
    from agent_service.tools.registry import tool_registry
    from agent_service.tools.examples.echo import EchoTool

    # Register tool
    tool_registry.register(EchoTool())
    tool = tool_registry.get("echo")

    # Valid arguments
    valid_args = {"message": "Hello"}
    is_valid, error = validate_tool_arguments(tool.schema, valid_args)
    print(f"Valid arguments: {is_valid}")

    # Invalid arguments (missing required param)
    invalid_args = {}
    is_valid, error = validate_tool_arguments(tool.schema, invalid_args)
    print(f"Invalid arguments: {is_valid}, Error: {error}")

    # Invalid arguments (wrong type)
    wrong_type_args = {"message": 123}
    is_valid, error = validate_tool_arguments(tool.schema, wrong_type_args)
    print(f"Wrong type arguments: {is_valid}, Error: {error}")


async def example_custom_tool_registration():
    """Example: Register a custom tool and use it via MCP."""
    from agent_service.interfaces import ITool, ToolSchema
    from agent_service.tools.registry import tool_registry
    from agent_service.protocols.mcp import MCPHandler

    # Define custom tool
    class GreetTool(ITool):
        @property
        def schema(self) -> ToolSchema:
            return ToolSchema(
                name="greet",
                description="Greet a person by name",
                parameters={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Name to greet"},
                        "formal": {"type": "boolean", "description": "Use formal greeting"}
                    },
                    "required": ["name"]
                }
            )

        async def execute(self, name: str, formal: bool = False, **kwargs) -> str:
            if formal:
                return f"Good day, {name}."
            return f"Hi {name}!"

    # Register custom tool
    tool_registry.register(GreetTool())

    # Use via MCP
    handler = MCPHandler()

    # Informal greeting
    result1 = await handler._call_tool(
        {"name": "greet", "arguments": {"name": "Alice"}},
        agent=None
    )
    print(f"Informal: {result1['content'][0]['text']}")

    # Formal greeting
    result2 = await handler._call_tool(
        {"name": "greet", "arguments": {"name": "Mr. Smith", "formal": True}},
        agent=None
    )
    print(f"Formal: {result2['content'][0]['text']}")


async def example_error_handling():
    """Example: MCP error handling."""
    from agent_service.protocols.mcp import MCPHandler

    handler = MCPHandler()

    # Try to call non-existent tool
    result = await handler._call_tool(
        {"name": "nonexistent", "arguments": {}},
        agent=None
    )

    print("Error Response:")
    print(f"  Is Error: {result.get('isError', False)}")
    print(f"  Message: {result['content'][0]['text']}")


async def example_registry_usage():
    """Example: Using the protocol registry."""
    from agent_service.protocols import get_protocol_registry
    from agent_service.interfaces import ProtocolType

    registry = get_protocol_registry()

    # Check if MCP is registered
    if registry.is_registered("mcp"):
        print("MCP is registered!")

    # Get handler
    mcp_handler = registry.get_handler("mcp")
    if mcp_handler:
        info = mcp_handler.get_capability_info()
        print(f"MCP Server: {info['name']}")

    # List all protocols
    protocols = registry.list_protocols()
    print(f"Registered protocols: {protocols}")

    # Get by protocol type
    handler = registry.get(ProtocolType.MCP)
    print(f"Handler: {handler.__class__.__name__}")


def run_example(example_func):
    """Helper to run an async example."""
    print(f"\n{'='*60}")
    print(f"Running: {example_func.__name__}")
    print(f"{'='*60}\n")
    return asyncio.run(example_func())


if __name__ == "__main__":
    """Run all examples."""
    # Basic examples
    run_example(example_list_tools)
    run_example(example_call_tool)
    run_example(example_list_resources)
    run_example(example_read_resource)
    run_example(example_list_prompts)
    run_example(example_get_prompt)

    # Advanced examples
    run_example(example_full_mcp_workflow)
    run_example(example_tool_validation)
    run_example(example_custom_tool_registration)
    run_example(example_error_handling)
    run_example(example_registry_usage)

    print("\n" + "="*60)
    print("All examples completed!")
    print("="*60)
