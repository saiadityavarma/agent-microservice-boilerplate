"""
Example usage of framework integrations.

This file demonstrates how to use the integration decorators for
LangGraph, CrewAI, and OpenAI function calling.
"""

from __future__ import annotations
from agent_service.interfaces.agent import IAgent, AgentInput, AgentOutput
from agent_service.agent.config import AgentConfig


# ============================================================================
# LangGraph Integration Example
# ============================================================================

def create_langgraph_example():
    """
    Example: Creating a LangGraph agent using the decorator.

    This example shows how to wrap a LangGraph StateGraph as an IAgent.
    """
    try:
        from agent_service.agent.integrations import langgraph_agent, LANGGRAPH_AVAILABLE

        if not LANGGRAPH_AVAILABLE:
            print("LangGraph not available. Install with: pip install langgraph")
            return None

        from langgraph.graph import StateGraph, END
        from typing import TypedDict

        # Define state
        class AgentState(TypedDict):
            messages: list[dict]
            session_id: str | None

        # Create graph
        def process_message(state: AgentState) -> AgentState:
            """Simple processing node."""
            messages = state["messages"]
            # Add a response message
            messages.append({
                "role": "assistant",
                "content": f"Processed: {messages[-1]['content']}"
            })
            return {"messages": messages, "session_id": state["session_id"]}

        # Build graph
        graph = StateGraph(AgentState)
        graph.add_node("process", process_message)
        graph.set_entry_point("process")
        graph.add_edge("process", END)
        compiled_graph = graph.compile()

        # Wrap as IAgent using decorator
        @langgraph_agent(
            graph=compiled_graph,
            name="example_langgraph_agent",
            description="Example LangGraph agent",
            config=AgentConfig(timeout=60, temperature=0.5),
        )
        class ExampleLangGraphAgent(IAgent):
            """This class body is ignored - the decorator returns a LangGraphAgent."""
            pass

        return ExampleLangGraphAgent

    except ImportError as e:
        print(f"LangGraph example requires langgraph: {e}")
        return None


# ============================================================================
# CrewAI Integration Example
# ============================================================================

def create_crewai_example():
    """
    Example: Creating a CrewAI agent using the decorator.

    This example shows how to wrap a CrewAI Crew as an IAgent.
    """
    try:
        from agent_service.agent.integrations import crewai_agent, CREWAI_AVAILABLE

        if not CREWAI_AVAILABLE:
            print("CrewAI not available. Install with: pip install crewai")
            return None

        from crewai import Agent, Task, Crew

        # Create CrewAI components
        researcher = Agent(
            role="Researcher",
            goal="Research and gather information",
            backstory="An expert researcher skilled at finding relevant information.",
            verbose=True,
        )

        research_task = Task(
            description="Research the topic: {message}",
            agent=researcher,
            expected_output="A comprehensive research summary",
        )

        crew = Crew(
            agents=[researcher],
            tasks=[research_task],
            verbose=True,
        )

        # Wrap as IAgent using decorator
        @crewai_agent(
            crew=crew,
            name="example_crewai_agent",
            description="Example CrewAI research agent",
            config=AgentConfig(timeout=300, max_tokens=2048),
        )
        class ExampleCrewAIAgent(IAgent):
            """This class body is ignored - the decorator returns a CrewAIAgent."""
            pass

        return ExampleCrewAIAgent

    except ImportError as e:
        print(f"CrewAI example requires crewai: {e}")
        return None


# ============================================================================
# OpenAI Function Calling Example
# ============================================================================

def create_openai_example():
    """
    Example: Creating an OpenAI function calling agent using the decorator.

    This example shows how to use OpenAI chat completions with function calling.
    """
    try:
        from agent_service.agent.integrations import (
            openai_agent,
            tool_to_openai_format,
            OPENAI_AVAILABLE,
        )

        if not OPENAI_AVAILABLE:
            print("OpenAI not available. Install with: pip install openai")
            return None

        # Define tools
        def get_weather(location: str, unit: str = "celsius") -> dict:
            """Get the weather for a location."""
            # Mock implementation
            return {
                "location": location,
                "temperature": 22,
                "unit": unit,
                "condition": "sunny",
            }

        def calculate(operation: str, a: float, b: float) -> dict:
            """Perform a calculation."""
            operations = {
                "add": a + b,
                "subtract": a - b,
                "multiply": a * b,
                "divide": a / b if b != 0 else None,
            }
            return {
                "operation": operation,
                "result": operations.get(operation),
            }

        # Convert tools to OpenAI format
        tools = [
            tool_to_openai_format(
                name="get_weather",
                description="Get the current weather for a location",
                parameters={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA",
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "Temperature unit",
                        },
                    },
                    "required": ["location"],
                },
            ),
            tool_to_openai_format(
                name="calculate",
                description="Perform a mathematical calculation",
                parameters={
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": ["add", "subtract", "multiply", "divide"],
                        },
                        "a": {"type": "number"},
                        "b": {"type": "number"},
                    },
                    "required": ["operation", "a", "b"],
                },
            ),
        ]

        # Map tool names to executors
        tool_executors = {
            "get_weather": get_weather,
            "calculate": calculate,
        }

        # Wrap as IAgent using decorator
        @openai_agent(
            name="example_openai_agent",
            model="gpt-4",
            tools=tools,
            tool_executors=tool_executors,
            description="Example OpenAI agent with tools",
            config=AgentConfig(temperature=0.7, max_tokens=1000),
            system_message="You are a helpful assistant with access to weather and calculator tools.",
        )
        class ExampleOpenAIAgent(IAgent):
            """This class body is ignored - the decorator returns an OpenAIFunctionAgent."""
            pass

        return ExampleOpenAIAgent

    except ImportError as e:
        print(f"OpenAI example requires openai: {e}")
        return None


# ============================================================================
# Usage Example
# ============================================================================

async def demonstrate_integrations():
    """
    Demonstrate using all integration types.
    """
    print("=" * 60)
    print("Agent Framework Integration Examples")
    print("=" * 60)

    # LangGraph
    print("\n1. LangGraph Integration")
    print("-" * 60)
    lg_agent = create_langgraph_example()
    if lg_agent:
        print(f"Created: {lg_agent.name}")
        print(f"Description: {lg_agent.description}")

        # Test invoke
        input_data = AgentInput(
            message="Hello from LangGraph!",
            session_id="test-session",
        )
        result = await lg_agent.invoke(input_data)
        print(f"Result: {result.content}")

    # CrewAI
    print("\n2. CrewAI Integration")
    print("-" * 60)
    crew_agent = create_crewai_example()
    if crew_agent:
        print(f"Created: {crew_agent.name}")
        print(f"Description: {crew_agent.description}")
        print("Note: CrewAI requires API keys to run")

    # OpenAI
    print("\n3. OpenAI Integration")
    print("-" * 60)
    oai_agent = create_openai_example()
    if oai_agent:
        print(f"Created: {oai_agent.name}")
        print(f"Description: {oai_agent.description}")
        print("Note: OpenAI requires OPENAI_API_KEY to run")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(demonstrate_integrations())
