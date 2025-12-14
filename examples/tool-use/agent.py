"""
Tool-Using Agent

Demonstrates an agent that uses multiple tools to accomplish tasks.

Features:
- Dynamic tool selection
- Tool chaining (using output of one tool as input to another)
- Error handling and retry
- Tool result interpretation
"""

from typing import AsyncGenerator
from agent_service.interfaces import AgentInput, AgentOutput, StreamChunk
from agent_service.agent import agent, streaming_agent, AgentContext


# ============================================================================
# Tool-Using Agent
# ============================================================================


@agent(
    name="tool_agent",
    description="Agent that uses multiple tools to accomplish tasks"
)
async def tool_agent(
    input: AgentInput,
    ctx: AgentContext
) -> AgentOutput:
    """
    Agent that dynamically selects and uses tools.

    Supports:
    - Math calculations
    - Web searches
    - File operations
    - Data processing
    - API calls

    Example queries:
    - "Calculate 25 * 4 + 10"
    - "Search for Python tutorials"
    - "What time is it?"
    - "Convert 100 F to C"
    """
    query = input.message
    ctx.logger.info("tool_agent_started", query=query)

    try:
        # Parse intent and select appropriate tool(s)
        intent = parse_intent(query)
        ctx.logger.info("intent_detected", intent=intent)

        # Execute based on intent
        if intent == "calculation":
            result = await handle_calculation(query, ctx)

        elif intent == "search":
            result = await handle_search(query, ctx)

        elif intent == "time":
            result = await handle_time_query(query, ctx)

        elif intent == "conversion":
            result = await handle_conversion(query, ctx)

        elif intent == "file":
            result = await handle_file_operation(query, ctx)

        elif intent == "data":
            result = await handle_data_processing(query, ctx)

        else:
            # Default: try to be helpful
            result = await handle_general_query(query, ctx)

        ctx.logger.info("tool_agent_completed", success=True)

        return AgentOutput(
            content=result["response"],
            metadata={
                "intent": intent,
                "tools_used": result.get("tools_used", []),
                "success": True
            }
        )

    except Exception as e:
        ctx.logger.error("tool_agent_failed", error=str(e), exc_info=True)
        return AgentOutput(
            content=f"I encountered an error: {str(e)}",
            metadata={"error": str(e), "success": False}
        )


# ============================================================================
# Intent Handlers
# ============================================================================


async def handle_calculation(query: str, ctx: AgentContext) -> dict:
    """Handle mathematical calculations."""
    # Extract expression from query
    expression = extract_expression(query)

    # Call calculator tool
    result = await ctx.call_tool("calculate", expression=expression)

    if result.get("success"):
        response = f"The result of {expression} is {result['result']}"
        tools_used = ["calculate"]
    else:
        response = f"I couldn't calculate that: {result.get('error', 'unknown error')}"
        tools_used = []

    return {
        "response": response,
        "tools_used": tools_used,
        "data": result
    }


async def handle_search(query: str, ctx: AgentContext) -> dict:
    """Handle web search queries."""
    # Extract search terms
    search_query = extract_search_query(query)

    # Call search tool
    result = await ctx.call_tool("web_search", query=search_query, max_results=3)

    # Format results
    response = f"I found {result['count']} results for '{search_query}':\n\n"
    for i, item in enumerate(result["results"], 1):
        response += f"{i}. {item['title']}\n"
        response += f"   {item['url']}\n"
        response += f"   {item['snippet']}\n\n"

    return {
        "response": response,
        "tools_used": ["web_search"],
        "data": result
    }


async def handle_time_query(query: str, ctx: AgentContext) -> dict:
    """Handle time-related queries."""
    # Get current time
    result = await ctx.call_tool("get_current_time", timezone="UTC")

    response = f"The current UTC time is {result['datetime']}\n"
    response += f"Date: {result['date']}\n"
    response += f"Time: {result['time']}"

    return {
        "response": response,
        "tools_used": ["get_current_time"],
        "data": result
    }


async def handle_conversion(query: str, ctx: AgentContext) -> dict:
    """Handle unit conversions."""
    # Parse conversion request
    conversion = parse_conversion(query)

    if conversion:
        result = await ctx.call_tool(
            "convert_units",
            value=conversion["value"],
            from_unit=conversion["from_unit"],
            to_unit=conversion["to_unit"]
        )

        if result.get("success"):
            response = f"{conversion['value']} {conversion['from_unit']} = {result['converted_value']:.2f} {conversion['to_unit']}"
            tools_used = ["convert_units"]
        else:
            response = f"I couldn't convert that: {result.get('error', 'unknown error')}"
            tools_used = []
    else:
        response = "I couldn't understand the conversion request. Please use format like '100 F to C' or '5 km to mi'."
        tools_used = []
        result = {}

    return {
        "response": response,
        "tools_used": tools_used,
        "data": result
    }


