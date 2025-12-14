"""
Quick start guide for framework integrations.

This file shows minimal examples for getting started with each integration.
"""

from agent_service.interfaces.agent import IAgent, AgentInput
from agent_service.agent.config import AgentConfig


# ============================================================================
# Example 1: LangGraph - Minimal Setup
# ============================================================================

print("Example 1: LangGraph Integration")
print("-" * 60)

try:
    from agent_service.agent.integrations import langgraph_agent, LANGGRAPH_AVAILABLE

    if LANGGRAPH_AVAILABLE:
        from langgraph.graph import StateGraph, END
        from typing import TypedDict

        class SimpleState(TypedDict):
            messages: list[dict]

        def echo(state: SimpleState) -> SimpleState:
            msg = state["messages"][-1]["content"]
            state["messages"].append({"role": "assistant", "content": f"Echo: {msg}"})
            return state

        builder = StateGraph(SimpleState)
        builder.add_node("echo", echo)
        builder.set_entry_point("echo")
        builder.add_edge("echo", END)
        lg_graph = builder.compile()

        @langgraph_agent(graph=lg_graph, name="echo_agent")
        class EchoAgent(IAgent):
            """Simple echo agent using LangGraph."""
            pass

        print("✓ LangGraph agent created: echo_agent")
        print("  Usage: agent = EchoAgent(); result = await agent.invoke(input)")
    else:
        print("✗ LangGraph not available. Install with: pip install langgraph")

except Exception as e:
    print(f"✗ Error: {e}")

print()


# ============================================================================
# Example 2: CrewAI - Minimal Setup
# ============================================================================

print("Example 2: CrewAI Integration")
print("-" * 60)

try:
    from agent_service.agent.integrations import crewai_agent, CREWAI_AVAILABLE

    if CREWAI_AVAILABLE:
        from crewai import Agent, Task, Crew

        writer = Agent(
            role="Writer",
            goal="Write concise responses",
            backstory="A skilled writer",
            verbose=False,
        )

        task = Task(
            description="Write about: {message}",
            agent=writer,
            expected_output="A brief response",
        )

        crew = Crew(agents=[writer], tasks=[task], verbose=False)

        @crewai_agent(crew=crew, name="writer_agent")
        class WriterAgent(IAgent):
            """Simple writer agent using CrewAI."""
            pass

        print("✓ CrewAI agent created: writer_agent")
        print("  Usage: agent = WriterAgent(); result = await agent.invoke(input)")
        print("  Note: Requires LLM API keys (OpenAI, etc.)")
    else:
        print("✗ CrewAI not available. Install with: pip install crewai")

except Exception as e:
    print(f"✗ Error: {e}")

print()


# ============================================================================
# Example 3: OpenAI - Minimal Setup
# ============================================================================

print("Example 3: OpenAI Function Calling Integration")
print("-" * 60)

try:
    from agent_service.agent.integrations import (
        openai_agent,
        tool_to_openai_format,
        OPENAI_AVAILABLE,
    )

    if OPENAI_AVAILABLE:
        # Define a simple tool
        def greet(name: str) -> str:
            """Greet a person by name."""
            return f"Hello, {name}!"

        # Convert to OpenAI format
        tools = [
            tool_to_openai_format(
                name="greet",
                description="Greet a person by name",
                parameters={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Person's name"}
                    },
                    "required": ["name"],
                },
            )
        ]

        @openai_agent(
            name="greeter_agent",
            model="gpt-4",
            tools=tools,
            tool_executors={"greet": greet},
            system_message="You are a friendly greeter.",
        )
        class GreeterAgent(IAgent):
            """Simple greeter agent using OpenAI."""
            pass

        print("✓ OpenAI agent created: greeter_agent")
        print("  Usage: agent = GreeterAgent(); result = await agent.invoke(input)")
        print("  Note: Requires OPENAI_API_KEY environment variable")
    else:
        print("✗ OpenAI not available. Install with: pip install openai")

except Exception as e:
    print(f"✗ Error: {e}")

print()


# ============================================================================
# Example 4: Using AgentConfig
# ============================================================================

print("Example 4: Agent Configuration")
print("-" * 60)

# Create config
config = AgentConfig(
    timeout=120,
    max_tokens=2048,
    temperature=0.5,
    rate_limit="50/hour",
    model="gpt-4",
    metadata={"version": "1.0"},
)

print("✓ Created AgentConfig:")
print(f"  - timeout: {config.timeout}s")
print(f"  - max_tokens: {config.max_tokens}")
print(f"  - temperature: {config.temperature}")
print(f"  - rate_limit: {config.rate_limit}")

# Save to YAML
import tempfile
import os

with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
    config_path = f.name

try:
    config.to_yaml(config_path)
    print(f"✓ Saved config to: {config_path}")

    # Load from YAML
    loaded = AgentConfig.from_yaml(config_path)
    print(f"✓ Loaded config from YAML")
    print(f"  - Loaded timeout: {loaded.timeout}s")
finally:
    os.unlink(config_path)

print()


# ============================================================================
# Example 5: Check Integration Status
# ============================================================================

print("Example 5: Integration Status Check")
print("-" * 60)

from agent_service.agent.integrations import print_integration_status

print_integration_status()

print()


# ============================================================================
# Example 6: Complete Usage Example
# ============================================================================

print("Example 6: Complete Usage Flow")
print("-" * 60)

async def demo_usage():
    """Demonstrate complete usage with error handling."""
    from agent_service.agent.integrations import (
        langgraph_agent,
        LANGGRAPH_AVAILABLE,
    )

    if not LANGGRAPH_AVAILABLE:
        print("⚠ LangGraph not available for demo")
        return

    from langgraph.graph import StateGraph, END
    from typing import TypedDict

    class State(TypedDict):
        messages: list[dict]

    def process(state: State) -> State:
        msg = state["messages"][-1]["content"]
        state["messages"].append({
            "role": "assistant",
            "content": f"Processed: {msg}"
        })
        return state

    builder = StateGraph(State)
    builder.add_node("process", process)
    builder.set_entry_point("process")
    builder.add_edge("process", END)
    graph = builder.compile()

    @langgraph_agent(
        graph=graph,
        name="demo_agent",
        config=AgentConfig(timeout=60),
    )
    class DemoAgent(IAgent):
        pass

    # Create agent instance
    agent = DemoAgent()
    print(f"✓ Created agent: {agent.name}")
    print(f"  Description: {agent.description}")

    # Create input
    input_data = AgentInput(
        message="Hello, agent!",
        session_id="demo-session",
    )

    # Invoke agent
    try:
        result = await agent.invoke(input_data)
        print(f"✓ Agent response: {result.content}")
        if result.metadata:
            print(f"  Metadata: {result.metadata}")
    except Exception as e:
        print(f"✗ Error invoking agent: {e}")

    # Stream agent (optional)
    print("\n✓ Streaming response:")
    try:
        async for chunk in agent.stream(input_data):
            if chunk.content:
                print(f"  Chunk: {chunk.content[:50]}...")
    except Exception as e:
        print(f"✗ Error streaming: {e}")


# Run the demo if this file is executed
if __name__ == "__main__":
    import asyncio

    print("\nRunning complete usage demo...")
    print("=" * 60)
    asyncio.run(demo_usage())
    print("=" * 60)
    print("\n✓ Quick start guide complete!")
    print("\nNext steps:")
    print("  1. Install desired frameworks: pip install langgraph crewai openai")
    print("  2. Set API keys if needed: export OPENAI_API_KEY=...")
    print("  3. See examples.py for more detailed examples")
    print("  4. See README.md for complete documentation")