async def handle_file_operation(query: str, ctx: AgentContext) -> dict:
    """Handle file operations."""
    query_lower = query.lower()

    if "read" in query_lower:
        # Extract file path
        # In production, use NLP to extract path
        response = "File reading requires a specific path. Example: 'read file /path/to/file.txt'"
        tools_used = []
        result = {}
    elif "write" in query_lower:
        response = "File writing requires confirmation and specific parameters."
        tools_used = []
        result = {}
    else:
        response = "I can help with file operations. Try 'read file <path>' or 'write to file <path>'."
        tools_used = []
        result = {}

    return {
        "response": response,
        "tools_used": tools_used,
        "data": result
    }


async def handle_data_processing(query: str, ctx: AgentContext) -> dict:
    """Handle data processing tasks."""
    query_lower = query.lower()

    if "parse json" in query_lower:
        response = "I can parse JSON. Provide the JSON string you'd like me to parse."
        tools_used = []
        result = {}
    else:
        response = "I can help with data processing: parsing JSON, extracting fields, formatting data."
        tools_used = []
        result = {}

    return {
        "response": response,
        "tools_used": tools_used,
        "data": result
    }


async def handle_general_query(query: str, ctx: AgentContext) -> dict:
    """Handle general queries by suggesting available tools."""
    response = f"""I'm not sure how to help with: "{query}"

I have access to these tools:
- Calculator: for math calculations
- Web Search: to find information online
- Time: to get current date/time
- Unit Converter: to convert between units
- File Operations: to read/write files
- Data Processing: to parse and format data

Try asking things like:
- "Calculate 25 * 4 + 10"
- "Search for Python tutorials"
- "What time is it?"
- "Convert 100 F to C"
"""

    return {
        "response": response,
        "tools_used": [],
        "data": {}
    }


# ============================================================================
# Tool Chaining Agent
# ============================================================================


@agent(
    name="tool_chain_agent",
    description="Agent that chains multiple tools together"
)
async def tool_chain_agent(
    input: AgentInput,
    ctx: AgentContext
) -> AgentOutput:
    """
    Agent that chains multiple tools to accomplish complex tasks.

    Example: "Search for Python tutorials and save the results to a file"
    - Tool 1: web_search
    - Tool 2: format_json (to structure results)
    - Tool 3: write_file (to save)
    """
    query = input.message
    ctx.logger.info("tool_chain_started", query=query)

    try:
        # Example chain: Search -> Format -> Present
        tools_used = []

        # Step 1: Search
        if "search" in query.lower():
            search_query = extract_search_query(query)
            search_result = await ctx.call_tool("web_search", query=search_query)
            tools_used.append("web_search")

            # Step 2: Format results as JSON
            formatted = await ctx.call_tool("format_json", data=search_result)
            tools_used.append("format_json")

            response = f"Search results for '{search_query}':\n\n{formatted['formatted']}"

        # Example chain: Calculate -> Convert
        elif "calculate" in query.lower() and "convert" in query.lower():
            # First calculate
            expression = extract_expression(query)
            calc_result = await ctx.call_tool("calculate", expression=expression)
            tools_used.append("calculate")

            # Then convert if needed
            # (simplified example)
            response = f"Calculation result: {calc_result['result']}"

        else:
            response = "I can chain tools together. Try: 'Search for Python and format as JSON'"
            tools_used = []

        return AgentOutput(
            content=response,
            metadata={
                "tools_used": tools_used,
                "chain_length": len(tools_used)
            }
        )

    except Exception as e:
        ctx.logger.error("tool_chain_failed", error=str(e), exc_info=True)
        return AgentOutput(
            content=f"Tool chaining failed: {str(e)}",
            metadata={"error": str(e)}
        )


# ============================================================================
# Parallel Tool Agent
# ============================================================================


@agent(
    name="parallel_tool_agent",
    description="Agent that executes multiple tools in parallel"
)
async def parallel_tool_agent(
    input: AgentInput,
    ctx: AgentContext
) -> AgentOutput:
    """
    Agent that executes multiple tools in parallel for efficiency.

    Example: "Get the weather, current time, and search results for Python"
    Executes all three tools simultaneously.
    """
    import asyncio

    query = input.message
    ctx.logger.info("parallel_tool_execution_started", query=query)

    try:
        # Parse which tools to run
        tasks = []
        tool_names = []

        if "time" in query.lower():
            tasks.append(ctx.call_tool("get_current_time"))
            tool_names.append("get_current_time")

        if "search" in query.lower():
            search_query = extract_search_query(query)
            tasks.append(ctx.call_tool("web_search", query=search_query))
            tool_names.append("web_search")

        if "calculate" in query.lower() or "math" in query.lower():
            tasks.append(ctx.call_tool("calculate", expression="2+2"))
            tool_names.append("calculate")

        if not tasks:
            return AgentOutput(
                content="Specify multiple operations to run in parallel, like: 'Get time and search for Python'"
            )

        # Execute all tools in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Compile results
        response = f"Executed {len(tasks)} tools in parallel:\n\n"
        for name, result in zip(tool_names, results):
            if isinstance(result, Exception):
                response += f"- {name}: Error - {str(result)}\n"
            else:
                response += f"- {name}: Success\n"

        return AgentOutput(
            content=response,
            metadata={
                "tools_used": tool_names,
                "parallel_count": len(tasks),
                "success_count": sum(1 for r in results if not isinstance(r, Exception))
            }
        )

    except Exception as e:
        ctx.logger.error("parallel_tool_execution_failed", error=str(e), exc_info=True)
        return AgentOutput(
            content=f"Parallel execution failed: {str(e)}",
            metadata={"error": str(e)}
        )


# ============================================================================
# Helper Functions
# ============================================================================


def parse_intent(query: str) -> str:
    """Parse user intent from query."""
    query_lower = query.lower()

    if any(word in query_lower for word in ["calculate", "compute", "math", "+", "-", "*", "/"]):
        return "calculation"
    elif any(word in query_lower for word in ["search", "find", "look up", "google"]):
        return "search"
    elif any(word in query_lower for word in ["time", "date", "clock", "when"]):
        return "time"
    elif any(word in query_lower for word in ["convert", "to", "from"]) and any(word in query_lower for word in ["f", "c", "k", "km", "mi", "kg", "lb"]):
        return "conversion"
    elif any(word in query_lower for word in ["read", "write", "file"]):
        return "file"
    elif any(word in query_lower for word in ["parse", "json", "extract", "format"]):
        return "data"
    else:
        return "general"


def extract_expression(query: str) -> str:
    """Extract mathematical expression from query."""
    # Simple extraction - in production, use NLP
    query = query.lower()

    # Remove common words
    for word in ["calculate", "compute", "what is", "what's", "equals", "="]:
        query = query.replace(word, "")

    return query.strip()


def extract_search_query(query: str) -> str:
    """Extract search terms from query."""
    query = query.lower()

    # Remove search-related words
    for word in ["search for", "search", "find", "look up", "google"]:
        query = query.replace(word, "")

    return query.strip()


def parse_conversion(query: str) -> dict | None:
    """Parse unit conversion request."""
    import re

    # Pattern: "100 F to C" or "5 km to mi"
    pattern = r'(\d+\.?\d*)\s*([a-zA-Z]+)\s+to\s+([a-zA-Z]+)'
    match = re.search(pattern, query, re.IGNORECASE)

    if match:
        return {
            "value": float(match.group(1)),
            "from_unit": match.group(2).upper(),
            "to_unit": match.group(3).upper()
        }

    return None


# ============================================================================
# Example Usage
# ============================================================================


async def example_usage():
    """Demonstrate tool-using agent."""
    from agent_service.agent import agent_registry

    agent = agent_registry.get("tool_agent")

    # Example 1: Calculation
    print("Example 1: Calculation")
    result = await agent.invoke(AgentInput(message="Calculate 25 * 4 + 10"))
    print(result.content)
    print(f"Tools used: {result.metadata['tools_used']}\n")

    # Example 2: Search
    print("Example 2: Search")
    result = await agent.invoke(AgentInput(message="Search for Python tutorials"))
    print(result.content)
    print(f"Tools used: {result.metadata['tools_used']}\n")

    # Example 3: Time
    print("Example 3: Time")
    result = await agent.invoke(AgentInput(message="What time is it?"))
    print(result.content)
    print(f"Tools used: {result.metadata['tools_used']}\n")

    # Example 4: Conversion
    print("Example 4: Conversion")
    result = await agent.invoke(AgentInput(message="Convert 100 F to C"))
    print(result.content)
    print(f"Tools used: {result.metadata['tools_used']}\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
